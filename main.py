"""Interfaz Streamlit de HardDiag. La inferencia y sus explicaciones viven en Prolog."""

from __future__ import annotations

import os
import re
import unicodedata

import streamlit as st
from pyswip.prolog import PrologError

from autenticacion import ROL_EXPERTO, autenticar, cargar_credenciales
from motor_inferencia import (
    MARCA_FIN,
    MARCA_INICIO,
    AnalisisOracion,
    MotorInferencia,
    Respuesta,
)
from preprocesamiento import VARIABLES, Preprocesador

RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logohardiag.jpeg")


@st.cache_resource
def obtener_motor() -> MotorInferencia:
    """Mantiene una única instancia del motor Prolog entre recargas de Streamlit.

    HARDDIAG_BASE_CONOCIMIENTO permite apuntar a otra copia del archivo .pl
    (por ejemplo, para ensayar la demostración sin tocar la base real).
    """
    ruta = os.environ.get("HARDDIAG_BASE_CONOCIMIENTO")
    return MotorInferencia(ruta) if ruta else MotorInferencia()


@st.cache_resource
def obtener_preprocesador() -> Preprocesador:
    """Entrena una sola vez el clasificador de lecturas numéricas."""
    return Preprocesador()


NOMBRES_DIAGNOSTICO = {
    "fuente_poder_defectuosa": "Fuente de poder defectuosa",
    "cable_o_monitor_defectuoso": "Cable o monitor defectuoso",
    "gpu_defectuosa": "Tarjeta gráfica defectuosa",
    "placa_base_defectuosa": "Placa base defectuosa",
    "refrigeracion_deficiente": "Refrigeración deficiente",
    "ram_mal_asentada": "Memoria RAM mal asentada",
    "ram_defectuosa": "Memoria RAM defectuosa",
    "disco_fallando": "Disco de almacenamiento fallando",
    "bateria_cmos_agotada": "Batería CMOS agotada",
}
DESCRIPCIONES_SINTOMA = {
    "no_enciende": "El equipo no enciende",
    "led_encendido": "Alguna luz indicadora está encendida",
    "apagados_repentinos": "El equipo se apaga de repente",
    "olor_quemado": "Hay olor a quemado",
    "pitidos_arranque": "Se oyen pitidos al arrancar",
    "hora_incorrecta": "La fecha y la hora se pierden",
    "error_bios": "Aparece un error en la BIOS",
    "reinicios_aleatorios": "El equipo se reinicia solo",
    "ventilador_ruidoso": "El ventilador hace ruido excesivo",
    "ventilador_detenido": "El ventilador no gira",
    "ventiladores_giran": "Los ventiladores giran al encender",
    "lentitud": "El equipo funciona muy lento",
    "pantalla_azul": "Aparece una pantalla azul",
    "bloqueos": "El equipo se congela",
    "arranque_lento": "El inicio tarda demasiado",
    "ruido_clic": "El disco hace clics",
    "disco_no_encontrado": "Aparece el aviso «disco no encontrado»",
    "pantalla_negra": "La pantalla queda en negro",
    "lineas_en_pantalla": "Aparecen líneas en la pantalla",
    "artefactos_video": "Aparecen artefactos en la imagen",
}
NOMBRES_PATRON_PITIDOS = {
    "tres_cortos": "tres pitidos cortos",
    "un_largo_dos_cortos": "un pitido largo y dos cortos",
    "cortos_repetidos": "pitidos cortos repetidos",
    "un_largo_tres_cortos": "un pitido largo y tres cortos",
}
NOMBRES_TIPO_EQUIPO = {
    "escritorio": "computador de escritorio",
    "portatil": "computador portátil",
    "desconocido": "equipo de tipo no indicado",
}
GUIAS_SOLUCION = {
    "fuente_poder_defectuosa": {
        "pasos": [
            "Apaga el computador y desconéctalo de la corriente.",
            "No abras la fuente de poder: puede conservar voltaje peligroso.",
            "Solicita a un técnico que confirme la falla y reemplace la fuente.",
        ],
        "ayuda": "La fuente de poder debe ser reemplazada por una compatible con el equipo.",
    },
    "cable_o_monitor_defectuoso": {
        "pasos": [
            "Apaga el equipo y vuelve a conectar firmemente el cable de video.",
            "Prueba con otro cable o monitor compatible para identificar cuál falla.",
            "Reemplaza únicamente el elemento que no funcione.",
        ],
        "ayuda": "No fuerces conectores; verifica que el cable corresponda al puerto del equipo.",
    },
    "gpu_defectuosa": {
        "pasos": [
            "Apaga y desconecta el computador antes de moverlo o llevarlo a revisión.",
            "Pide una prueba de la tarjeta gráfica y sus conexiones.",
            "Si se confirma la falla, solicita reemplazo o reparación compatible.",
        ],
        "ayuda": "La instalación o reparación interna es mejor dejarla a un técnico si no tienes experiencia.",
    },
    "placa_base_defectuosa": {
        "pasos": [
            "Apaga y desconecta el equipo.",
            "Lleva el computador a un técnico para revisar la placa y sus conexiones.",
            "Confirma el costo de reparación frente al reemplazo antes de autorizar el trabajo.",
        ],
        "ayuda": "La placa base requiere diagnóstico y reparación especializados.",
    },
    "refrigeracion_deficiente": {
        "pasos": [
            "Apaga el equipo y deja que se enfríe completamente.",
            "Mantén libres las rejillas de ventilación; en un portátil, úsalo sobre una superficie firme.",
            "Solicita limpieza interna y revisión del ventilador y la pasta térmica.",
        ],
        "ayuda": "Si el equipo sigue muy caliente, no continúes usándolo: un técnico debe revisar la refrigeración.",
    },
    "ram_mal_asentada": {
        "pasos": [
            "Apaga y desconecta el equipo antes de cualquier intervención.",
            "Solicita que vuelvan a colocar la memoria RAM y comprueben que quede bien fijada.",
            "Reinicia y observa si el problema vuelve a presentarse.",
        ],
        "ayuda": "Si no tienes experiencia abriendo el equipo, pide ayuda a un técnico.",
    },
    "ram_defectuosa": {
        "pasos": [
            "Solicita una prueba de memoria para identificar el módulo que falla.",
            "Reemplaza el módulo defectuoso por uno compatible con el equipo.",
            "Comprueba después que el sistema arranque y funcione con normalidad.",
        ],
        "ayuda": "La compatibilidad depende del modelo del computador y de su placa base.",
    },
    "disco_fallando": {
        "pasos": [
            "Respalda de inmediato tus archivos importantes si el disco todavía responde.",
            "Evita seguir usando el disco si hace ruidos extraños o los archivos dejan de abrir.",
            "Solicita la sustitución del disco y la recuperación o reinstalación del sistema.",
        ],
        "ayuda": "No guardes el respaldo en el mismo disco que presenta la falla.",
    },
    "bateria_cmos_agotada": {
        "pasos": [
            "Guarda la fecha y hora actuales y confirma si se pierden al apagar el equipo.",
            "Solicita el cambio de la batería CMOS por una del tipo compatible.",
            "Al encender de nuevo, ajusta la fecha y hora si es necesario.",
        ],
        "ayuda": "En algunos portátiles la batería no es de fácil acceso; consulta el manual o a un técnico.",
    },
}
NOMBRES_COMPONENTE = {
    "fuente_poder": "Fuente de poder",
    "placa_base": "Placa base",
    "procesador": "Procesador y refrigeración",
    "memoria_ram": "Memoria RAM",
    "almacenamiento": "Almacenamiento",
    "tarjeta_video": "Tarjeta gráfica y video",
}
NOMBRES_PRUEBA = {
    "fuente_con_probador": "Probar la fuente con un probador",
    "cambio_cable": "Cambiar el cable de video",
    "otro_monitor": "Conectar otro monitor",
    "gpu_en_otro_equipo": "Probar la tarjeta gráfica en otro equipo",
    "reasentar_ram": "Reasentar la memoria RAM",
    "smart_disco": "Revisar el estado de salud del disco",
    "cambio_bateria": "Cambiar la batería CMOS",
}
NOMBRES_RESULTADO = {
    "falla": "La prueba detectó una falla",
    "ok": "El componente pasó la prueba",
    "resuelve": "La acción resolvió el problema",
    "no_resuelve": "La acción no resolvió el problema",
}
PATRONES_PITIDOS = {
    "Tres pitidos cortos": "tres_cortos",
    "Uno largo y dos cortos": "un_largo_dos_cortos",
    "Pitidos cortos repetidos": "cortos_repetidos",
    "Uno largo y tres cortos": "un_largo_tres_cortos",
}
RESULTADOS_PRUEBA = {
    "La prueba detectó una falla": "falla",
    "El componente pasó la prueba": "ok",
    "La acción resolvió el problema": "resuelve",
    "La acción no resolvió el problema": "no_resuelve",
}
PREGUNTAS_LENTITUD = [
    (
        "¿La demora se nota principalmente cuando enciendes el computador?",
        "arranque_lento",
    ),
    (
        "¿El computador también se congela o deja de responder?",
        "bloqueos",
    ),
    (
        "¿Escuchas clics repetidos o ruidos inusuales del disco?",
        "ruido_clic",
    ),
]
ESTADOS = {
    "ok": "Diagnóstico generado.",
    "datos_insuficientes": "La información no basta para confirmar un diagnóstico.",
    "entrada_vacia": "No se proporcionaron datos para analizar.",
    "entrada_invalida": "No se encontraron condiciones válidas.",
    "entrada_contradictoria": "Los datos son incompatibles entre sí.",
}


def analizar_descripcion(texto: str) -> AnalisisOracion:
    """Envía la descripción libre a la DCG de Prolog (``parsear_oracion_texto/3``)."""
    if not texto.strip():
        return AnalisisOracion()
    return obtener_motor().parsear_oracion(texto)


def nombre_diagnostico(codigo: str) -> str:
    """Nombre legible de un diagnóstico base o aprendido por el experto."""
    if codigo in NOMBRES_DIAGNOSTICO:
        return NOMBRES_DIAGNOSTICO[codigo]
    for regla in obtener_motor().listar_reglas_aprendidas():
        if regla.id == codigo:
            return regla.nombre
    return codigo.replace("_", " ").capitalize()


def describir_condicion(condicion: str) -> str:
    """Traduce una condición de regla aprendida a una frase en español."""
    if condicion == "temp_cpu_alta":
        return "Temperatura del procesador sobre el umbral"
    if condicion == "equipo_antiguo":
        return "Equipo con antigüedad crítica"
    coincidencia = re.fullmatch(r"pitidos\(([^)]+)\)", condicion)
    if coincidencia:
        return "Pitidos: " + nombre_dato(coincidencia.group(1), NOMBRES_PATRON_PITIDOS)
    coincidencia = re.fullmatch(r"prueba\(([^,]+),\s*([^)]+)\)", condicion)
    if coincidencia:
        prueba, resultado = coincidencia.groups()
        return (f"Prueba «{nombre_dato(prueba, NOMBRES_PRUEBA)}»: "
                f"{nombre_dato(resultado, NOMBRES_RESULTADO).lower()}")
    return nombre_dato(condicion, DESCRIPCIONES_SINTOMA)


def describir_hecho_dcg(hecho: str) -> str:
    """Etiqueta corta para un hecho extraído por la DCG."""
    coincidencia = re.fullmatch(r"ausente\(([^)]+)\)", hecho)
    if coincidencia:
        return f"NO ocurre: {describir_condicion(coincidencia.group(1)).lower()}"
    coincidencia = re.fullmatch(r"temp_cpu\((-?\d+(?:\.\d+)?)\)", hecho)
    if coincidencia:
        return f"Temperatura {coincidencia.group(1)} °C"
    coincidencia = re.fullmatch(r"equipo\(([^,]+),\s*(\d+)\)", hecho)
    if coincidencia:
        tipo, anios = coincidencia.groups()
        return f"{nombre_dato(tipo, NOMBRES_TIPO_EQUIPO).capitalize()}, {anios} años"
    return describir_condicion(hecho)


def generar_identificador(nombre: str) -> str:
    """Propone un átomo Prolog válido a partir del nombre legible."""
    texto = unicodedata.normalize("NFKD", nombre.lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    if texto and not texto[0].isalpha():
        texto = "diag_" + texto
    return texto[:60]


def bloque_persistido(motor: MotorInferencia) -> str:
    """Lee del archivo .pl el bloque de conocimiento aprendido (evidencia)."""
    try:
        with open(motor.ruta_base, encoding="utf-8") as archivo:
            texto = archivo.read()
    except OSError as error:
        return f"No se pudo leer el archivo: {error}"
    inicio = texto.find(MARCA_INICIO)
    fin = texto.find(MARCA_FIN)
    if inicio == -1 or fin == -1:
        return "(el archivo todavía no tiene bloque de conocimiento aprendido)"
    return texto[inicio:fin + len(MARCA_FIN)]


def mostrar_login_experto() -> None:
    """Formulario de acceso: solo el rol «experto» ve el panel de conocimiento."""
    st.markdown('<div class="section-kicker">Acceso restringido</div>', unsafe_allow_html=True)
    st.markdown("## Iniciar sesión como experto")
    st.markdown(
        '<p class="section-intro">El panel de adquisición de conocimiento modifica la '
        'base Prolog. Solo un usuario con rol <b>Experto</b> puede usarlo.</p>',
        unsafe_allow_html=True,
    )
    if cargar_credenciales() is None:
        st.warning(
            "No hay credenciales de experto configuradas. Ejecuta "
            "`py autenticacion.py --configurar` y vuelve a cargar la página."
        )
        return
    with st.form("harddiag_form_login"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
    if entrar:
        rol = autenticar(usuario, contrasena)
        if rol == ROL_EXPERTO:
            st.session_state["harddiag_rol"] = rol
            st.session_state["harddiag_usuario"] = usuario.strip()
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")


def mostrar_panel_experto(
    motor: MotorInferencia,
    opciones_sintomas: dict[str, str],
) -> None:
    """Panel de adquisición dinámica de conocimiento (rol experto)."""
    st.markdown('<div class="section-kicker">Administración del conocimiento</div>', unsafe_allow_html=True)
    st.markdown("## Centro experto")
    st.markdown(
        '<p class="section-intro">Crea diagnósticos nuevos y enseña vocabulario. Cada cambio '
        'se inyecta en caliente con <code>assertz/1</code> y se escribe en '
        '<code>base_conocimiento.pl</code>, así que se conserva al reiniciar.</p>',
        unsafe_allow_html=True,
    )

    reglas = motor.listar_reglas_aprendidas()
    alias_actuales = motor.listar_aliases_aprendidos()
    col_reglas, col_alias, col_sintomas = st.columns(3)
    col_reglas.metric("Reglas aprendidas", len(reglas))
    col_alias.metric("Frases personalizadas", len(alias_actuales))
    col_sintomas.metric("Síntomas disponibles", len(opciones_sintomas))

    pestana_regla, pestana_lista, pestana_alias = st.tabs(
        ["Nuevo diagnóstico", "Reglas aprendidas", "Vocabulario"]
    )
    with pestana_regla:
        mostrar_formulario_regla(motor, opciones_sintomas)
    with pestana_lista:
        mostrar_reglas_aprendidas(motor, reglas)
    with pestana_alias:
        mostrar_vocabulario(motor, opciones_sintomas, alias_actuales)


def mostrar_formulario_regla(
    motor: MotorInferencia,
    opciones_sintomas: dict[str, str],
) -> None:
    componentes = dict(motor.listar_componentes())
    especiales = motor.listar_condiciones_especiales()
    todas = [*opciones_sintomas, *especiales]

    st.markdown("### Crear un diagnóstico nuevo")
    st.caption(
        "La regla se guarda como regla_aprendida/8 y la evalúa la regla genérica R26: "
        "el diagnóstico aparece en los resultados, en la explicación y en las sugerencias "
        "igual que los diagnósticos originales."
    )
    with st.form("harddiag_form_regla", clear_on_submit=False):
        nombre = st.text_input(
            "Nombre del diagnóstico",
            placeholder="Ejemplo: Fuente de poder sobrecargada",
            max_chars=120,
        ).strip()
        identificador = st.text_input(
            "Identificador Prolog (opcional)",
            placeholder="Se genera a partir del nombre, por ejemplo fuente_sobrecargada",
            help="Átomo de Prolog: minúsculas, números y guion bajo; debe empezar con una letra.",
            max_chars=60,
        ).strip()
        componente = st.selectbox(
            "Componente afectado",
            options=list(componentes),
            format_func=lambda c: componentes[c],
        )
        requeridos = st.multiselect(
            "Síntomas requeridos (todos deben estar presentes)",
            options=list(opciones_sintomas),
            format_func=lambda s: opciones_sintomas[s],
        )
        adicionales = st.multiselect(
            "Condiciones adicionales requeridas (opcional)",
            options=especiales,
            format_func=describir_condicion,
        )
        excluyentes = st.multiselect(
            "Condiciones que excluyen el diagnóstico (opcional)",
            options=todas,
            format_func=describir_condicion,
        )
        columna_certeza, columna_gravedad = st.columns(2)
        certeza = columna_certeza.radio("Certeza", ["alta", "media"], horizontal=True)
        gravedad = columna_gravedad.select_slider(
            "Gravedad / nivel de daño", options=["baja", "media", "alta"], value="media"
        )
        accion = st.text_area(
            "Acción o solución recomendada",
            placeholder="Ejemplo: Revisar el consumo del equipo y reemplazar la fuente por una de mayor potencia.",
            max_chars=400,
        ).strip()
        guardar = st.form_submit_button(
            "Inyectar regla y guardarla en el .pl", type="primary", use_container_width=True
        )

    if guardar:
        id_final = identificador or generar_identificador(nombre)
        try:
            regla = motor.crear_regla(
                id_final, nombre, componente, requeridos + adicionales,
                excluyentes, certeza, gravedad, accion,
            )
        except ValueError as error:
            st.error(str(error))
        except (OSError, PrologError, RuntimeError) as error:
            st.error(f"No se pudo guardar la regla: {error}")
        else:
            st.success(
                f"Regla «{regla.nombre}» ({regla.id}) inyectada con assertz/1 y escrita en "
                "base_conocimiento.pl. Ya participa en el diagnóstico normal."
            )
            st.code(
                f"regla_aprendida({regla.id}, '{regla.nombre}', {regla.componente},\n"
                f"    [{', '.join(regla.requeridas)}],\n"
                f"    [{', '.join(regla.excluyentes)}],\n"
                f"    {regla.certeza}, {regla.gravedad}, '{regla.accion}').",
                language="prolog",
            )


def mostrar_reglas_aprendidas(motor: MotorInferencia, reglas: list) -> None:
    st.markdown("### Reglas aprendidas")
    if not reglas:
        st.caption("Aún no se han creado diagnósticos nuevos.")
    for regla in reglas:
        with st.container(border=True):
            st.markdown(f"**{regla.nombre}** · `{regla.id}`")
            st.write(
                f"Componente: {NOMBRES_COMPONENTE.get(regla.componente, regla.componente)} · "
                f"certeza {regla.certeza} · gravedad {regla.gravedad}"
            )
            st.write("Requiere: " + "; ".join(describir_condicion(c) for c in regla.requeridas))
            if regla.excluyentes:
                st.write("Se excluye si: " + "; ".join(
                    describir_condicion(c) for c in regla.excluyentes))
            st.caption(f"Acción: {regla.accion}")
            if st.button("Eliminar esta regla", key=f"harddiag_eliminar_regla_{regla.id}"):
                try:
                    eliminada = motor.eliminar_regla(regla.id)
                except (OSError, PrologError, RuntimeError) as error:
                    st.error(f"No se pudo eliminar la regla: {error}")
                else:
                    if eliminada:
                        st.session_state.pop("harddiag_ultima_respuesta", None)
                        st.rerun()
                    st.error("La regla ya no existe.")

    with st.expander("Ver el bloque persistido en base_conocimiento.pl"):
        st.code(bloque_persistido(motor), language="prolog")


def mostrar_vocabulario(
    motor: MotorInferencia,
    opciones_sintomas: dict[str, str],
    alias_actuales: list[tuple[str, str]],
) -> None:
    st.markdown("### Enseñar una frase nueva")
    st.caption(
        "Las frases se guardan como alias_aprendido/2 y la DCG las reconoce como una "
        "secuencia de palabras dentro de cualquier oración."
    )
    with st.form("harddiag_form_aprender_alias", clear_on_submit=True):
        nueva_frase = st.text_input(
            "Cómo describiría el usuario la falla",
            placeholder="Ejemplo: el monitor muestra rayas de colores",
            max_chars=120,
        ).strip()
        sintoma_aprendido = st.selectbox(
            "Síntoma conocido que mejor representa la frase",
            options=sorted(opciones_sintomas),
            format_func=lambda nombre: opciones_sintomas[nombre],
        )
        guardar = st.form_submit_button(
            "Guardar frase para futuros diagnósticos",
            type="primary",
            use_container_width=True,
        )

    if guardar:
        if not nueva_frase:
            st.warning("Escribe una frase antes de guardarla.")
        else:
            try:
                guardado = motor.aprender_alias(nueva_frase, sintoma_aprendido)
            except (OSError, ValueError, PrologError, RuntimeError) as error:
                st.error(f"No se pudo guardar la frase: {error}")
            else:
                if guardado:
                    st.success(
                        f"Aprendida: «{nueva_frase}» → "
                        f"{opciones_sintomas[sintoma_aprendido]}. "
                        "Ya se puede usar en el diagnóstico normal."
                    )
                    alias_actuales = motor.listar_aliases_aprendidos()
                else:
                    st.warning(
                        "No se guardó: esa frase ya está asociada con otro síntoma "
                        "o la asociación no es válida."
                    )

    st.markdown("### Frases personalizadas")
    if not alias_actuales:
        st.caption("Aún no se han agregado frases personalizadas.")
        return
    for sintoma, frase in alias_actuales:
        st.write(f"- **{frase}** → {opciones_sintomas.get(sintoma, sintoma)}")

    frase_eliminar = st.selectbox(
        "Selecciona una frase para eliminar",
        options=[frase for _, frase in alias_actuales],
        key="harddiag_alias_a_eliminar",
    )
    if st.button("Eliminar frase seleccionada", key="harddiag_eliminar_alias"):
        try:
            eliminada = motor.eliminar_alias_aprendido(frase_eliminar)
        except (OSError, ValueError, PrologError, RuntimeError) as error:
            st.error(f"No se pudo eliminar la frase: {error}")
        else:
            if eliminada:
                st.success(f"Se eliminó la frase «{frase_eliminar}».")
                st.rerun()
            else:
                st.error("La frase no está guardada como aprendizaje personalizado.")


def nombre_dato(codigo: str, nombres: dict[str, str]) -> str:
    return nombres.get(codigo, codigo.replace("_", " "))


def presentar_hecho(hecho: str) -> str:
    """Muestra en español los datos internos usados para justificar el resultado."""
    coincidencia = re.fullmatch(r"observado\(([^)]+)\)", hecho)
    if coincidencia:
        return nombre_dato(coincidencia.group(1), DESCRIPCIONES_SINTOMA)

    coincidencia = re.fullmatch(r"temp_cpu\((\d+)\s*°C\)", hecho)
    if coincidencia:
        return f"Temperatura del procesador: {coincidencia.group(1)} °C"

    coincidencia = re.fullmatch(r"pitidos\(([^)]+)\)", hecho)
    if coincidencia:
        patron = nombre_dato(coincidencia.group(1), NOMBRES_PATRON_PITIDOS)
        return f"Patrón de pitidos: {patron}"

    coincidencia = re.fullmatch(r"prueba\(([^,]+),\s*([^)]+)\)", hecho)
    if coincidencia:
        prueba, resultado = coincidencia.groups()
        return (
            f"Prueba realizada: {nombre_dato(prueba, NOMBRES_PRUEBA)}. "
            f"Resultado: {nombre_dato(resultado, NOMBRES_RESULTADO)}."
        )

    coincidencia = re.fullmatch(r"equipo\(([^,]+),\s*(\d+) años\)", hecho)
    if coincidencia:
        tipo, antiguedad = coincidencia.groups()
        return (
            f"Equipo: {nombre_dato(tipo, NOMBRES_TIPO_EQUIPO)}, "
            f"{antiguedad} años de antigüedad."
        )

    coincidencia = re.fullmatch(r"sintoma_componente\(([^,]+),\s*([^)]+)\)", hecho)
    if coincidencia:
        sintoma, componente = coincidencia.groups()
        descripcion = nombre_dato(sintoma, DESCRIPCIONES_SINTOMA)
        nombre = nombre_dato(componente, NOMBRES_COMPONENTE).lower()
        return f"El síntoma «{descripcion}» puede relacionarse con {nombre}."

    coincidencia = re.fullmatch(r"codigo_pitido\(([^,]+),\s*([^)]+)\)", hecho)
    if coincidencia:
        patron, componente = coincidencia.groups()
        nombre_patron = nombre_dato(patron, NOMBRES_PATRON_PITIDOS)
        nombre_componente = nombre_dato(componente, NOMBRES_COMPONENTE).lower()
        return f"El patrón «{nombre_patron}» puede relacionarse con {nombre_componente}."

    coincidencia = re.fullmatch(r"umbral\(temp_cpu_max_celsius,\s*(\d+)\)", hecho)
    if coincidencia:
        return f"Umbral de temperatura utilizado: {coincidencia.group(1)} °C."

    coincidencia = re.fullmatch(r"umbral\(antiguedad_critica_anios,\s*(\d+)\)", hecho)
    if coincidencia:
        return f"Umbral de antigüedad utilizado: {coincidencia.group(1)} años."

    coincidencia = re.fullmatch(r"dato\(([^,]+),\s*([^)]+)\)", hecho)
    if coincidencia:
        variable, nivel = coincidencia.groups()
        nombre = VARIABLES.get(variable, (variable.replace("_", " "),))[0]
        return f"Clasificador numérico: {nombre.lower()} en nivel «{nivel}»."

    return hecho.replace("_", " ").capitalize()


def presentar_negacion(texto: str) -> str:
    """Traduce las comprobaciones lógicas a una explicación clara en español."""
    if texto.startswith("R21:"):
        return "No se encontró una prueba que descarte este posible diagnóstico."
    if texto.startswith("R1:"):
        return "No se reportaron luces indicadoras encendidas."
    if texto.startswith("R9b:"):
        return "La prueba no confirmó una falla de la fuente de poder."
    if texto.startswith("R13:"):
        return (
            "No se detectó un patrón de pitidos que indique una falla de memoria; "
            "la sospecha se basa en la inestabilidad y los síntomas observados."
        )
    if texto.startswith("R25:"):
        return "Con los datos ingresados no se pudo obtener una conclusión final."
    if texto.startswith("R26: \\+ descartado"):
        return "No se encontró una prueba que descarte este diagnóstico aprendido."
    coincidencia = re.match(r"R26: \\\+ (.+?) tuvo éxito", texto)
    if coincidencia:
        return (f"No está presente «{describir_condicion(coincidencia.group(1))}», "
                "la condición que excluye esta regla aprendida.")
    return texto.replace("\\+", "no").replace("_", " ")


def presentar_alternativa(texto: str) -> str:
    diagnostico, separador, razon = texto.partition(": ")
    if not separador:
        return texto
    return f"{nombre_diagnostico(diagnostico)}: {razon}"


def sintomas_seguimiento_lentitud(respuestas: dict[int, str]) -> list[str]:
    """Convierte únicamente respuestas afirmativas del asistente en síntomas."""
    return [
        sintoma
        for indice, (_, sintoma) in enumerate(PREGUNTAS_LENTITUD)
        if respuestas.get(indice) == "Sí"
    ]


def preparar_entrada(
    sintomas: list[str],
    analisis: AnalisisOracion,
    temperatura: int | None,
    pitidos: str | None,
    tipo_equipo: str | None,
    antiguedad: int | None,
    pruebas: list[tuple[str, str]],
    discretos: list[str],
) -> list[str]:
    """Une los controles del formulario con los hechos que extrajo la DCG.

    Si el formulario y la descripción libre informan el mismo dato
    (temperatura, pitidos o equipo), prevalece el valor del formulario.
    """
    hechos_dcg = [
        hecho for hecho in analisis.hechos
        if not (temperatura is not None and hecho.startswith("temp_cpu("))
        and not (pitidos and hecho.startswith("pitidos("))
        and not (tipo_equipo and antiguedad is not None and hecho.startswith("equipo("))
    ]
    entrada = list(dict.fromkeys([*sintomas, *hechos_dcg]))
    if temperatura is not None:
        entrada.append(f"temp_cpu({temperatura})")
    if pitidos:
        entrada.append(f"pitidos({pitidos})")
    for nombre, resultado in pruebas:
        entrada.append(f"prueba({nombre}, {resultado})")
    if tipo_equipo and antiguedad is not None:
        entrada.append(f"equipo({tipo_equipo}, {antiguedad})")
    entrada.extend(discretos)
    return list(dict.fromkeys(entrada))


def lectura_desde_dcg(analisis: AnalisisOracion, patron: str) -> int | None:
    """Recupera un número (temperatura o antigüedad) extraído por la DCG."""
    for hecho in analisis.hechos:
        coincidencia = re.fullmatch(patron, hecho)
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def mostrar_resultado(respuesta: Respuesta) -> None:
    """Presenta únicamente los diagnósticos, trazas y sugerencias devueltos por Prolog."""
    st.markdown('<div class="section-kicker">Paso 3 · Resultado</div>', unsafe_allow_html=True)
    st.markdown("## Lo que encontramos")
    marca = st.session_state.get("harddiag_marca")
    if marca:
        st.caption(f"Equipo: {marca}")

    mensajes_estado = {
        "ok": ("✅", "Se encontraron posibles diagnósticos"),
        "datos_insuficientes": ("🔎", "Hace falta información para confirmar una falla"),
        "entrada_vacia": ("ℹ️", "Aún no hay información para analizar"),
        "entrada_invalida": ("⚠️", "No se encontraron datos válidos"),
        "entrada_contradictoria": ("⛔", "Hay datos que se contradicen"),
    }
    icono, mensaje = mensajes_estado.get(
        respuesta.estado, ("ℹ️", ESTADOS.get(respuesta.estado, respuesta.estado))
    )
    if respuesta.estado == "entrada_contradictoria":
        st.error(f"{icono} **{mensaje}.** Prolog bloqueó el diagnóstico para no emitir uno erróneo.")
    else:
        st.info(f"{icono} **{mensaje}.**")

    entrada = st.session_state.get("harddiag_ultima_entrada")
    if entrada or respuesta.hechos_dcg:
        with st.expander("Ver lo que se envió a Prolog"):
            if respuesta.hechos_dcg:
                st.markdown("**Hechos extraídos por la DCG:** " + ", ".join(
                    f"`{hecho}`" for hecho in respuesta.hechos_dcg))
            if respuesta.no_reconocidas:
                st.markdown("**Palabras no reconocidas:** " + ", ".join(respuesta.no_reconocidas))
            if entrada:
                st.code(f"analizar_caso([{', '.join(entrada)}], Reporte).", language="prolog")

    if respuesta.estado == "entrada_contradictoria":
        st.markdown("### Contradicciones encontradas")
        for contradiccion in respuesta.contradicciones:
            with st.container(border=True):
                partes = [describir_hecho_dcg(parte)
                          for parte in contradiccion.elementos.split(" + ")]
                st.markdown("**" + "  ⟷  ".join(partes) + "**")
                st.write(contradiccion.motivo)
                st.caption(f"Regla de consistencia: {contradiccion.tipo}")
        st.info("Corrige o quita uno de los datos en conflicto y vuelve a analizar.")
        return

    if respuesta.diagnosticos:
        if len(respuesta.diagnosticos) > 1:
            st.caption("Las hipótesis están ordenadas por prioridad y evidencia.")
        for indice, diagnostico in enumerate(respuesta.diagnosticos, start=1):
            nombre = nombre_diagnostico(diagnostico.nombre)
            with st.container(border=True):
                st.markdown(f"### {indice}. {nombre}")
                col_danio, col_severidad, col_certeza, col_prioridad = st.columns(4)
                col_danio.metric("Nivel de daño", diagnostico.nivel_danio.capitalize())
                col_severidad.metric("Severidad", diagnostico.severidad.capitalize())
                col_certeza.metric("Certeza", diagnostico.certeza.capitalize())
                col_prioridad.metric("Prioridad", diagnostico.prioridad)
                st.progress(
                    max(0, min(diagnostico.cobertura, 100)) / 100,
                    text=f"Evidencia relacionada: {diagnostico.cobertura}%",
                )
                st.markdown("#### Solución recomendada")
                st.success(diagnostico.accion)
                guia = GUIAS_SOLUCION.get(diagnostico.nombre)
                if guia:
                    st.markdown("**Pasos sugeridos**")
                    for paso in guia["pasos"]:
                        st.markdown(f"- {paso}")
                    st.caption(f"Ten en cuenta: {guia['ayuda']}")
                else:
                    st.caption(
                        "Sigue la recomendación indicada y consulta a un técnico si no "
                        "tienes experiencia con reparaciones de hardware."
                    )

                explicacion = next(
                    (e for e in respuesta.explicaciones if e.nombre == diagnostico.nombre),
                    None,
                )
                if explicacion:
                    with st.expander("Ver explicación del diagnóstico"):
                        col_reglas, col_hechos = st.columns(2)
                        with col_reglas:
                            st.markdown("**Reglas aplicadas**")
                            if explicacion.reglas:
                                for regla in explicacion.reglas:
                                    st.write(f"- Regla {regla}")
                            else:
                                st.caption("No hay reglas registradas.")
                        with col_hechos:
                            st.markdown("**Datos que respaldan el resultado**")
                            if explicacion.hechos:
                                for hecho in explicacion.hechos:
                                    st.write(f"- {presentar_hecho(hecho)}")
                            else:
                                st.caption("No se registraron hechos positivos.")
                        if explicacion.negaciones:
                            st.markdown("**Comprobaciones que descartaron fallas**")
                            for negacion in explicacion.negaciones:
                                st.write(f"- {presentar_negacion(negacion)}")
                        if explicacion.alternativas_descartadas:
                            st.markdown("**Otras hipótesis descartadas**")
                            for alternativa in explicacion.alternativas_descartadas:
                                st.write(f"- {presentar_alternativa(alternativa)}")
                        st.caption(
                            "La explicación corresponde a las reglas y pruebas que Prolog "
                            "comprobó para este resultado."
                        )
    elif respuesta.sospechosos:
        st.markdown("### Componentes que conviene revisar")
        st.caption("Estos componentes tienen relación con los síntomas indicados; no son un diagnóstico confirmado.")
        columnas = st.columns(min(len(respuesta.sospechosos), 3))
        for indice, (componente, indicios) in enumerate(respuesta.sospechosos):
            with columnas[indice % len(columnas)]:
                st.metric(
                    NOMBRES_COMPONENTE.get(componente, componente),
                    f"{indicios} indicio(s)",
                )

    if respuesta.descartados:
        with st.expander("Datos que no se pudieron reconocer"):
            st.write(", ".join(respuesta.descartados))

    if respuesta.sugerencias:
        st.markdown("## ¿Qué falta?")
        st.caption(
            "Completar estas comprobaciones puede ayudar a distinguir las posibles causas. "
            "Empieza por la primera sugerencia."
        )
        for indice, sugerencia in enumerate(respuesta.sugerencias, start=1):
            with st.container(border=True):
                st.markdown(f"### {indice}. {sugerencia.dato}")
                st.write(sugerencia.razon)
                if sugerencia.hipotesis:
                    hipotesis = [
                        nombre_diagnostico(nombre)
                        for nombre in sugerencia.hipotesis
                    ]
                    st.caption("Esta comprobación ayuda a diferenciar: " + " · ".join(hipotesis))
    elif respuesta.estado == "datos_insuficientes":
        st.info(
            "Prueba a agregar más síntomas observados o completar los detalles del equipo "
            "y vuelve a analizar."
        )


def main() -> None:
    st.session_state.setdefault("harddiag_modo", "normal")
    st.set_page_config(
        page_title="HardDiag | Diagnóstico de hardware",
        page_icon=RUTA_LOGO if os.path.isfile(RUTA_LOGO) else "🖥️",
        layout="wide",
    )
    hero = """
        <style>
        /* Tema "terminal bancaria": gris beige, azul marino, bordes biselados,
           esquinas rectas, sin degradados ni sombras difusas. */
        #MainMenu, header[data-testid="stHeader"], footer {visibility: hidden;}
        :root {
            --bk-fondo: #c9c5b8;
            --bk-panel: #e4e1d6;
            --bk-campo: #ffffff;
            --bk-azul: #0a246a;
            --bk-azul-claro: #3a5ea8;
            --bk-texto: #000000;
            --bk-apagado: #3c3c3c;
            --bk-luz: #ffffff;
            --bk-sombra: #6b6b6b;
            --bk-negro: #1a1a1a;
            --bk-ambar: #fff4b8;
            --bk-mono: "Lucida Console", "Courier New", monospace;
        }
        .stApp { background: var(--bk-fondo); color: var(--bk-texto); }
        .block-container {
            max-width: 1060px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, h4, h5 {
            font-family: var(--bk-mono);
            letter-spacing: 0;
            text-transform: uppercase;
            color: var(--bk-azul);
        }
        h2 { border-bottom: 2px solid var(--bk-azul); padding-bottom: .2rem; font-size: 1.35rem; }
        h3 { font-size: 1.05rem; }
        .stMarkdown p, .stCaption, label, [data-testid="stWidgetLabel"] p,
        [data-testid="stCaptionContainer"] {
            color: var(--bk-texto);
        }
        [data-testid="stWidgetLabel"] p { font-weight: 700; text-transform: uppercase; font-size: .78rem; }
        .stMarkdown code, code {
            border: 1px solid var(--bk-sombra);
            border-radius: 0;
            background: var(--bk-campo);
            color: var(--bk-negro);
        }

        /* Ventana principal: barra de título azul marino + marco biselado */
        .hero {
            margin: 0 0 1.2rem;
            padding: 0 0 1rem;
            border-radius: 0;
            border: 2px solid;
            border-color: var(--bk-luz) var(--bk-negro) var(--bk-negro) var(--bk-luz);
            outline: 1px solid var(--bk-sombra);
            background: var(--bk-panel);
            box-shadow: 4px 4px 0 var(--bk-negro);
        }
        .hero-kicker {
            padding: .35rem .7rem;
            background: var(--bk-azul);
            color: #ffffff;
            font-family: var(--bk-mono);
            font-size: .8rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .hero-kicker::after { content: "   [ _ ] [ □ ] [ X ]"; float: right; opacity: .85; white-space: pre; }
        .hero h1 {
            margin: .9rem 1rem .3rem;
            font-size: clamp(1.7rem, 4vw, 2.4rem);
            color: var(--bk-azul);
            text-shadow: none;
        }
        .hero p {
            margin: 0 1rem;
            max-width: 760px;
            color: var(--bk-texto);
            font-size: .95rem;
            line-height: 1.55;
        }
        .hero-status {
            display: inline-block;
            margin: .9rem 1rem 0;
            padding: .2rem .6rem;
            border: 1px solid var(--bk-negro);
            background: var(--bk-negro);
            color: #7dff7d;
            font-family: var(--bk-mono);
            font-size: .75rem;
        }
        .hero-status::before { content: "> "; }
        .workflow { display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 1rem 0; }
        .workflow span {
            padding: .25rem .6rem;
            border: 2px solid;
            border-color: var(--bk-luz) var(--bk-sombra) var(--bk-sombra) var(--bk-luz);
            border-radius: 0;
            background: var(--bk-fondo);
            color: var(--bk-texto);
            font-family: var(--bk-mono);
            font-size: .76rem;
        }
        .workflow b { margin-right: .35rem; color: var(--bk-azul); }

        /* Encabezados de sección: franja azul */
        .section-kicker {
            display: block;
            margin: 1rem 0 .4rem;
            padding: .25rem .6rem;
            background: var(--bk-azul);
            color: #ffffff;
            font-family: var(--bk-mono);
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .section-intro { margin: 0 0 .9rem; color: var(--bk-apagado); font-size: .9rem; }

        /* Paneles */
        .form-card, div[data-testid="stForm"],
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border: 2px solid;
            border-color: var(--bk-sombra) var(--bk-luz) var(--bk-luz) var(--bk-sombra);
            border-radius: 0;
            background: var(--bk-panel);
            box-shadow: none;
        }
        .form-card, div[data-testid="stForm"] { padding: 1.1rem 1.25rem; }
        div[data-testid="stExpander"] {
            margin: .45rem 0;
            border: 2px solid;
            border-color: var(--bk-luz) var(--bk-sombra) var(--bk-sombra) var(--bk-luz);
            border-radius: 0;
            background: var(--bk-panel);
        }
        div[data-testid="stExpander"] details summary {
            background: var(--bk-fondo);
            color: var(--bk-texto);
            font-weight: 700;
        }
        div[data-testid="stMetric"] {
            min-height: 5.5rem;
            padding: .6rem .8rem;
            border: 2px solid;
            border-color: var(--bk-sombra) var(--bk-luz) var(--bk-luz) var(--bk-sombra);
            border-radius: 0;
            background: var(--bk-campo);
        }
        div[data-testid="stMetricLabel"] p { color: var(--bk-apagado); }
        div[data-testid="stMetricValue"] { color: var(--bk-azul); font-family: var(--bk-mono); }

        /* Alertas: nota amarilla de sistema, borde negro */
        div[data-testid="stAlert"] {
            border: 2px solid var(--bk-negro);
            border-radius: 0;
            background: var(--bk-ambar);
            color: var(--bk-texto);
        }

        /* Botones: relieve clásico */
        div.stButton > button, div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            min-height: 2.6rem;
            border: 2px solid;
            border-color: var(--bk-luz) var(--bk-negro) var(--bk-negro) var(--bk-luz);
            border-radius: 0;
            background: var(--bk-fondo);
            color: var(--bk-texto);
            font-family: var(--bk-mono);
            font-weight: 700;
            text-transform: uppercase;
            box-shadow: none;
            transition: none;
        }
        div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
            background: #d9d5c8;
            color: var(--bk-azul);
            transform: none;
        }
        div.stButton > button:active, div[data-testid="stFormSubmitButton"] > button:active {
            border-color: var(--bk-negro) var(--bk-luz) var(--bk-luz) var(--bk-negro);
            background: #bcb8ab;
        }
        div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button[kind="primary"],
        .st-key-harddiag_analyze button {
            background: var(--bk-azul);
            color: #ffffff;
            min-height: 3rem;
            font-size: .95rem;
        }
        .st-key-harddiag_analyze button:hover { background: var(--bk-azul-claro); color: #ffffff; }

        /* Campos de captura: hundidos, fondo blanco, tipografía de terminal */
        [data-baseweb="select"] > div, [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div, [data-baseweb="textarea"] {
            border: 2px solid;
            border-color: var(--bk-sombra) var(--bk-luz) var(--bk-luz) var(--bk-sombra);
            border-radius: 0;
            background-color: var(--bk-campo);
            color: var(--bk-negro);
            font-family: var(--bk-mono);
        }
        [data-baseweb="select"] > div:focus-within, [data-baseweb="input"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {
            border-color: var(--bk-azul) var(--bk-azul-claro) var(--bk-azul-claro) var(--bk-azul);
            box-shadow: none;
        }
        textarea, input { color: var(--bk-negro) !important; font-family: var(--bk-mono) !important; }
        [data-baseweb="tag"] { border-radius: 0; background: var(--bk-azul); color: #ffffff; }
        [data-baseweb="popover"] ul, [data-baseweb="menu"] {
            border: 2px solid var(--bk-negro);
            border-radius: 0;
            background: var(--bk-campo);
        }
        [data-baseweb="popover"] li:hover { background: var(--bk-azul); color: #ffffff; }
        [data-testid="stCheckbox"] span[role="checkbox"], [data-baseweb="checkbox"] > span {
            border-radius: 0;
        }
        [data-baseweb="radio"] input + div { border-radius: 50%; }

        /* Barra de progreso: bloques azul marino */
        [data-testid="stProgressBar"] > div { border-radius: 0; background: var(--bk-campo); border: 1px solid var(--bk-negro); }
        [data-testid="stProgressBar"] > div > div { border-radius: 0; background: var(--bk-azul); box-shadow: none; }

        /* Bloques de código: pantalla verde sobre negro */
        pre, [data-testid="stCode"] pre, .stCodeBlock pre {
            border: 2px solid var(--bk-negro);
            border-radius: 0;
            background: var(--bk-negro) !important;
            color: #7dff7d !important;
        }
        pre code { color: #7dff7d !important; border: 0; background: transparent; }
        hr { border: 0; border-top: 2px solid var(--bk-sombra); }

        /* Refuerzo: Streamlit redondea y tiñe sus contenedores; aquí se fuerza el estilo rígido */
        [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stExpander"], [data-testid="stExpander"] details,
        [data-testid="stTextArea"] *, [data-testid="stTextInput"] *, [data-testid="stNumberInput"] *,
        [data-testid="stSelectbox"] [data-baseweb="select"] *, [data-testid="stMultiSelect"] [data-baseweb="select"] *,
        [data-testid="stAlert"], [data-testid="stAlert"] *, button, [data-baseweb="tag"] {
            border-radius: 0 !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] [data-testid="stTextArea"]),
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 2px solid #6b6b6b;
            border-color: #6b6b6b #ffffff #ffffff #6b6b6b;
        }
        [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            background: #ffffff !important;
        }
        [data-testid="stTextArea"] [data-baseweb="textarea"], [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 2px solid !important;
            border-color: #6b6b6b #ffffff #ffffff #6b6b6b !important;
        }
        [data-testid="stTextArea"] textarea::placeholder, [data-testid="stTextInput"] input::placeholder {
            color: #6b6b6b !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] *, [data-testid="stMultiSelect"] [data-baseweb="select"] input {
            color: #000000;
        }
        @media (max-width: 640px) {
            .block-container { padding: 1rem .8rem 3rem; }
            .hero-kicker::after { content: ""; }
        }
        </style>
        <section class="hero">
            <div class="hero-kicker">Diagnóstico guiado de computadores</div>
            <h1>HardDiag</h1>
            <p>Identifica posibles fallas de hardware a partir de síntomas,
            pruebas y condiciones del equipo. Recibe hipótesis explicadas y
            recomendaciones seguras para continuar.</p>
            <div class="hero-status">Sistema experto · Análisis de hardware</div>
            <div class="workflow">
                <span><b>01</b> Describe la falla</span>
                <span><b>02</b> Añade evidencias</span>
                <span><b>03</b> Revisa el diagnóstico</span>
            </div>
        </section>
        """
    if st.session_state["harddiag_modo"] == "experto":
        hero = hero.replace(
            "Diagnóstico guiado de computadores",
            "Administración del conocimiento experto",
        ).replace(
            "Identifica posibles fallas de hardware a partir de síntomas,\n"
            "            pruebas y condiciones del equipo. Recibe hipótesis explicadas y\n"
            "            recomendaciones seguras para continuar.",
            "Crea diagnósticos nuevos en caliente y amplía el vocabulario de la gramática\n"
            "            usado en las consultas de diagnóstico.",
        ).replace(
            '<div class="workflow">\n'
            '                <span><b>01</b> Describe la falla</span>\n'
            '                <span><b>02</b> Añade evidencias</span>\n'
            '                <span><b>03</b> Revisa el diagnóstico</span>\n'
            "            </div>",
            "",
        )
    if os.path.isfile(RUTA_LOGO):
        st.image(RUTA_LOGO, width=150)
    st.markdown(hero, unsafe_allow_html=True)
    if st.session_state["harddiag_modo"] == "experto":
        st.write("Panel exclusivo del rol Experto; el diagnóstico normal queda en una vista separada.")
    else:
        st.write(
            "Empieza por contar qué le sucede al computador. Los datos adicionales son opcionales."
        )
    st.info(
        "Orientación educativa, no reemplaza a un técnico. Si percibes olor a quemado, "
        "apaga y desconecta el equipo; nunca abras la fuente de poder."
    )

    try:
        motor = obtener_motor()
        sintomas_catalogo = motor.listar_sintomas()
    except (FileNotFoundError, OSError, PrologError, RuntimeError) as error:
        st.error(f"No se pudo iniciar SWI-Prolog o cargar la base de conocimiento: {error}")
        st.info(
            "Instala SWI-Prolog, verifica que esté disponible para PySwip y ejecuta "
            "`py -m pip install -r requirements.txt`."
        )
        return

    opciones_sintomas = {nombre: descripcion for nombre, descripcion in sintomas_catalogo}
    if st.session_state["harddiag_modo"] == "experto":
        columna_volver, columna_sesion = st.columns([3, 1])
        with columna_volver:
            if st.button("← Volver al diagnóstico normal", key="harddiag_volver_normal"):
                st.session_state["harddiag_modo"] = "normal"
                st.rerun()
        if st.session_state.get("harddiag_rol") != ROL_EXPERTO:
            mostrar_login_experto()
            return
        with columna_sesion:
            if st.button("Cerrar sesión", key="harddiag_cerrar_sesion", use_container_width=True):
                st.session_state.pop("harddiag_rol", None)
                st.session_state.pop("harddiag_usuario", None)
                st.session_state["harddiag_modo"] = "normal"
                st.rerun()
        st.caption(
            f"Sesión iniciada como **{st.session_state.get('harddiag_usuario', 'experto')}** "
            "(rol Experto)."
        )
        mostrar_panel_experto(motor, opciones_sintomas)
        return

    columnas_modo = st.columns([3, 1])
    with columnas_modo[0]:
        st.caption("Estás en el modo normal: las herramientas de conocimiento no aparecen aquí.")
    with columnas_modo[1]:
        if st.button(
            "Ir al modo experto →",
            key="harddiag_ir_experto",
            use_container_width=True,
        ):
            st.session_state["harddiag_modo"] = "experto"
            st.rerun()

    st.markdown('<div class="section-kicker">Paso 1 · Describe el problema</div>', unsafe_allow_html=True)
    st.markdown("## ¿Qué le sucede al computador?")
    st.markdown(
        '<p class="section-intro">Selecciona los síntomas que observas o descríbelos como se los contarías a un técnico.</p>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        elegidos = st.multiselect(
            "Síntomas principales",
            options=list(opciones_sintomas),
            format_func=lambda nombre: opciones_sintomas[nombre],
            placeholder="Busca y selecciona los síntomas observados",
        )
        adicionales = st.text_area(
            "Describe cualquier otra falla",
            placeholder=(
                "Ejemplo: el computador se apaga al jugar y el ventilador suena muy fuerte. "
                "Puedes escribir varias observaciones."
            ),
            help=(
                "Señala qué ocurre, cuándo ocurre y cualquier ruido, luz o mensaje que aparezca. "
                "Se pueden escribir daños no incluidos en la lista."
            ),
            height=120,
            key="harddiag_descripcion_falla",
        )
        try:
            analisis = analizar_descripcion(adicionales)
        except (PrologError, RuntimeError) as error:
            st.error(f"La gramática de Prolog no pudo analizar la descripción: {error}")
            analisis = AnalisisOracion()
        sintomas_libres = [hecho for hecho in analisis.hechos if hecho in opciones_sintomas]
        if adicionales.strip() and not analisis.hechos:
            st.info(
                "La descripción quedó registrada. La gramática (DCG) no encontró síntomas "
                "conocidos, así que no se inventará un diagnóstico. Un experto puede enseñar "
                "esa frase en el modo experto."
            )
        elif analisis.hechos:
            st.markdown(
                "**Hechos extraídos por la DCG de Prolog:** "
                + " · ".join(f"`{hecho}`" for hecho in analisis.hechos)
            )
            st.caption(
                "Interpretación: "
                + " · ".join(describir_hecho_dcg(hecho) for hecho in analisis.hechos)
            )
        if analisis.no_reconocidas:
            st.caption(
                "Palabras que la gramática no reconoció: "
                + ", ".join(analisis.no_reconocidas)
            )

        presenta_lentitud = "lentitud" in elegidos or "lentitud" in sintomas_libres
        if presenta_lentitud:
            st.markdown("#### Precisemos la lentitud")
            st.caption(
                "Responde estas preguntas breves; solo las respuestas afirmativas se usarán "
                "como síntomas adicionales."
            )
            paso_lentitud = st.session_state.get("harddiag_lentitud_paso", 0)
            respuestas_lentitud = st.session_state.get("harddiag_lentitud_respuestas", {})

            if paso_lentitud < len(PREGUNTAS_LENTITUD):
                pregunta, _ = PREGUNTAS_LENTITUD[paso_lentitud]
                st.progress(
                    (paso_lentitud + 1) / len(PREGUNTAS_LENTITUD),
                    text=f"Pregunta {paso_lentitud + 1} de {len(PREGUNTAS_LENTITUD)}",
                )
                respuesta_lentitud = st.radio(
                    pregunta,
                    options=["Sí", "No", "No estoy seguro"],
                    index=None,
                    key=f"harddiag_lentitud_respuesta_{paso_lentitud}",
                    horizontal=True,
                )
                columna_anterior, columna_siguiente = st.columns(2)
                with columna_anterior:
                    if paso_lentitud > 0 and st.button(
                        "Pregunta anterior",
                        key=f"harddiag_lentitud_anterior_{paso_lentitud}",
                    ):
                        st.session_state["harddiag_lentitud_paso"] = paso_lentitud - 1
                        st.rerun()
                with columna_siguiente:
                    texto_boton = (
                        "Ver resumen"
                        if paso_lentitud == len(PREGUNTAS_LENTITUD) - 1
                        else "Siguiente pregunta"
                    )
                    if st.button(
                        texto_boton,
                        key=f"harddiag_lentitud_siguiente_{paso_lentitud}",
                    ):
                        if respuesta_lentitud is None:
                            st.warning("Elige «Sí», «No» o «No estoy seguro» para continuar.")
                        else:
                            respuestas_lentitud[paso_lentitud] = respuesta_lentitud
                            for indice in range(paso_lentitud + 1, len(PREGUNTAS_LENTITUD)):
                                respuestas_lentitud.pop(indice, None)
                            st.session_state["harddiag_lentitud_respuestas"] = respuestas_lentitud
                            st.session_state["harddiag_lentitud_paso"] = paso_lentitud + 1
                            st.rerun()
            else:
                sintomas_seguimiento = sintomas_seguimiento_lentitud(respuestas_lentitud)
                if sintomas_seguimiento:
                    st.success(
                        "Síntomas adicionales identificados: "
                        + ", ".join(
                            DESCRIPCIONES_SINTOMA.get(sintoma, sintoma)
                            for sintoma in sintomas_seguimiento
                        )
                    )
                else:
                    st.info(
                        "No se identificaron síntomas adicionales. Se incluirá la lentitud general."
                    )
                if st.button("Volver a revisar las respuestas", key="harddiag_lentitud_reiniciar"):
                    st.session_state["harddiag_lentitud_paso"] = 0
                    st.session_state["harddiag_lentitud_respuestas"] = {}
                    st.rerun()
        else:
            st.session_state["harddiag_lentitud_paso"] = 0
            st.session_state["harddiag_lentitud_respuestas"] = {}

    st.markdown('<div class="section-kicker">Paso 2 · Añade evidencias</div>', unsafe_allow_html=True)
    st.markdown("## Datos que pueden afinar el resultado")
    st.markdown(
        '<p class="section-intro">Son opcionales; analiza igualmente si no tienes esta información.</p>',
        unsafe_allow_html=True,
    )

    temperatura = None
    tipo_equipo = None
    antiguedad = None
    with st.expander("Temperatura y datos del equipo", expanded=False):
        columna_temperatura, columna_equipo = st.columns(2)
        with columna_temperatura:
            conoce_temperatura = st.checkbox(
                "Tengo la temperatura del procesador",
                key="opcion_temperatura_independiente",
            )
            if conoce_temperatura:
                temperatura = st.number_input(
                    "Temperatura aproximada (°C)",
                    min_value=0,
                    max_value=150,
                    step=1,
                    value=None,
                    placeholder="Ejemplo: 85",
                )
        with columna_equipo:
            incluir_equipo = st.checkbox(
                "Agregar tipo y antigüedad del equipo",
                key="opcion_equipo_independiente",
            )
            if incluir_equipo:
                tipo_equipo = st.selectbox(
                    "Tipo de equipo",
                    options=["escritorio", "portatil"],
                    format_func=lambda valor: (
                        "Computador de escritorio"
                        if valor == "escritorio"
                        else "Computador portátil"
                    ),
                )
                antiguedad = st.number_input(
                    "Antigüedad (años)", min_value=0, max_value=100, step=1, value=5
                )

    patron = None
    marca = ""
    pruebas_seleccionadas: list[tuple[str, str]] = []
    resultados_pendientes: list[str] = []
    with st.expander("Pitidos, pruebas realizadas y marca", expanded=False):
        columna_patron, columna_marca = st.columns(2)
        with columna_patron:
            patron_label = st.selectbox(
                "Patrón de pitidos al encender",
                options=["No lo conozco / no aplica", *PATRONES_PITIDOS],
            )
            patron = PATRONES_PITIDOS.get(patron_label)
        with columna_marca:
            marca = st.text_input(
                "Marca del computador (opcional)",
                placeholder="Dell, HP, Lenovo, ASUS...",
                help="Dato informativo; no modifica las reglas de diagnóstico.",
            ).strip()

        no_hizo_pruebas = st.checkbox(
            "No he realizado pruebas",
            value=True,
            key="harddiag_no_hizo_pruebas",
        )
        if not no_hizo_pruebas:
            nombres_pruebas = st.multiselect(
                "Selecciona las pruebas realizadas",
                options=list(NOMBRES_PRUEBA),
                format_func=lambda nombre: NOMBRES_PRUEBA[nombre],
            )
            for nombre in nombres_pruebas:
                resultado_label = st.selectbox(
                    f"Resultado: {NOMBRES_PRUEBA[nombre]}",
                    options=["Selecciona el resultado", *RESULTADOS_PRUEBA],
                    key=f"resultado_{nombre}",
                )
                resultado = RESULTADOS_PRUEBA.get(resultado_label)
                if resultado:
                    pruebas_seleccionadas.append((nombre, resultado))
                else:
                    resultados_pendientes.append(NOMBRES_PRUEBA[nombre])

    # Pre-procesamiento numérico: las lecturas continuas (del formulario o de
    # la descripción libre) se discretizan en Python antes de ir a Prolog.
    horas_uso = None
    uso_disco = None
    discretos: list[str] = []
    with st.expander("Lecturas numéricas (clasificador ligero)", expanded=False):
        st.caption(
            "Un árbol de decisión de scikit-learn convierte valores continuos en hechos "
            "discretos dato(Variable, Nivel) antes de enviarlos a Prolog. También usa la "
            "temperatura y la antigüedad de arriba o de tu descripción."
        )
        columna_horas, columna_disco = st.columns(2)
        with columna_horas:
            if st.checkbox("Indicar horas de uso diario", key="harddiag_opcion_horas"):
                horas_uso = st.number_input(
                    "Horas de uso por día", min_value=0, max_value=24, step=1, value=8
                )
        with columna_disco:
            if st.checkbox("Indicar ocupación del disco", key="harddiag_opcion_disco"):
                uso_disco = st.number_input(
                    "Ocupación del disco (%)", min_value=0, max_value=100, step=1, value=80
                )
        temperatura_efectiva = (
            temperatura if temperatura is not None
            else lectura_desde_dcg(analisis, r"temp_cpu\((\d+)\)")
        )
        antiguedad_efectiva = (
            antiguedad if antiguedad is not None
            else lectura_desde_dcg(analisis, r"equipo\([^,]+,\s*(\d+)\)")
        )
        try:
            preprocesador = obtener_preprocesador()
            hechos_discretos = preprocesador.discretizar(
                temperatura_cpu=temperatura_efectiva,
                antiguedad=antiguedad_efectiva,
                horas_uso=horas_uso,
                uso_disco=uso_disco,
            )
        except ValueError as error:
            st.error(str(error))
            hechos_discretos = []
        if hechos_discretos:
            st.markdown(f"**Hechos discretos generados** · método: {preprocesador.metodo}")
            for hecho in hechos_discretos:
                variable = VARIABLES[hecho.variable]
                st.write(
                    f"- {variable[0]}: {hecho.valor:g} {variable[1]} → `{hecho.termino}`"
                )
        else:
            st.caption("Sin lecturas numéricas todavía.")
        discretos = [hecho.termino for hecho in hechos_discretos]

    enviar = st.button(
        "Analizar mi computador",
        type="primary",
        use_container_width=True,
        key="harddiag_analyze",
    )

    if enviar:
        try:
            if resultados_pendientes:
                raise ValueError(
                    "Selecciona el resultado de cada prueba realizada: "
                    + ", ".join(resultados_pendientes)
                    + "."
                )
            entrada = preparar_entrada(
                list(
                    dict.fromkeys(
                        elegidos
                        + (
                            sintomas_seguimiento_lentitud(
                                st.session_state.get("harddiag_lentitud_respuestas", {})
                            )
                            if presenta_lentitud
                            else []
                        )
                    )
                ),
                analisis,
                temperatura,
                patron,
                tipo_equipo,
                antiguedad,
                pruebas_seleccionadas,
                discretos,
            )
            respuesta = motor.analizar_caso(entrada)
            respuesta.hechos_dcg = analisis.hechos
            respuesta.no_reconocidas = analisis.no_reconocidas
            st.session_state["harddiag_ultima_respuesta"] = respuesta
            st.session_state["harddiag_ultima_entrada"] = entrada
            st.session_state["harddiag_marca"] = marca
        except ValueError as error:
            st.error(str(error))
        except (PrologError, RuntimeError, OSError) as error:
            st.error(f"Falló la consulta entre Python y Prolog: {error}")

    respuesta = st.session_state.get("harddiag_ultima_respuesta")
    if respuesta is not None:
        mostrar_resultado(respuesta)


if __name__ == "__main__":
    main()
