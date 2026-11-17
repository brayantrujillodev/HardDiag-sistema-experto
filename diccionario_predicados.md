# Diccionario de Predicados

**Sistema Experto de Diagnóstico y Soporte Técnico para Fallos de Hardware**
Archivo de Prolog: `base_conocimiento.pl` · Puente Python: `motor_inferencia.py`

**Modos de instanciación:** `+Arg` entrada (enviada desde Python) · `-Arg` salida (hacia Python) · `?Arg` ambos.

## 1. Predicados invocados desde Python

| Firma | Modo | Descripción funcional | Función de Python que lo invoca |
| --- | --- | --- | --- |
| `consultar_texto/2` | `consultar_texto(+Texto, -Respuesta)` | Convierte el texto (condiciones separadas por comas) en lista y llama a `consultar_caso/2`. Si el texto no se puede interpretar, responde por defecto `[entrada_invalida, [], [], []]`. | `MotorInferencia.consultar_texto()` |
| `consultar_caso/2` | `consultar_caso(+Entrada, -Respuesta)` | Consulta principal. `Respuesta = [Estado, Diagnosticos, Sospechosos, Descartados]`. | `MotorInferencia.consultar_lista()` |
| `diagnosticar_todos/3` | `diagnosticar_todos(+Entrada, -Estado, -Diagnosticos)` | Recolecta en una sola lista, sin duplicados y ordenada por prioridad, todos los diagnósticos del caso. `Estado` es `ok`, `datos_insuficientes`, `entrada_vacia` o `entrada_invalida`. Cada diagnóstico es `[Nombre, Certeza, Severidad, NivelDanio, Prioridad, Cobertura, Accion]`. | `MotorInferencia.diagnosticar_todos()` |
| `componentes_sospechosos/2` | `componentes_sospechosos(+Entrada, -Sospechosos)` | Lista `[[Componente, Cantidad], ...]` de componentes con indicios (síntomas y pitidos), de mayor a menor. Sirve cuando faltan datos. | (vía `consultar_caso/2`) |
| `listar_sintomas/1` | `listar_sintomas(-Lista)` | Devuelve el catálogo `[[Sintoma, Descripcion], ...]`. | `MotorInferencia.listar_sintomas()` |
| `analizar_caso/2` | `analizar_caso(+Entrada, -Reporte)` | Devuelve estado, diagnósticos, sospechosos, entradas descartadas, trazas de Prolog y sugerencias de información adicional. | `MotorInferencia.analizar_caso()` |

## 2. Procesamiento de listas y control de flujo (3.2)

| Firma | Modo | Descripción funcional |
| --- | --- | --- |
| `clasificar_item/2` | `clasificar_item(+Item, -Tipo)` | Clasifica un elemento de la lista: `sintoma`, `medicion`, `pitidos`, `prueba`, `equipo` o `desconocido`. Usa **corte** para que las cláusulas sean excluyentes y una última cláusula como valor por defecto. Usa `\+ ground/1` para rechazar variables sueltas. |
| `validar_entrada/3` | `validar_entrada(+Entrada, -Validos, -Descartados)` | Recorre la lista y la separa en elementos válidos y no reconocidos. |
| `evidencia_presente/2` | `evidencia_presente(+Condicion, +Lista)` | Verdadero si la condición está en la lista. Evalúa `temp_cpu_alta` y `equipo_antiguo` contra los umbrales. |
| `contiene_todos/2` | `contiene_todos(+Requisitos, +Lista)` | Verdadero si la lista contiene todos los requisitos (subconjunto). |
| `contar_presentes/3` | `contar_presentes(+Requisitos, +Lista, -N)` | Cuenta cuántos requisitos están presentes en la lista. |
| `contar_ocurrencias/3` | `contar_ocurrencias(+Elemento, +Lista, -N)` | Cuenta cuántas veces aparece un elemento en una lista. |
| `cobertura/3` | `cobertura(+Validos, +Diagnostico, -Porcentaje)` | Porcentaje (0–100) de la evidencia típica del diagnóstico que está presente. |
| `cargar_caso/2` | `cargar_caso(+Id, +Validos)` | Carga temporalmente los datos válidos como hechos del caso `Id`, para reutilizar las reglas. |
| `limpiar_caso/1` | `limpiar_caso(+Id)` | Elimina los hechos temporales del caso. |

## 3. Reglas de inferencia por niveles (3.1)

| Nivel | Firma | Modo | Descripción funcional |
| --- | --- | --- | --- |
| 1 | `sin_energia/1` | `sin_energia(?E)` | No enciende y no hay ningún LED encendido (usa `\+`). |
| 1 | `sin_video/1` | `sin_video(?E)` | Pantalla negra con ventiladores girando. |
| 1 | `sobrecalentamiento/1` | `sobrecalentamiento(?E)` | La temperatura del procesador supera el umbral máximo. |
| 1 | `pitidos_error/2` | `pitidos_error(?E, ?Componente)` | El patrón de pitidos apunta a un componente. |
| 1 | `inestabilidad/1` | `inestabilidad(?E)` | Hay reinicios, pantalla azul o bloqueos. |
| 1 | `sintoma_de/2` | `sintoma_de(?E, ?Componente)` | Un síntoma observado se asocia a un componente. |
| 1 | `equipo_antiguo/1` | `equipo_antiguo(?E)` | El equipo supera la antigüedad crítica. |
| 1 | `factor_riesgo/1` | `factor_riesgo(?E)` | Hay olor a quemado o temperatura crítica. |
| 2 | `falla_energia/1` | `falla_energia(?E)` | Sin energía y la fuente falla, o hay olor a quemado. |
| 2 | `falla_cable_o_monitor/1` | `falla_cable_o_monitor(?E)` | Sin imagen que se corrige cambiando cable o monitor. |
| 2 | `falla_video_interno/1` | `falla_video_interno(?E)` | Sin imagen y las pruebas externas no la corrigen. |
| 2 | `falla_refrigeracion/1` | `falla_refrigeracion(?E)` | Sobrecalentamiento con ventilador ruidoso o detenido. |
| 2 | `memoria_sospechosa/1` | `memoria_sospechosa(?E)` | Pitidos o inestabilidad que apuntan a la RAM. |
| 2 | `memoria_mal_asentada/1` | `memoria_mal_asentada(?E)` | RAM sospechosa y reasentarla lo resuelve. |
| 2 | `memoria_defectuosa/1` | `memoria_defectuosa(?E)` | RAM sospechosa y reasentarla no lo resuelve. |
| 2 | `almacenamiento_degradado/1` | `almacenamiento_degradado(?E)` | Síntomas de disco y prueba SMART con falla. |
| 2 | `bateria_cmos_agotada/1` | `bateria_cmos_agotada(?E)` | La hora se pierde en un equipo antiguo. |
| 2 | `descartado/2` | `descartado(?E, ?Diagnostico)` | Una prueba contradice el diagnóstico (se usa con `\+`). |
| 2 | `placa_base_sospechosa/1` | `placa_base_sospechosa(?E)` | No hay energía, la fuente pasó su prueba y los pitidos apuntan a la placa base. |
| 2 | `placa_base_defectuosa/1` | `placa_base_defectuosa(?E)` | Confirma una falla probable de placa base a partir de las señales intermedias. |
| 3 | `diagnostico/3` | `diagnostico(?E, ?Diagnostico, ?Certeza)` | Conclusión final: integra reglas de nivel 2 y exige `\+ descartado/2`. |
| 3 | `recomendacion/2` | `recomendacion(?E, -Accion)` | Acción asociada a cada diagnóstico del equipo. |
| 3 | `requiere_tecnico/1` | `requiere_tecnico(?E)` | Hay diagnóstico de gravedad alta o certeza media, o refrigeración deficiente junto con un factor de riesgo. |
| 3 | `sin_diagnostico/1` | `sin_diagnostico(?E)` | El equipo está registrado y ninguna regla aplica (usa `\+`). |

## 4. Severidad y prioridad (3.3)

| Firma | Modo | Descripción funcional |
| --- | --- | --- |
| `severidad/4` | `severidad(+Id, +Diagnostico, -Nivel, -Peso)` | Calcula la severidad: `baja`, `media`, `alta` o `critica` (si hay factor de riesgo y la gravedad no es baja). Usa **corte** para que las cláusulas sean excluyentes y un valor por defecto al final. |
| `nivel_danio/2` | `nivel_danio(+Diagnostico, -Nivel)` | Clasifica la gravedad base del tipo de diagnóstico como `leve`, `moderado` o `grave`, independientemente de los factores de riesgo del caso. |
| `prioridad/3` | `prioridad(+Peso, +Cobertura, -Prioridad)` | `Prioridad = Peso × 100 + Cobertura`. La severidad domina y la evidencia desempata. |
| `recolectar_diagnosticos/3` | `recolectar_diagnosticos(+Id, +Validos, -Ordenados)` | Usa `findall/3`, `sort/2` (elimina duplicados) y `sort/4` (ordena por prioridad). |
| `estado_caso/2` | `estado_caso(+Diagnosticos, -Estado)` | `datos_insuficientes` si la lista está vacía; `ok` en otro caso (excluyentes con corte). |

## 6. Explicabilidad y datos faltantes

`analizar_caso/2` construye el reporte dentro de Prolog reutilizando los diagnósticos calculados por `diagnosticar_todos/3`. Cada explicación incluye las reglas cuya ruta intermedia tuvo éxito, los hechos positivos registrados en el caso, las negaciones por fallo que se comprobaron y las alternativas respaldadas por una prueba contradictoria.

Las sugerencias se generan a partir de síntomas asociados a componentes, las evidencias típicas de los diagnósticos y el catálogo vigente de pruebas, temperaturas, pitidos y antigüedad. Si un dato ya fue informado, Prolog no lo recomienda de nuevo. La prioridad favorece el dato compartido por varias hipótesis posibles.

Los predicados auxiliares de estas funciones están en la sección F de `base_conocimiento.pl`. Las reglas de inferencia numeradas son R1–R26: R26 es la regla genérica que evalúa los diagnósticos aprendidos en caliente (parte H). Los auxiliares de reporte no se cuentan como reglas de diagnóstico.

## 5. Hechos principales (base)

| Firma | Contenido |
| --- | --- |
| `componente/2` | Seis componentes de hardware cubiertos. |
| `sintoma_catalogo/2` | Diecinueve síntomas que el usuario puede reportar. |
| `relaciones_sintoma/1` | Hecho compacto con asociaciones entre síntomas y componentes; `sintoma_componente/2` las consulta. |
| `catalogo_pitidos/1` | Hecho compacto con patrones BIOS y componentes asociados; `codigo_pitido/2` lo consulta. |
| `catalogo_pruebas/1`, `catalogo_resultados/1` | Hechos compactos consultados mediante `prueba_catalogo/2` y `resultado_prueba/2`. |
| `catalogo_tipos_equipo/1`, `umbral/2` | Tipos de equipo en un hecho compacto y tres umbrales como hechos individuales. |
| `catalogo_gravedades/1`, `catalogo_pesos/1` | Hechos compactos consultados mediante `gravedad/2` y `peso_gravedad/2`. |
| `catalogo_acciones/1`, `catalogo_evidencia/1` | Acciones y evidencia típica almacenadas en hechos compactos. |
| `caso_ejemplo/2` | Ocho listas de condiciones listas para consultar con `consultar_caso/2`. |
| `equipo/3`, `observado/2`, `medicion/3`, `pitidos/2`, `prueba/3` | Predicados dinámicos donde se cargan temporalmente los datos de cada consulta; no tienen hechos de ejemplo permanentes. |

La base contiene exactamente **46 hechos**: 6 componentes, 19 síntomas, 10 hechos compactos de catálogo (incluido `catalogo_variables_discretas/1` del pre-procesamiento numérico), 3 umbrales y 8 casos de ejemplo. Los accesores de catálogos son reglas auxiliares; las reglas de inferencia numeradas son R1–R26. El léxico de la DCG (`vocabulario/2`), los alias base y el bloque de conocimiento aprendido no se cuentan entre esos hechos.

## 6. Entregable 3: lenguaje natural y conocimiento aprendido

| Firma | Parte | Descripción |
| --- | --- | --- |
| `tokenizar(+Texto, -Palabras)` | G.1 | Minúsculas, sin tildes ni signos; las comas quedan como el token `','`. |
| `vocabulario(?Categoria, ?Palabras)`, `lexico/2` | G.2 | Léxico de la gramática (determinantes, conectores, verbos, sustantivos del dominio...). |
| `alias_sintoma/2` | G.3 | Frases sinónimas base; incluye los `alias_aprendido/2` del experto. |
| `oracion//1`, `sintagma//1`, `hecho_mas_largo//1` | G.4 | Gramática: secuencia de sintagmas; en cada posición gana la lectura más larga. |
| `sintoma//1`, `temperatura//1`, `patron_pitidos//1`, `antiguedad//1`, `tipo_de_equipo//1`, `frase_alias//1` | G.4 | No terminales que producen los hechos simbólicos. |
| `parsear_oracion(+Texto, -Hechos, -NoReconocidas)` | G.5 | Interfaz de la DCG; `parsear_oracion_texto/3` devuelve los hechos como átomos para Python. |
| `regla_aprendida/8` (dinámico) | H | `regla_aprendida(Id, Nombre, Componente, Requeridas, Excluyentes, Certeza, Gravedad, Accion)`. |
| `diagnostico/3` (R26) | B | Evalúa cada regla aprendida con `cumple_condiciones/2` y `condicion_caso/2`. |
| `validar_regla/8`, `aprender_regla/8`, `olvidar_regla/1` | H | Validación, `assertz/1` y `retract/1` de reglas aprendidas. |
| `agregar_alias/2`, `olvidar_alias/2`, `listar_aliases_aprendidos/1` | H | Alias aprendidos (`alias_aprendido/2`, dinámico). |
| `listar_reglas_aprendidas/1`, `contenido_aprendido/1` | H | Listado para Python y texto del bloque persistido (`portray_clause/1`). |
| `catalogo_variables_discretas/1`, `nivel_discreto/2`, `discreto/3` | A.15, C | Niveles `dato(Variable, Nivel)` del pre-procesamiento numérico; R3b, R6b, R7b y R8b los usan. |

## 7. Entregable 4: consistencia de los hechos (parte I) y negación en la DCG

| Firma | Parte | Descripción |
| --- | --- | --- |
| `sintoma_requiere_energia/1` | I.1 | Síntomas imposibles si el equipo no enciende (no incluye `led_encendido`: un LED de reserva es posible). |
| `incompatible_dirigido/3`, `incompatible/3` | I.1 | `incompatible(A, B, Motivo)`: A y B no pueden darse a la vez. La forma dirigida se declara en un sentido; `incompatible/3` la hace simétrica. |
| `limite_plausible/3`, `tolerancia_lecturas/2` | I.1 | Rango físico de la temperatura (10–125 °C) y diferencia máxima entre dos lecturas (15 °C). |
| `nivel_temperatura/2`, `nivel_antiguedad/2` | I.1 | Nivel discreto que corresponde a una lectura numérica (mismos cortes que `preprocesamiento.py`). |
| `contradiccion(+Validos, -[Tipo, Elementos, Motivo])` | I.2 | Una cláusula por tipo: `sintomas_incompatibles`, `afirmado_y_negado`, `lectura_imposible`, `lecturas_discrepantes`, `nivel_discordante`, `datos_duplicados`. |
| `detectar_contradicciones(+Validos, -Lista)` | I.2 | Todas las contradicciones del caso, sin duplicados. Lista vacía = caso coherente. |
| `contradicciones_caso(+Entrada, -Lista)` | I.2 | Interfaz para Python (`MotorInferencia.verificar_consistencia`): valida la entrada y la revisa. |
| `diagnosticar_todos/3`, `analizar_caso/2` | D, F | Si hay contradicciones devuelven el estado `entrada_contradictoria` sin diagnósticos, sospechosos, explicación ni sugerencias. |
| `ausente(Sintoma)` | C, G | Hecho de entrada que significa «el síntoma NO ocurre». `clasificar_item/2` lo acepta; `cargar_item/2` lo ignora (no es evidencia) y solo sirve para detectar `afirmado_y_negado`. |
| `sintoma_negado//1`, `negador//0`, `encendido_afirmado//0` | G.4 | La DCG produce `ausente(S)` para «no huele a quemado» y `ausente(no_enciende)` para «sí enciende». |
| `emparejar_equipos/3` | G.5 | Una antigüedad por equipo mencionado, para que dos equipos distintos lleguen a la parte I. |
