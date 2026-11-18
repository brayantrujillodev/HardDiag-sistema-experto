"""
pruebas.py
==========
Script de pruebas por consola del Sistema Experto de Diagnóstico de Hardware.

Ejecuta once casos base, verificaciones de integración (diagnóstico,
explicabilidad, sugerencias, DCG y pre-procesamiento numérico) y las pruebas
de persistencia del Entregable 3. Guarda la salida en ``evidencia_pruebas.txt``.

Las pruebas que crean reglas trabajan sobre una COPIA temporal de
``base_conocimiento.pl`` y cada fase corre en un proceso de Python nuevo, que
equivale a reiniciar la aplicación: así se comprueba que la regla sobrevive
porque quedó escrita en el archivo .pl y no porque siga en memoria.

Ejecución:  python pruebas.py
Código de salida: 0 si todos los casos pasan, 1 si alguno falla.

Python solo envía la entrada, invoca Prolog y compara/presenta resultados.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from motor_inferencia import RUTA_BASE as RUTA_BASE_REAL
from motor_inferencia import MotorInferencia, formatear_respuesta
from preprocesamiento import Preprocesador

ARCHIVO_EVIDENCIA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "evidencia_pruebas.txt")

# Cada caso: tipo, objetivo, entrada (texto enviado a Prolog) y esperado.
CASOS = [
    {
        "id": 1,
        "tipo": "Normal 1 (diagnóstico único claro)",
        "objetivo": "Un solo diagnóstico claro, con severidad elevada por olor a quemado.",
        "entrada": "no_enciende, olor_quemado, prueba(fuente_con_probador, falla)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("fuente_poder_defectuosa", "critica")],
                     "niveles_danio": ["grave"]},
    },
    {
        "id": 2,
        "tipo": "Normal 2 (múltiples diagnósticos / recolección)",
        "objetivo": "Recolectar dos diagnósticos distintos, sin duplicados y "
                    "ordenados por prioridad (el de mayor severidad primero).",
        "entrada": "pantalla_azul, bloqueos, pitidos(tres_cortos), "
                   "prueba(reasentar_ram, no_resuelve), arranque_lento, "
                   "ruido_clic, prueba(smart_disco, falla)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("disco_fallando", "alta"),
                                      ("ram_defectuosa", "media")],
                     "niveles_danio": ["grave", "moderado"]},
    },
    {
        "id": 3,
        "tipo": "Normal 3 (severidad crítica por temperatura)",
        "objetivo": "Elevar a 'critica' la severidad cuando la temperatura "
                    "del procesador supera el umbral crítico.",
        "entrada": "temp_cpu(97), ventilador_ruidoso",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("refrigeracion_deficiente", "critica")],
                     "niveles_danio": ["moderado"]},
    },
    {
        "id": 4,
        "tipo": "Exclusión 1 (\\+)",
        "objetivo": "Descartar la falla de fuente aunque haya síntomas, porque "
                    "la fuente pasó la prueba (\\+ descartado). Debe quedar solo "
                    "la batería CMOS.",
        "entrada": "no_enciende, olor_quemado, prueba(fuente_con_probador, ok), "
                   "hora_incorrecta, equipo(escritorio, 7)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("bateria_cmos_agotada", "baja")],
                     "niveles_danio": ["leve"]},
    },
    {
        "id": 5,
        "tipo": "Exclusión 2 (! reglas mutuamente excluyentes)",
        "objetivo": "RAM mal asentada y RAM defectuosa son excluyentes: si "
                    "reasentar resuelve, solo debe salir 'ram_mal_asentada'.",
        "entrada": "pantalla_azul, prueba(reasentar_ram, resuelve)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("ram_mal_asentada", "baja")],
                     "niveles_danio": ["leve"]},
    },
    {
        "id": 6,
        "tipo": "Borde 1 (datos insuficientes / lista parcial)",
        "objetivo": "Con un solo síntoma ninguna regla se cumple: debe indicar "
                    "datos insuficientes y sugerir el componente sospechoso.",
        "entrada": "pantalla_negra",
        "esperado": {"estado": "datos_insuficientes", "diagnosticos": [],
                     "sospechosos": ["tarjeta_video"]},
    },
    {
        "id": 7,
        "tipo": "Borde 1b (lista con elementos inválidos)",
        "objetivo": "Ignorar elementos no reconocidos sin romper la consulta y "
                    "reportarlos como descartados.",
        "entrada": "xyz, temp_cpu(abc), pantalla_negra",
        "esperado": {"estado": "datos_insuficientes", "diagnosticos": [],
                     "descartados": ["xyz", "temp_cpu(abc)"]},
    },
    {
        "id": 8,
        "tipo": "Borde 2 (lista vacía / caso por defecto)",
        "objetivo": "Una lista vacía no debe producir errores en Python: "
                    "Prolog responde con el caso por defecto 'entrada_vacia'.",
        "entrada": "",
        "esperado": {"estado": "entrada_vacia", "diagnosticos": []},
    },
    {
        "id": 9,
        "tipo": "Placa base (nuevas reglas de inferencia)",
        "objetivo": "Diagnosticar la placa base cuando no hay energía, "
                    "la fuente pasa la prueba y el patrón BIOS apunta a la placa.",
        "entrada": "no_enciende, prueba(fuente_con_probador, ok), "
                   "pitidos(un_largo_tres_cortos)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("placa_base_defectuosa", "alta")],
                     "niveles_danio": ["grave"]},
    },
    {
        "id": 10,
        "tipo": "Nivel de daño leve (cable o monitor)",
        "objetivo": "Clasificar como leve la falla externa de cable o monitor.",
        "entrada": "pantalla_negra, ventiladores_giran, "
                   "prueba(cambio_cable, resuelve)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("cable_o_monitor_defectuoso", "baja")],
                     "niveles_danio": ["leve"]},
    },
    {
        "id": 11,
        "tipo": "Nivel de daño grave (tarjeta gráfica)",
        "objetivo": "Clasificar como grave la falla de la tarjeta gráfica.",
        "entrada": "pantalla_negra, ventiladores_giran, lineas_en_pantalla, "
                   "prueba(cambio_cable, no_resuelve), "
                   "prueba(otro_monitor, no_resuelve)",
        "esperado": {"estado": "ok",
                     "diagnosticos": [("gpu_defectuosa", "alta")],
                     "niveles_danio": ["grave"]},
    },
]


class Tee:
    """Escribe a la vez en la consola y en el archivo de evidencia."""

    def __init__(self, *flujos):
        self.flujos = flujos

    def write(self, texto):
        for flujo in self.flujos:
            flujo.write(texto)

    def flush(self):
        for flujo in self.flujos:
            flujo.flush()


def evaluar(resp, esperado):
    """Compara lo obtenido con lo esperado; devuelve (ok, lista_de_diferencias)."""
    diferencias = []
    if resp.estado != esperado["estado"]:
        diferencias.append(f"estado: esperado {esperado['estado']}, obtenido {resp.estado}")
    obtenidos = [(d.nombre, d.severidad) for d in resp.diagnosticos]
    if obtenidos != esperado["diagnosticos"]:
        diferencias.append(f"diagnósticos: esperado {esperado['diagnosticos']}, obtenido {obtenidos}")
    if "niveles_danio" in esperado:
        niveles = [d.nivel_danio for d in resp.diagnosticos]
        if niveles != esperado["niveles_danio"]:
            diferencias.append(
                f"niveles de daño: esperado {esperado['niveles_danio']}, obtenido {niveles}"
            )
    if "sospechosos" in esperado:
        comps = [c for c, _ in resp.sospechosos]
        if comps != esperado["sospechosos"]:
            diferencias.append(f"sospechosos: esperado {esperado['sospechosos']}, obtenido {comps}")
    if "descartados" in esperado and resp.descartados != esperado["descartados"]:
        diferencias.append(f"descartados: esperado {esperado['descartados']}, obtenido {resp.descartados}")
    return not diferencias, diferencias


def describir_esperado(esperado):
    partes = [f"estado = {esperado['estado']}"]
    if esperado["diagnosticos"]:
        partes.append("diagnósticos = " + ", ".join(
            f"{n} ({s})" for n, s in esperado["diagnosticos"]))
        if "niveles_danio" in esperado:
            partes.append("niveles de daño = " + ", ".join(esperado["niveles_danio"]))
    else:
        partes.append("diagnósticos = ninguno")
    if "sospechosos" in esperado:
        partes.append("sospechoso principal = " + esperado["sospechosos"][0])
    if "descartados" in esperado:
        partes.append("ignorados = " + ", ".join(esperado["descartados"]))
    return "; ".join(partes)


def main():
    with open(ARCHIVO_EVIDENCIA, "w", encoding="utf-8") as archivo:
        sys.stdout = Tee(sys.__stdout__, archivo)
        try:
            ejecutar()
        finally:
            sys.stdout = sys.__stdout__
    return 0


def ejecutar():
    motor = MotorInferencia()
    print("=" * 72)
    print(" PRUEBAS DEL SISTEMA EXPERTO DE DIAGNÓSTICO DE HARDWARE")
    print("=" * 72)
    aprobados = 0
    for caso in CASOS:
        resp = motor.consultar_texto(caso["entrada"])
        ok, diferencias = evaluar(resp, caso["esperado"])
        aprobados += ok
        entrada_mostrada = caso["entrada"] if caso["entrada"] else "(texto vacío)"
        print(f"\nCaso {caso['id']}: {caso['tipo']}")
        print("-" * 72)
        print(f"Objetivo : {caso['objetivo']}")
        print(f"Entrada  : {entrada_mostrada}")
        print(f"Consulta : consultar_texto('{caso['entrada']}', Respuesta).")
        print(f"Esperado : {describir_esperado(caso['esperado'])}")
        print("Obtenido :")
        for linea in formatear_respuesta(resp).splitlines():
            print("    " + linea)
        print(f"Resultado: {'APROBADO' if ok else 'FALLIDO'}")
        for d in diferencias:
            print(f"    ! {d}")
    print("\n" + "=" * 72)
    integraciones_aprobadas, integraciones_total = evaluar_integraciones(motor)
    aprobados += integraciones_aprobadas
    print(f" INTEGRACIÓN: {integraciones_aprobadas} de {integraciones_total} casos aprobados")
    print("=" * 72)
    print(" DCG: oraciones en español analizadas por Prolog")
    dcg_aprobados, dcg_total = evaluar_dcg(motor)
    aprobados += dcg_aprobados
    print(f" DCG: {dcg_aprobados} de {dcg_total} oraciones analizadas correctamente")
    print("=" * 72)
    print(" CONSISTENCIA (Entregable 4): contradicciones y entradas ambiguas")
    consistencia_aprobadas, consistencia_total = evaluar_consistencia(motor)
    aprobados += consistencia_aprobadas
    print(f" CONSISTENCIA: {consistencia_aprobadas} de {consistencia_total} verificaciones aprobadas")
    print("=" * 72)
    print(" PERSISTENCIA: regla aprendida en caliente y reinicios")
    persistencia_aprobadas, persistencia_total = evaluar_persistencia()
    aprobados += persistencia_aprobadas
    print(f" PERSISTENCIA: {persistencia_aprobadas} de {persistencia_total} fases aprobadas")
    total_casos = (len(CASOS) + integraciones_total + dcg_total
                   + consistencia_total + persistencia_total)
    print("=" * 72)
    print(f" RESUMEN: {aprobados} de {total_casos} casos aprobados")
    print("=" * 72)
    if aprobados != total_casos:
        sys.exit(1)


def evaluar_integraciones(motor):
    """Comprueba escenarios de Streamlit, explicabilidad e inventario."""
    casos = [
        (
            "Diagnóstico con explicación",
            lambda: _caso_diagnostico_explicable(motor),
        ),
        (
            "Síntomas insuficientes y sugerencia",
            lambda: _caso_informacion_insuficiente(motor),
        ),
        (
            "Varias hipótesis posibles",
            lambda: _caso_hipotesis_ambiguas(motor),
        ),
        (
            "Prueba recomendada para RAM",
            lambda: _caso_sugerencia_ram(motor),
        ),
        (
            "Entrada válida sin diagnóstico",
            lambda: _caso_sin_diagnostico(motor),
        ),
        (
            "Inventario completo de hechos y catálogos",
            lambda: _caso_inventario_completo(motor),
        ),
        (
            "Reconocimiento de descripción natural ampliada",
            lambda: _caso_lenguaje_natural_ampliado(motor),
        ),
        (
            "Oración natural completa -> DCG -> diagnóstico",
            lambda: _caso_oracion_a_diagnostico(motor),
        ),
        (
            "Pre-procesamiento numérico -> dato/2 -> R3b",
            lambda: _caso_preprocesamiento(motor),
        ),
    ]
    aprobados = 0
    for nombre, comprobar in casos:
        try:
            ok = comprobar()
        except Exception as error:
            ok = False
            print(f"  Error en {nombre}: {error}")
        aprobados += ok
        print(f"  {nombre}: {'APROBADO' if ok else 'FALLIDO'}")
    return aprobados, len(casos)


def _caso_diagnostico_explicable(motor):
    respuesta = motor.analizar_caso([
        "no_enciende",
        "olor_quemado",
        "prueba(fuente_con_probador, falla)",
    ])
    if respuesta.estado != "ok" or not respuesta.diagnosticos:
        return False
    explicacion = respuesta.explicaciones[0]
    return (
        respuesta.diagnosticos[0].nombre == "fuente_poder_defectuosa"
        and {"R1", "R9", "R21"}.issubset(explicacion.reglas)
        and any("prueba(fuente_con_probador, falla)" in hecho for hecho in explicacion.hechos)
        and any("\\+" in negacion for negacion in explicacion.negaciones)
    )


def _caso_informacion_insuficiente(motor):
    respuesta = motor.analizar_caso(["pantalla_negra"])
    return (
        respuesta.estado == "datos_insuficientes"
        and not respuesta.diagnosticos
        and bool(respuesta.sugerencias)
    )


def _caso_hipotesis_ambiguas(motor):
    respuesta = motor.analizar_caso(["pantalla_negra", "ventiladores_giran"])
    hipotesis = {
        nombre
        for sugerencia in respuesta.sugerencias
        for nombre in sugerencia.hipotesis
    }
    return (
        respuesta.estado == "datos_insuficientes"
        and {"cable_o_monitor_defectuoso", "gpu_defectuosa"}.issubset(hipotesis)
    )


def _caso_sugerencia_ram(motor):
    respuesta = motor.analizar_caso(["pantalla_azul"])
    return (
        bool(respuesta.sugerencias)
        and any("RAM" in sugerencia.dato for sugerencia in respuesta.sugerencias)
        and any("R14" in sugerencia.razon or "R15" in sugerencia.razon
                for sugerencia in respuesta.sugerencias)
    )


def _caso_sin_diagnostico(motor):
    respuesta = motor.analizar_caso(["led_encendido"])
    return (
        respuesta.estado == "datos_insuficientes"
        and not respuesta.diagnosticos
        and any(
            explicacion.nombre == "sin_diagnostico"
            and "R25" in explicacion.reglas
            for explicacion in respuesta.explicaciones
        )
    )


def _caso_inventario_completo(motor):
    inventario = motor.listar_hechos_base()
    return (
        len(inventario) == 13
        and len(inventario["Componentes"]) == 6
        and len(inventario["Síntomas reportables"]) == 20
        and len(inventario["Relaciones síntoma-componente"]) == 23
        and len(inventario["Casos de ejemplo"]) == 8
        and all(inventario.values())
    )


def _caso_lenguaje_natural_ampliado(motor):
    respuesta = motor.consultar_texto("no da video")
    return (
        respuesta.estado == "datos_insuficientes"
        and not respuesta.diagnosticos
        and respuesta.sospechosos
        and respuesta.sospechosos[0][0] == "tarjeta_video"
    )


def _caso_oracion_a_diagnostico(motor):
    respuesta = motor.consultar_texto(
        "el pc va lento, la cpu esta a 97 grados y el ventilador suena muy fuerte"
    )
    return (
        respuesta.hechos_dcg == ["lentitud", "temp_cpu(97)", "ventilador_ruidoso"]
        and [(d.nombre, d.severidad) for d in respuesta.diagnosticos]
        == [("refrigeracion_deficiente", "critica")]
    )


def _caso_preprocesamiento(motor):
    preprocesador = Preprocesador()
    discretos = preprocesador.discretizar(temperatura_cpu=97, uso_disco=93)
    terminos = [hecho.termino for hecho in discretos]
    print(f"    clasificador ({preprocesador.metodo}): {terminos}")
    respuesta = motor.analizar_caso(["ventilador_ruidoso", *terminos])
    return (
        terminos == ["dato(temperatura_cpu, critica)", "dato(uso_disco, critico)"]
        and [(d.nombre, d.severidad) for d in respuesta.diagnosticos]
        == [("refrigeracion_deficiente", "critica")]
        and "R3b" in respuesta.explicaciones[0].reglas
    )


# --------------------------------------------------------------------------- #
#  DCG: oraciones en español -> hechos simbólicos
# --------------------------------------------------------------------------- #
ORACIONES_DCG = [
    ("mi computador no enciende y huele a quemado",
     ["no_enciende", "olor_quemado"]),
    ("La pantalla se pone azul, se reinicia sola y el disco hace clic",
     ["pantalla_azul", "reinicios_aleatorios", "ruido_clic"]),
    ("el pc va lento y la cpu está a 95 grados",
     ["lentitud", "temp_cpu(95)"]),
    ("Al encender hace tres pitidos cortos y la pantalla queda en negro",
     ["pitidos(tres_cortos)", "pantalla_negra"]),
    ("suena un pitido largo y dos cortos",
     ["pitidos(un_largo_dos_cortos)"]),
    ("mi portátil de 7 años pierde la fecha y hora",
     ["hora_incorrecta", "equipo(portatil,7)"]),
    ("la pantalla no muestra imagen pero los ventiladores giran",
     ["pantalla_negra", "ventiladores_giran"]),
    ("tarda mucho en iniciar y el disco duro hace ruido",
     ["arranque_lento", "ruido_clic"]),
    ("aparecen rayas de colores en la pantalla y la imagen se ve distorsionada",
     ["lineas_en_pantalla", "artefactos_video"]),
    ("el led está encendido, el ventilador no gira y se queda congelado",
     ["led_encendido", "ventilador_detenido", "bloqueos"]),
]


def evaluar_dcg(motor):
    """Cada oración debe producir exactamente los hechos esperados."""
    aprobados = 0
    for oracion, esperados in ORACIONES_DCG:
        analisis = motor.parsear_oracion(oracion)
        ok = analisis.hechos == esperados
        aprobados += ok
        print(f"  «{oracion}»")
        print(f"      hechos: {analisis.hechos}  no reconocidas: {analisis.no_reconocidas}"
              f"  -> {'APROBADO' if ok else 'FALLIDO (esperado ' + str(esperados) + ')'}")
    return aprobados, len(ORACIONES_DCG)


# --------------------------------------------------------------------------- #
#  Entregable 4: contradicciones y entradas ambiguas
# --------------------------------------------------------------------------- #
# (entrada formal, tipo de contradicción que debe detectar Prolog)
CONTRADICCIONES = [
    ("no_enciende, ventiladores_giran", "sintomas_incompatibles"),
    ("pantalla_negra, pantalla_azul", "sintomas_incompatibles"),
    ("ventilador_detenido, ventilador_ruidoso", "sintomas_incompatibles"),
    ("disco_no_encontrado, prueba(smart_disco, ok)", "sintomas_incompatibles"),
    ("olor_quemado, ausente(olor_quemado)", "afirmado_y_negado"),
    ("temp_cpu(500)", "lectura_imposible"),
    ("temp_cpu(40), temp_cpu(99)", "lecturas_discrepantes"),
    ("temp_cpu(97), dato(temperatura_cpu, normal)", "nivel_discordante"),
    ("prueba(cambio_cable, ok), prueba(cambio_cable, falla)", "datos_duplicados"),
    ("equipo(portatil, 2), equipo(escritorio, 9)", "datos_duplicados"),
]

# (oración ambigua, hechos que debe extraer la DCG, estado esperado)
ORACIONES_AMBIGUAS = [
    ("mi pc no huele a quemado", ["ausente(olor_quemado)"], "datos_insuficientes"),
    ("el computador si enciende", ["ausente(no_enciende)"], "datos_insuficientes"),
    ("mi pc no prende pero los ventiladores giran",
     ["no_enciende", "ventiladores_giran"], "entrada_contradictoria"),
    ("huele a quemado y no huele a quemado",
     ["olor_quemado", "ausente(olor_quemado)"], "entrada_contradictoria"),
    ("la cpu esta a 200 grados", ["temp_cpu(200)"], "entrada_contradictoria"),
    ("mi portatil de 2 años y mi escritorio de 9 años",
     ["equipo(portatil,2)", "equipo(escritorio,9)"], "entrada_contradictoria"),
    ("no enciende ni huele a quemado",
     ["no_enciende", "ausente(olor_quemado)"], "datos_insuficientes"),
]

# Combinaciones coherentes: la parte I NO debe bloquearlas (falsos positivos).
COHERENTES = [
    "no_enciende, led_encendido",
    "no_enciende, prueba(fuente_con_probador, ok), pitidos(un_largo_tres_cortos)",
    "temp_cpu(90), temp_cpu(95), ventilador_ruidoso",
    "temp_cpu(97), dato(temperatura_cpu, critica)",
    "olor_quemado, ausente(lentitud)",
]


def evaluar_consistencia(motor):
    """Contradicciones, ambigüedad en la DCG y falsos positivos."""
    aprobados = 0
    total = 0

    def registrar(descripcion, ok, detalle=""):
        nonlocal aprobados, total
        total += 1
        aprobados += bool(ok)
        print(f"  {descripcion}: {'APROBADO' if ok else 'FALLIDO'}")
        if detalle:
            print(f"      {detalle}")

    print("  -- Contradicciones que Prolog debe bloquear --")
    for entrada, tipo in CONTRADICCIONES:
        resp = motor.consultar_texto(entrada)
        tipos = [c.tipo for c in resp.contradicciones]
        ok = (resp.estado == "entrada_contradictoria"
              and not resp.diagnosticos and tipo in tipos)
        registrar(f"[{tipo}] {entrada}", ok,
                  f"estado={resp.estado}, tipos={tipos}")

    print("  -- Entradas ambiguas en lenguaje natural (DCG) --")
    for oracion, hechos, estado in ORACIONES_AMBIGUAS:
        resp = motor.consultar_texto(oracion)
        ok = resp.hechos_dcg == hechos and resp.estado == estado
        registrar(f"«{oracion}»", ok,
                  f"hechos={resp.hechos_dcg}, estado={resp.estado}")

    print("  -- Coherentes (no deben bloquearse) --")
    for entrada in COHERENTES:
        resp = motor.consultar_texto(entrada)
        registrar(entrada, resp.estado != "entrada_contradictoria",
                  f"estado={resp.estado}")

    print("  -- analizar_caso/2 también bloquea --")
    resp = motor.analizar_caso(["no_enciende", "ventiladores_giran"])
    registrar("analizar_caso([no_enciende, ventiladores_giran])",
              resp.estado == "entrada_contradictoria" and not resp.explicaciones
              and not resp.sugerencias and len(resp.contradicciones) == 1,
              formatear_respuesta(resp).replace("\n", " | "))

    print("  -- Batería de estrés en Prolog (pruebas_estres.pl) --")
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pruebas_estres.pl")
    try:
        proceso = subprocess.run(
            ["swipl", "-q", "-f", "none", "-g", "correr_pruebas", "-t", "halt", ruta],
            cwd=os.path.dirname(ruta), capture_output=True, text=True,
            encoding="utf-8", timeout=120)
        ultima = [linea for linea in proceso.stdout.splitlines() if "RESULTADO" in linea]
        registrar("swipl pruebas_estres.pl", proceso.returncode == 0,
                  ultima[-1] if ultima else proceso.stderr.strip()[:200])
    except (OSError, subprocess.TimeoutExpired) as error:
        registrar("swipl pruebas_estres.pl", False, str(error))
    return aprobados, total


# --------------------------------------------------------------------------- #
#  Persistencia de reglas aprendidas (cada fase en un proceso nuevo)
# --------------------------------------------------------------------------- #
REGLA_PRUEBA = dict(
    id_diagnostico="fuente_sobrecargada",
    nombre="Fuente de poder sobrecargada",
    componente="fuente_poder",
    requeridas=["apagados_repentinos", "olor_quemado"],
    excluyentes=["no_enciende"],
    certeza="media",
    gravedad="alta",
    accion="Revisar el consumo del equipo e instalar una fuente de mayor potencia.",
)
ORACION_PRUEBA = "se apaga de repente y huele a quemado"
ALIAS_PRUEBA = ("se muere el pc", "apagados_repentinos")
FASES = [
    ("crear", "Crear regla en caliente (assertz + escritura en el .pl)"),
    ("verificar", "Reinicio: la regla y el alias siguen en el .pl y diagnostican"),
    ("eliminar", "Eliminar regla y alias (retract + bloque del .pl)"),
    ("verificar_eliminada", "Reinicio: la regla ya no existe"),
]


def evaluar_persistencia():
    carpeta = tempfile.mkdtemp(prefix="harddiag_prueba_")
    copia = os.path.join(carpeta, "base_conocimiento.pl")
    shutil.copyfile(RUTA_BASE_REAL, copia)
    print(f"  Copia temporal de la base: {copia}")
    aprobadas = 0
    try:
        for fase, descripcion in FASES:
            proceso = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--fase", fase, copia],
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            try:
                resultado = json.loads(proceso.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                resultado = {"ok": False, "detalle": proceso.stderr.strip()[-400:]}
            aprobadas += bool(resultado.get("ok"))
            print(f"  [{fase}] {descripcion}: {'APROBADO' if resultado.get('ok') else 'FALLIDO'}")
            for clave, valor in resultado.items():
                if clave != "ok":
                    print(f"      {clave}: {valor}")
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
    return aprobadas, len(FASES)


def _bloque_del_archivo(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        texto = archivo.read()
    inicio = texto.index("=== INICIO CONOCIMIENTO APRENDIDO")
    return texto[inicio:texto.index("=== FIN CONOCIMIENTO APRENDIDO")]


def ejecutar_fase(fase, ruta):
    """Corre en un proceso nuevo: carga la copia del .pl desde cero."""
    motor = MotorInferencia(ruta, ruta_alias=None)

    def ids():
        return [regla.id for regla in motor.listar_reglas_aprendidas()]

    def diagnosticos(texto):
        return [d.nombre for d in motor.consultar_texto(texto).diagnosticos]

    if fase == "crear":
        antes = diagnosticos(ORACION_PRUEBA)
        motor.crear_regla(**REGLA_PRUEBA)
        motor.aprender_alias(*ALIAS_PRUEBA)
        despues = diagnosticos(ORACION_PRUEBA)
        reporte = motor.analizar_caso(["apagados_repentinos", "olor_quemado"])
        bloque = _bloque_del_archivo(ruta)
        return {
            "ok": "fuente_sobrecargada" not in antes
            and "fuente_sobrecargada" in despues
            and "R26" in reporte.explicaciones[0].reglas
            and "regla_aprendida(fuente_sobrecargada" in bloque
            and "alias_aprendido(apagados_repentinos" in bloque,
            "diagnósticos antes": antes,
            "diagnósticos después": despues,
            "reglas de la explicación": reporte.explicaciones[0].reglas,
        }
    if fase == "verificar":
        con_alias = diagnosticos("se muere el pc y huele a quemado")
        excluido = diagnosticos("no enciende, se apaga de repente y huele a quemado")
        return {
            "ok": ids() == ["fuente_sobrecargada"]
            and con_alias == ["fuente_sobrecargada"]
            and "fuente_sobrecargada" not in excluido,
            "reglas cargadas del .pl": ids(),
            "con el alias aprendido": con_alias,
            "con la condición excluyente (no_enciende)": excluido,
        }
    if fase == "eliminar":
        eliminada = motor.eliminar_regla("fuente_sobrecargada")
        alias_eliminado = motor.eliminar_alias_aprendido(ALIAS_PRUEBA[0])
        bloque = _bloque_del_archivo(ruta)
        return {
            "ok": eliminada and alias_eliminado and not ids()
            and "regla_aprendida" not in bloque and "alias_aprendido" not in bloque,
            "reglas en memoria": ids(),
        }
    if fase == "verificar_eliminada":
        despues = diagnosticos(ORACION_PRUEBA)
        return {
            "ok": not ids() and "fuente_sobrecargada" not in despues,
            "reglas cargadas del .pl": ids(),
            "diagnósticos": despues,
        }
    raise ValueError(f"Fase desconocida: {fase}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--fase":
        print(json.dumps(ejecutar_fase(sys.argv[2], sys.argv[3]), ensure_ascii=False))
        sys.exit(0)
    sys.exit(main())
