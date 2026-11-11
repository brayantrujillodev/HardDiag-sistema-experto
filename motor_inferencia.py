"""
motor_inferencia.py
===================
Puente Python <-> SWI-Prolog (PySwip) del Sistema Experto de Diagnóstico y
Soporte Técnico para Fallos de Hardware.

RESPONSABILIDAD DE ESTE MÓDULO
    Python solo hace cuatro cosas:
      1. Cargar ``base_conocimiento.pl`` en el motor de SWI-Prolog.
      2. Enviar los datos de entrada (o la oración libre, que analiza la DCG
         de Prolog) e invocar los predicados de Prolog.
      3. Recibir las listas de resultados y presentarlas en consola.
      4. Persistir en el archivo ``.pl`` el conocimiento que el experto
         inyecta en caliente con ``assertz/1``.

    NO hay lógica de inferencia, descarte, validación de reglas, análisis del
    lenguaje ni cálculo de severidad aquí: todo eso vive en Prolog.
"""

from __future__ import annotations

import os
import json
import re
import tempfile
import unicodedata
from threading import RLock
from dataclasses import dataclass, field
from typing import Iterable

from pyswip import Prolog

RUTA_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "base_conocimiento.pl")
# Archivo de la versión anterior del modo experto. Si existe, sus alias se
# migran una sola vez al bloque de conocimiento aprendido del archivo .pl.
RUTA_ALIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "aliases_aprendidos.json")

MARCA_INICIO = "%% === INICIO CONOCIMIENTO APRENDIDO (no editar a mano) ==="
MARCA_FIN = "%% === FIN CONOCIMIENTO APRENDIDO ==="

PATRON_ID = re.compile(r"[a-z][a-z0-9_]*")
# Un elemento de la sintaxis formal: identificador o término como temp_cpu(90).
PATRON_FORMAL = re.compile(r"[a-z][a-z0-9_]*(\(.*\))?")
CONDICIONES_ESPECIALES = ("temp_cpu_alta", "equipo_antiguo")


# --------------------------------------------------------------------------- #
#  Estructuras de datos (solo transportan lo que devuelve Prolog)
# --------------------------------------------------------------------------- #
@dataclass
class Diagnostico:
    """Un diagnóstico tal como lo entrega Prolog."""
    nombre: str
    certeza: str
    severidad: str
    nivel_danio: str
    prioridad: int
    cobertura: int
    accion: str


@dataclass
class Respuesta:
    """Respuesta completa de ``consultar_caso/2``."""
    estado: str
    diagnosticos: list[Diagnostico] = field(default_factory=list)
    sospechosos: list[tuple[str, int]] = field(default_factory=list)
    descartados: list[str] = field(default_factory=list)
    explicaciones: list[ExplicacionDiagnostico] = field(default_factory=list)
    sugerencias: list[Sugerencia] = field(default_factory=list)
    hechos_dcg: list[str] = field(default_factory=list)
    no_reconocidas: list[str] = field(default_factory=list)


@dataclass
class ExplicacionDiagnostico:
    """Traza de reglas, hechos y exclusiones devuelta por Prolog."""
    nombre: str
    certeza: str
    severidad: str
    nivel_danio: str
    prioridad: int
    cobertura: int
    accion: str
    reglas: list[str] = field(default_factory=list)
    hechos: list[str] = field(default_factory=list)
    negaciones: list[str] = field(default_factory=list)
    alternativas_descartadas: list[str] = field(default_factory=list)


@dataclass
class Sugerencia:
    """Dato o prueba priorizada por Prolog para completar el caso."""
    dato: str
    razon: str
    hipotesis: list[str] = field(default_factory=list)


@dataclass
class AnalisisOracion:
    """Resultado de ``parsear_oracion_texto/3`` (la DCG de Prolog)."""
    hechos: list[str] = field(default_factory=list)
    no_reconocidas: list[str] = field(default_factory=list)


@dataclass
class ReglaAprendida:
    """Diagnóstico creado por el experto (hecho ``regla_aprendida/8``)."""
    id: str
    nombre: str
    componente: str
    requeridas: list[str]
    excluyentes: list[str]
    certeza: str
    gravedad: str
    accion: str


# --------------------------------------------------------------------------- #
#  Motor
# --------------------------------------------------------------------------- #
class MotorInferencia:
    """Carga la base de conocimiento y expone funciones que consultan Prolog."""

    def __init__(self, ruta_base: str = RUTA_BASE, ruta_alias: str = RUTA_ALIAS) -> None:
        if not os.path.isfile(ruta_base):
            raise FileNotFoundError(f"No se encontró la base de conocimiento: {ruta_base}")
        self._prolog = Prolog()
        self._lock = RLock()
        self._ruta_base = os.path.abspath(ruta_base)
        self._ruta_alias = ruta_alias
        # PySwip espera rutas con "/" aunque el sistema operativo sea Windows.
        list(self._prolog.query(f"consult({self._atomo(self._ruta_base.replace(os.sep, '/'))})"))
        self._migrar_aliases_json()

    @property
    def ruta_base(self) -> str:
        """Archivo .pl cargado; allí se persiste el conocimiento aprendido."""
        return self._ruta_base

    # -- utilidades internas ------------------------------------------------ #
    @staticmethod
    def _atomo(texto: str) -> str:
        """Escapa un texto para enviarlo a Prolog como átomo entre comillas."""
        texto = re.sub(r"[\r\n\t]+", " ", str(texto))
        return "'" + texto.replace("\\", "\\\\").replace("'", "\\'") + "'"

    @staticmethod
    def _lista_prolog(items: Iterable[str]) -> str:
        """Arma el texto ``[a, b, c]`` con los elementos (términos Prolog)."""
        return "[" + ", ".join(items) + "]"

    def _una_solucion(self, consulta: str) -> dict:
        """Ejecuta una consulta y devuelve su primera solución."""
        with self._lock:
            soluciones = list(self._prolog.query(consulta, maxresult=1))
        if not soluciones:
            raise RuntimeError(f"Prolog no devolvió solución para: {consulta}")
        return soluciones[0]

    def _se_cumple(self, consulta: str) -> bool:
        with self._lock:
            return bool(list(self._prolog.query(consulta, maxresult=1)))

    @staticmethod
    def _a_respuesta(crudo: list) -> Respuesta:
        """Convierte la lista que devuelve Prolog en una ``Respuesta``."""
        estado, diagnosticos, sospechosos, descartados = crudo
        return Respuesta(
            estado=str(estado),
            diagnosticos=[
                Diagnostico(str(d[0]), str(d[1]), str(d[2]), str(d[3]),
                            int(d[4]), int(d[5]), str(d[6]))
                for d in diagnosticos
            ],
            sospechosos=[(str(s[0]), int(s[1])) for s in sospechosos],
            descartados=[str(x) for x in descartados],
        )

    # -- lenguaje natural (DCG) ---------------------------------------------- #
    def parsear_oracion(self, texto: str) -> AnalisisOracion:
        """Envía la oración a la DCG de Prolog y devuelve los hechos extraídos.

        Invoca ``parsear_oracion_texto(+Texto, -Hechos, -NoReconocidas)``:
        Prolog tokeniza, analiza con ``phrase/2`` y responde con los hechos
        simbólicos (``no_enciende``, ``temp_cpu(95)``...) y las palabras que
        no pertenecen a su léxico.
        """
        if texto is None or not str(texto).strip():
            return AnalisisOracion()
        sol = self._una_solucion(
            f"parsear_oracion_texto({self._atomo(texto)}, Hechos, NoReconocidas)"
        )
        return AnalisisOracion(
            hechos=[str(h) for h in sol["Hechos"]],
            no_reconocidas=[str(p) for p in sol["NoReconocidas"]],
        )

    # -- consultas a Prolog ------------------------------------------------- #
    def consultar_texto(self, texto: str) -> Respuesta:
        """Consulta con texto: sintaxis formal, oración libre o una mezcla.

        Los elementos formales separados por comas (``no_enciende``,
        ``prueba(cambio_cable, ok)``) se envían tal cual; las frases en
        español se analizan con la DCG de Prolog.
        """
        if texto is None or not str(texto).strip():
            return Respuesta("entrada_vacia")

        partes = self._split_top_level(str(texto))
        if not partes:
            return Respuesta("entrada_vacia")

        formales = [p for p in partes if PATRON_FORMAL.fullmatch(p)]
        naturales = [p for p in partes if not PATRON_FORMAL.fullmatch(p)]
        analisis = self.parsear_oracion(", ".join(naturales)) if naturales else AnalisisOracion()

        lista = list(dict.fromkeys(formales + analisis.hechos))
        if not lista:
            respuesta = Respuesta("entrada_invalida")
        else:
            respuesta = self.consultar_lista(lista)
        respuesta.hechos_dcg = analisis.hechos
        respuesta.no_reconocidas = analisis.no_reconocidas
        return respuesta

    @staticmethod
    def _split_top_level(texto: str) -> list[str]:
        """Divide entradas por comas que estén fuera de paréntesis."""
        partes: list[str] = []
        actual: list[str] = []
        profundidad = 0
        for caracter in texto:
            if caracter == "(":
                profundidad += 1
            elif caracter == ")" and profundidad > 0:
                profundidad -= 1
            elif caracter == "," and profundidad == 0:
                valor = "".join(actual).strip()
                if valor:
                    partes.append(valor)
                actual = []
                continue
            actual.append(caracter)
        valor = "".join(actual).strip()
        if valor:
            partes.append(valor)
        return partes

    @staticmethod
    def _normalizar_alias(texto: str) -> str:
        """Normaliza una frase para comparar alias sin distinguir mayúsculas."""
        texto_norm = unicodedata.normalize("NFKD", texto.lower())
        texto_norm = "".join(
            caracter for caracter in texto_norm
            if not unicodedata.combining(caracter)
        )
        texto_norm = re.sub(r"[^a-z0-9\s]+", " ", texto_norm)
        return re.sub(r"\s+", " ", texto_norm).strip()

    def consultar_lista(self, items: Iterable[str]) -> Respuesta:
        """Invoca ``consultar_caso(+Entrada, -Respuesta)`` con una lista."""
        consulta = f"consultar_caso({self._lista_prolog(items)}, R)"
        return self._a_respuesta(self._una_solucion(consulta)["R"])

    def analizar_caso(self, items: Iterable[str]) -> Respuesta:
        """Consulta el diagnóstico, la traza y datos faltantes en Prolog."""
        consulta = f"analizar_caso({self._lista_prolog(items)}, R)"
        crudo = self._una_solucion(consulta)["R"]
        estado, diagnosticos, sospechosos, descartados, explicaciones, sugerencias = crudo
        respuesta = self._a_respuesta(
            [estado, diagnosticos, sospechosos, descartados]
        )
        respuesta.explicaciones = [
            ExplicacionDiagnostico(
                nombre=str(item[0]),
                certeza=str(item[1]),
                severidad=str(item[2]),
                nivel_danio=str(item[3]),
                prioridad=int(item[4]),
                cobertura=int(item[5]),
                accion=str(item[6]),
                reglas=[str(regla) for regla in item[7]],
                hechos=[str(hecho) for hecho in item[8]],
                negaciones=[str(negacion) for negacion in item[9]],
                alternativas_descartadas=[str(alt) for alt in item[10]],
            )
            for item in explicaciones
        ]
        respuesta.sugerencias = [
            Sugerencia(
                dato=str(item[0]),
                razon=str(item[1]),
                hipotesis=[str(hipotesis) for hipotesis in item[2]],
            )
            for item in sugerencias
        ]
        return respuesta

    def diagnosticar_todos(self, items: Iterable[str]) -> tuple[str, list[Diagnostico]]:
        """Invoca ``diagnosticar_todos(+Entrada, -Estado, -Diagnosticos)``."""
        consulta = f"diagnosticar_todos({self._lista_prolog(items)}, E, D)"
        sol = self._una_solucion(consulta)
        diagnosticos = [Diagnostico(str(d[0]), str(d[1]), str(d[2]), str(d[3]),
                                    int(d[4]), int(d[5]), str(d[6]))
                        for d in sol["D"]]
        return str(sol["E"]), diagnosticos

    def listar_sintomas(self) -> list[tuple[str, str]]:
        """Invoca ``listar_sintomas(-Lista)``."""
        sol = self._una_solucion("listar_sintomas(L)")
        return [(str(s[0]), str(s[1])) for s in sol["L"]]

    def listar_componentes(self) -> list[tuple[str, str]]:
        with self._lock:
            return [(str(r["C"]), str(r["D"]))
                    for r in self._prolog.query("componente(C, D)")]

    def listar_condiciones_especiales(self) -> list[str]:
        """Condiciones no sintomáticas que puede usar una regla aprendida."""
        with self._lock:
            pitidos = [f"pitidos({r['P']})" for r in self._prolog.query("codigo_pitido(P, _)")]
            pruebas = [f"prueba({r['N']}, {r['R']})"
                       for r in self._prolog.query("prueba_catalogo(N, _), resultado_prueba(R, _)")]
        return [*CONDICIONES_ESPECIALES, *pitidos, *pruebas]

    # -- alias aprendidos ------------------------------------------------------ #
    def listar_aliases(self) -> list[tuple[str, str]]:
        """Lista todos los alias (base y aprendidos) que usa la DCG."""
        sol = self._una_solucion("listar_aliases(L)")
        return [(str(item[0]), str(item[1])) for item in sol["L"]]

    def listar_aliases_aprendidos(self) -> list[tuple[str, str]]:
        """Devuelve solo las asociaciones personalizadas persistidas por el experto."""
        sol = self._una_solucion("listar_aliases_aprendidos(L)")
        return [(str(item[0]), str(item[1])) for item in sol["L"]]

    def aprender_alias(self, frase: str, sintoma: str) -> bool:
        """Inyecta un alias con ``assertz/1`` y lo persiste en el archivo .pl."""
        frase = " ".join(frase.split())
        sintoma = sintoma.strip()
        if not frase or len(frase) > 120 or not PATRON_ID.fullmatch(sintoma):
            return False

        with self._lock:
            if not self._se_cumple(f"sintoma_catalogo({sintoma}, _)"):
                return False
            normalizada = self._normalizar_alias(frase)
            coincidencias = [
                nombre for nombre, alias in self.listar_aliases()
                if self._normalizar_alias(alias) == normalizada
            ]
            if coincidencias:
                return all(nombre == sintoma for nombre in coincidencias)

            if not self._se_cumple(f"agregar_alias({self._atomo(frase)}, {sintoma})"):
                return False
            try:
                self._persistir_conocimiento()
            except OSError:
                self._se_cumple(f"olvidar_alias({sintoma}, {self._atomo(frase)})")
                raise
        return True

    def eliminar_alias_aprendido(self, frase: str) -> bool:
        """Elimina un alias personalizado de la memoria y del archivo .pl."""
        normalizada = self._normalizar_alias(frase)
        if not normalizada:
            return False

        with self._lock:
            encontrado = next(
                (
                    (sintoma, alias) for sintoma, alias in self.listar_aliases_aprendidos()
                    if self._normalizar_alias(alias) == normalizada
                ),
                None,
            )
            if encontrado is None:
                return False
            sintoma, alias = encontrado
            if not self._se_cumple(f"olvidar_alias({sintoma}, {self._atomo(alias)})"):
                return False
            try:
                self._persistir_conocimiento()
            except OSError:
                self._se_cumple(f"assertz(alias_aprendido({sintoma}, {self._atomo(alias)}))")
                raise
        return True

    def _migrar_aliases_json(self) -> None:
        """Pasa los alias del JSON antiguo al archivo .pl y renombra el JSON."""
        if not self._ruta_alias or not os.path.exists(self._ruta_alias):
            return
        try:
            with open(self._ruta_alias, encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"No se pudieron cargar los alias aprendidos ({self._ruta_alias}): {error}"
            ) from error
        if not isinstance(datos, list):
            raise RuntimeError(
                f"El archivo de alias aprendidos no contiene una lista: {self._ruta_alias}"
            )

        with self._lock:
            agregados = 0
            for item in datos:
                if not isinstance(item, dict):
                    raise RuntimeError(f"Registro inválido en {self._ruta_alias}")
                frase = item.get("frase")
                sintoma = item.get("sintoma")
                if not isinstance(frase, str) or not isinstance(sintoma, str):
                    raise RuntimeError(f"Registro inválido en {self._ruta_alias}")
                frase = " ".join(frase.split())
                sintoma = sintoma.strip()
                if not frase or len(frase) > 120 or not PATRON_ID.fullmatch(sintoma):
                    raise RuntimeError(f"Alias inválido en {self._ruta_alias}: {frase!r}")
                if self._se_cumple(f"agregar_alias({self._atomo(frase)}, {sintoma})"):
                    agregados += 1
            if agregados:
                self._persistir_conocimiento()
            os.replace(self._ruta_alias, self._ruta_alias + ".migrado")

    # -- reglas aprendidas (modo experto) ----------------------------------- #
    def listar_reglas_aprendidas(self) -> list[ReglaAprendida]:
        """Invoca ``listar_reglas_aprendidas(-Lista)``."""
        sol = self._una_solucion("listar_reglas_aprendidas(L)")
        return [
            ReglaAprendida(
                id=str(r[0]), nombre=str(r[1]), componente=str(r[2]),
                requeridas=[str(c) for c in r[3]],
                excluyentes=[str(c) for c in r[4]],
                certeza=str(r[5]), gravedad=str(r[6]), accion=str(r[7]),
            )
            for r in sol["L"]
        ]

    def crear_regla(
        self,
        id_diagnostico: str,
        nombre: str,
        componente: str,
        requeridas: list[str],
        excluyentes: list[str],
        certeza: str,
        gravedad: str,
        accion: str,
    ) -> ReglaAprendida:
        """Valida en Prolog, inyecta con ``assertz/1`` y persiste en el .pl.

        Si la escritura del archivo falla, la regla se retira de la memoria
        para que memoria y archivo no queden desincronizados.
        """
        id_diagnostico = id_diagnostico.strip()
        nombre = " ".join(nombre.split())
        accion = " ".join(accion.split())
        if not PATRON_ID.fullmatch(id_diagnostico) or len(id_diagnostico) > 60:
            raise ValueError(
                "El identificador debe empezar con una letra minúscula y usar solo "
                "minúsculas, números y guion bajo (máximo 60 caracteres)."
            )
        if not nombre or len(nombre) > 120:
            raise ValueError("Escribe un nombre legible de hasta 120 caracteres.")
        if not accion or len(accion) > 400:
            raise ValueError("Escribe la acción recomendada (hasta 400 caracteres).")
        for valor in (componente, certeza, gravedad):
            if not PATRON_ID.fullmatch(valor):
                raise ValueError(f"Valor inválido: {valor!r}")
        condiciones_validas = {s for s, _ in self.listar_sintomas()}
        condiciones_validas.update(self.listar_condiciones_especiales())
        for condicion in [*requeridas, *excluyentes]:
            if condicion not in condiciones_validas:
                raise ValueError(f"Condición desconocida: {condicion!r}")

        argumentos = ", ".join([
            id_diagnostico,
            self._atomo(nombre),
            componente,
            self._lista_prolog(requeridas),
            self._lista_prolog(excluyentes),
            certeza,
            gravedad,
            self._atomo(accion),
        ])
        with self._lock:
            if self._se_cumple(f"gravedad({id_diagnostico}, _)"):
                raise ValueError(f"Ya existe un diagnóstico con el identificador «{id_diagnostico}».")
            if not self._se_cumple(f"validar_regla({argumentos})"):
                raise ValueError(
                    "Prolog rechazó la regla: revisa que tenga al menos un síntoma "
                    "requerido y que ninguna condición sea a la vez requerida y excluyente."
                )
            self._prolog.assertz(f"regla_aprendida({argumentos})")
            try:
                self._persistir_conocimiento()
            except OSError:
                self._se_cumple(f"olvidar_regla({id_diagnostico})")
                raise
        return next(r for r in self.listar_reglas_aprendidas() if r.id == id_diagnostico)

    def eliminar_regla(self, id_diagnostico: str) -> bool:
        """Retira la regla con ``retract/1`` y la quita del bloque del .pl."""
        if not PATRON_ID.fullmatch(id_diagnostico):
            return False
        with self._lock:
            respaldo = next(
                (r for r in self.listar_reglas_aprendidas() if r.id == id_diagnostico), None
            )
            if respaldo is None or not self._se_cumple(f"olvidar_regla({id_diagnostico})"):
                return False
            try:
                self._persistir_conocimiento()
            except OSError:
                self._prolog.assertz(
                    "regla_aprendida(" + ", ".join([
                        respaldo.id, self._atomo(respaldo.nombre), respaldo.componente,
                        self._lista_prolog(respaldo.requeridas),
                        self._lista_prolog(respaldo.excluyentes),
                        respaldo.certeza, respaldo.gravedad, self._atomo(respaldo.accion),
                    ]) + ")"
                )
                raise
        return True

    # -- persistencia en el archivo .pl -------------------------------------- #
    def _persistir_conocimiento(self) -> None:
        """Reescribe el bloque de conocimiento aprendido de ``base_conocimiento.pl``.

        El contenido lo genera Prolog (``contenido_aprendido/1``, con
        ``portray_clause/1``) a partir de lo que hay en memoria. La escritura es
        atómica: se escribe un archivo temporal en la misma carpeta y luego se
        reemplaza el original con ``os.replace``.
        """
        contenido = str(self._una_solucion("contenido_aprendido(T)")["T"])
        with open(self._ruta_base, encoding="utf-8", newline="") as archivo:
            texto = archivo.read()
        salto = "\r\n" if "\r\n" in texto else "\n"
        cuerpo = contenido.replace("\r\n", "\n").strip("\n")
        lineas = [MARCA_INICIO, *(cuerpo.split("\n") if cuerpo else []), MARCA_FIN]
        bloque = salto.join(lineas)

        inicio = texto.find(MARCA_INICIO)
        fin = texto.find(MARCA_FIN, inicio + 1) if inicio != -1 else -1
        if inicio != -1 and fin != -1:
            nuevo = texto[:inicio] + bloque + texto[fin + len(MARCA_FIN):]
        else:
            nuevo = texto.rstrip("\r\n") + salto * 2 + bloque + salto

        carpeta = os.path.dirname(self._ruta_base)
        archivo_temporal = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=carpeta,
                prefix=".base_conocimiento-", suffix=".tmp", delete=False,
            ) as archivo:
                archivo_temporal = archivo.name
                archivo.write(nuevo)
            os.replace(archivo_temporal, self._ruta_base)
        except OSError:
            if archivo_temporal and os.path.exists(archivo_temporal):
                os.remove(archivo_temporal)
            raise

    def listar_hechos_base(self) -> dict[str, list[str]]:
        """Devuelve los hechos y elementos de catálogos definidos en Prolog."""
        consultas = [
            ("Componentes", "componente(Id, Descripcion)",
             lambda r: f"componente({r['Id']}, {r['Descripcion']})"),
            ("Síntomas reportables", "sintoma_catalogo(Sintoma, Descripcion)",
             lambda r: f"sintoma_catalogo({r['Sintoma']}, {r['Descripcion']})"),
            ("Relaciones síntoma-componente", "sintoma_componente(Sintoma, Componente)",
             lambda r: f"sintoma_componente({r['Sintoma']}, {r['Componente']})"),
            ("Patrones de pitidos", "codigo_pitido(Patron, Componente)",
             lambda r: f"codigo_pitido({r['Patron']}, {r['Componente']})"),
            ("Pruebas", "prueba_catalogo(Nombre, Descripcion)",
             lambda r: f"prueba_catalogo({r['Nombre']}, {r['Descripcion']})"),
            ("Resultados de pruebas", "resultado_prueba(Resultado, Descripcion)",
             lambda r: f"resultado_prueba({r['Resultado']}, {r['Descripcion']})"),
            ("Tipos de equipo", "tipo_equipo(Tipo, Descripcion)",
             lambda r: f"tipo_equipo({r['Tipo']}, {r['Descripcion']})"),
            ("Umbrales", "umbral(Parametro, Valor)",
             lambda r: f"umbral({r['Parametro']}, {r['Valor']})"),
            ("Gravedad base por diagnóstico", "gravedad(Diagnostico, Nivel)",
             lambda r: f"gravedad({r['Diagnostico']}, {r['Nivel']})"),
            ("Pesos de severidad", "peso_gravedad(Nivel, Peso)",
             lambda r: f"peso_gravedad({r['Nivel']}, {r['Peso']})"),
            ("Acciones recomendadas", "accion(Diagnostico, Accion)",
             lambda r: f"accion({r['Diagnostico']}, {r['Accion']})"),
            ("Evidencia típica por diagnóstico", "evidencia_tipica(Diagnostico, Evidencia)",
             lambda r: f"evidencia_tipica({r['Diagnostico']}, "
                       f"[{', '.join(map(str, r['Evidencia']))}])"),
            ("Casos de ejemplo", "caso_ejemplo(Nombre, Entrada)",
             lambda r: f"caso_ejemplo({r['Nombre']}, "
                       f"[{', '.join(map(str, r['Entrada']))}])"),
        ]
        with self._lock:
            return {
                seccion: [formatear(fila) for fila in self._prolog.query(consulta)]
                for seccion, consulta, formatear in consultas
            }


# --------------------------------------------------------------------------- #
#  Presentación en consola
# --------------------------------------------------------------------------- #
_MENSAJES_ESTADO = {
    "ok": "Diagnóstico generado.",
    "datos_insuficientes": "Datos insuficientes: ninguna regla se cumple con la información dada.",
    "entrada_vacia": "No se ingresó ninguna condición.",
    "entrada_invalida": "Ninguna condición válida en la entrada.",
}


def formatear_respuesta(resp: Respuesta) -> str:
    """Devuelve la respuesta de Prolog como texto legible para la consola."""
    lineas = [f"Estado: {resp.estado} - {_MENSAJES_ESTADO.get(resp.estado, '')}"]
    if resp.hechos_dcg:
        lineas.append("Hechos extraídos por la DCG: " + ", ".join(resp.hechos_dcg))
    if resp.no_reconocidas:
        lineas.append("Palabras no reconocidas por la DCG: " + ", ".join(resp.no_reconocidas))
    if resp.descartados:
        lineas.append("Condiciones no reconocidas (ignoradas): "
                      + ", ".join(resp.descartados))
    if resp.diagnosticos:
        lineas.append("Diagnósticos (de mayor a menor prioridad):")
        for i, d in enumerate(resp.diagnosticos, start=1):
            lineas.append(f"  {i}. {d.nombre}  |  nivel de daño: {d.nivel_danio}  |  "
                          f"severidad: {d.severidad}  |  "
                          f"certeza: {d.certeza}  |  prioridad: {d.prioridad}  |  "
                          f"evidencia: {d.cobertura}%")
            lineas.append(f"     Acción: {d.accion}")
    elif resp.sospechosos:
        lineas.append("Componentes sospechosos (de más a menos indicios):")
        for comp, cantidad in resp.sospechosos:
            lineas.append(f"  - {comp} ({cantidad} indicio(s))")
        lineas.append("Sugerencia: realice más pruebas y vuelva a consultar.")
    return "\n".join(lineas)
