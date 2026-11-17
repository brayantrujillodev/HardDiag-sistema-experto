<p align="center"><img src="logohardiag.jpeg" alt="Logo de HardDiag" width="220"></p>

# HardDiag

Sistema experto universitario para orientar el diagnóstico de fallas de hardware en computadores. La interfaz Streamlit recibe y valida los datos; el motor SWI-Prolog aplica las reglas, explica las conclusiones y recomienda la información adicional que ayudaría a distinguir hipótesis.

## Clonar y ejecutar en otro PC

```powershell
git clone https://github.com/brayantrujillodev/HardDiag-sistema-experto.git
cd HardDiag-sistema-experto
py -m pip install -r requirements.txt
py pruebas.py
py -m streamlit run main.py
```

Antes hay que instalar Python 3.10+ y SWI-Prolog de 64 bits (ver «Instalación»). Usuario del modo experto: `experto`, contraseña de demostración `HardDiag2026` (cámbiala con `py autenticacion.py --configurar`).

> HardDiag es un proyecto educativo, no sustituye una revisión profesional. Si hay olor a quemado, apaga y desconecta el computador. No abras la fuente de poder.

## Requisitos

- Windows 10/11.
- Python 3.10 o posterior.
- SWI-Prolog instalado y disponible para PySwip.
- Navegador web moderno.

## Instalación

### 1. Instalar SWI-Prolog

Descárgalo e instálalo desde [swi-prolog.org](https://www.swi-prolog.org/download/stable). En el instalador de Windows, habilita la opción para agregar SWI-Prolog al `PATH` si está disponible. Abre una terminal nueva y verifica:

```powershell
swipl --version
```

PySwip utiliza la biblioteca compartida de SWI-Prolog. Si Python no logra localizarla, configura `PATH` para incluir la carpeta `bin` de SWI-Prolog y verifica la arquitectura compatible (Python y SWI-Prolog deben ser ambos de 64 bits o ambos de 32 bits). Después de modificar `PATH`, cierra y abre de nuevo Visual Studio Code.

### 2. Instalar dependencias Python

Abre la terminal integrada de VS Code en la carpeta del repositorio:

```powershell
py --version
py -m pip install -r requirements.txt
```

La instalación directa equivalente solicitada es:

```powershell
py -m pip install pyswip streamlit scikit-learn
```

`requirements.txt` declara PySwip, Streamlit y scikit-learn (este último solo para el pre-procesamiento numérico opcional; sin él se usa una heurística por umbrales). No se necesita Node.js.

## Ejecutar la interfaz Streamlit

Desde la carpeta que contiene `main.py` y `base_conocimiento.pl`:

```powershell
py -m streamlit run main.py
```

Streamlit muestra la dirección local en la terminal y abre el navegador. Normalmente es:

```text
http://localhost:8501
```

La interfaz utiliza un tema oscuro con acentos luminosos. Para detener la aplicación, vuelve a la terminal y presiona **Ctrl+C**. La recarga automática de archivos está desactivada para que no aparezca el aviso en inglés de Streamlit; después de cambiar el código, reinicia la aplicación y actualiza la página del navegador. No ejecutes `py main.py` para iniciar la interfaz; usa `streamlit run` como se indica.

## Uso

1. Empieza en **«¿Qué le sucede al computador?»**: selecciona síntomas o escribe libremente una descripción en el campo multilínea (por ejemplo: "no prende", "pantalla negra", "la pantalla parpadea y se apaga jugando"). La gramática DCG de Prolog analiza la oración y la interfaz muestra los hechos que extrajo y las palabras que no reconoció. Si no encuentra síntomas, avisa que no puede inferir un diagnóstico; un experto puede enseñarle la frase. Si indicas lentitud, aparece una guía para precisar si tarda al iniciar, se congela o el disco hace clic.
2. La DCG también reconoce temperaturas (*la cpu está a 95 grados*), patrones de pitidos (*un pitido largo y dos cortos*) y la antigüedad del equipo (*mi portátil de 7 años*).
3. En **«Datos que pueden afinar el resultado»** puedes abrir las secciones opcionales para agregar temperatura, antigüedad, pitidos, pruebas o lecturas numéricas (horas de uso, ocupación del disco) que discretiza el clasificador. No es necesario completar estos datos para analizar.
4. Para crear diagnósticos o enseñar vocabulario, pulsa **«Ir al modo experto»** e inicia sesión con el rol Experto (ver la sección del Entregable 3). **«Volver al diagnóstico normal»** retorna al formulario.
5. Puedes registrar la marca del computador; se muestra como dato informativo y no modifica las reglas de diagnóstico.
6. Deja marcada **«No he realizado pruebas»** si corresponde. Si desmarcas esa opción, selecciona las pruebas realizadas y su resultado. Las pruebas sin resultado no se envían como evidencia.
7. Pulsa **«Analizar mi computador»** y revisa las hipótesis, la evidencia y las recomendaciones.

### Modos de uso

- **Normal:** formulario de síntomas, descripción libre (analizada por la DCG de Prolog), datos opcionales, lecturas numéricas y resultados del diagnóstico. No muestra herramientas de administración del conocimiento.
- **Experto:** se abre con **«Ir al modo experto»** y exige iniciar sesión con un usuario de rol **Experto**. Permite crear diagnósticos nuevos en caliente, listarlos y eliminarlos, y administrar frases (alias) de la gramática. Todo cambio se inyecta con `assertz/1` y se escribe en `base_conocimiento.pl`. Usa **«Cerrar sesión»** o **«Volver al diagnóstico normal»** para salir.

La interfaz, los resultados y las explicaciones se presentan en español. El resultado contiene los diagnósticos calculados por Prolog (nivel de daño según el tipo de falla, certeza, severidad, prioridad y evidencia), una solución recomendada y pasos orientativos para cada daño reconocido. El nivel de daño se clasifica como leve, moderado o grave a partir de la gravedad base de cada diagnóstico; la severidad puede aumentar por los factores de riesgo del caso. Si faltan datos, muestra componentes sospechosos y el panel **«¿Qué falta?»** con pruebas o datos priorizados por las hipótesis compatibles. Abre **«Ver explicación del diagnóstico»** para ver las reglas comprobadas, los hechos del caso, las negaciones por fallo y las alternativas descartadas mediante pruebas. Las guías son educativas; si no tienes experiencia en reparaciones internas, consulta a un técnico.

## Entregable 3: lenguaje natural (DCG) y aprendizaje dinámico en caliente

### 1. Entrada en lenguaje natural con una DCG

El texto libre ya no se interpreta en Python. `motor_inferencia.py` envía la oración tal cual a Prolog mediante PySwip y Prolog responde con los hechos simbólicos:

```text
Python  ──parsear_oracion_texto('mi pc no prende y huele a quemado', H, N)──▶  Prolog
Python  ◀──────────── H = [no_enciende, olor_quemado], N = [] ──────────────  Prolog
```

La parte G de `base_conocimiento.pl` contiene la gramática:

1. `tokenizar/2` pasa el texto a minúsculas, quita tildes y signos y lo divide en palabras (las comas se conservan como separador).
2. `oracion//1` analiza la lista de palabras con `phrase/2`. Una oración es una secuencia de **sintagmas** unidos por **conectores** (`y`, `e`, `ni`, `pero`, `además`, `,`...) y acompañados de palabras de **relleno** (artículos, preposiciones, "mi computador", "presenta"...).
3. Cada sintagma lo reconoce un no terminal con su propio léxico (`vocabulario/2`): `sintoma//1` (los 19 síntomas del catálogo y sus variantes: *la pantalla se pone azul*, *el disco duro hace ruido*, *no detecta el disco*...), `temperatura//1` (*la cpu está a 95 grados*, *97 °C*), `patron_pitidos//1` (*un pitido largo y dos cortos*), `antiguedad//1` y `tipo_de_equipo//1` (*mi portátil de 7 años*), `frase_alias//1` (alias base y aprendidos) e `identificador_sintoma//1` (`pantalla_azul`).
4. `hecho_mas_largo//1` elige, en cada posición, la lectura que consume más palabras (*tres pitidos cortos* gana a *tres pitidos*).
5. Las palabras que no pertenecen al léxico se devuelven en `NoReconocidas`; la interfaz las muestra para que el experto pueda enseñarlas.

Ejemplos (todos verificados en `pruebas.py`):

| Oración | Hechos extraídos por la DCG |
| --- | --- |
| mi computador no enciende y huele a quemado | `no_enciende`, `olor_quemado` |
| La pantalla se pone azul, se reinicia sola y el disco hace clic | `pantalla_azul`, `reinicios_aleatorios`, `ruido_clic` |
| el pc va lento y la cpu está a 95 grados | `lentitud`, `temp_cpu(95)` |
| Al encender hace tres pitidos cortos y la pantalla queda en negro | `pitidos(tres_cortos)`, `pantalla_negra` |
| mi portátil de 7 años pierde la fecha y hora | `hora_incorrecta`, `equipo(portatil,7)` |
| tarda mucho en iniciar y el disco duro hace ruido | `arranque_lento`, `ruido_clic` |

Desde la consola de SWI-Prolog:

```prolog
?- parsear_oracion('el pc va lento y la cpu esta a 95 grados', Hechos, NoRec).
Hechos = [lentitud, temp_cpu(95)], NoRec = [].

?- consultar_texto('mi pc no prende y huele a quemado', Respuesta).
```

La entrada formal anterior (`no_enciende, pitidos(tres_cortos), temp_cpu(97), prueba(...)`) sigue funcionando; si se mezclan, los elementos formales se envían tal cual y las frases pasan por la DCG.

### 2. Modo Experto con rol y adquisición de conocimiento

**Inicio de sesión.** Las credenciales viven en `config_experto.json` como hash PBKDF2-SHA256 con sal (nunca en texto plano). La configuración entregada trae el usuario `experto` con la contraseña de demostración `HardDiag2026`; cámbiala antes de publicar el proyecto:

```powershell
py autenticacion.py --configurar
```

También se pueden definir las variables de entorno `HARDDIAG_EXPERTO_USUARIO` y `HARDDIAG_EXPERTO_HASH` (el hash con el mismo formato), que tienen prioridad sobre el archivo.

**Crear un diagnóstico nuevo** (pestaña «Nuevo diagnóstico»): nombre legible, identificador Prolog (se propone a partir del nombre), componente, síntomas requeridos, condiciones adicionales (pitidos, resultado de pruebas, temperatura alta, equipo antiguo), condiciones que lo excluyen, certeza, gravedad y acción recomendada. Al guardar:

1. Prolog valida la regla con `validar_regla/8` (identificador nuevo, componente y condiciones existentes, al menos un síntoma, nada a la vez requerido y excluyente).
2. Python la inyecta en memoria con `assertz/1` vía PySwip: `regla_aprendida(Id, Nombre, Componente, Requeridas, Excluyentes, Certeza, Gravedad, Accion)`.
3. Python reescribe el bloque final de `base_conocimiento.pl` con el texto que genera Prolog (`contenido_aprendido/1`, con `portray_clause/1`). La escritura es atómica (archivo temporal + reemplazo); si falla, la regla se retira de la memoria.

El bloque persistido queda así (incluye como comentario la regla lógica equivalente):

```prolog
%% === INICIO CONOCIMIENTO APRENDIDO (no editar a mano) ===
alias_aprendido(apagados_repentinos, 'se muere el pc').

% R26 aprendida: Fuente de poder sobrecargada
%   diagnostico(E, fuente_sobrecargada, media) :-
%       observado(E, apagados_repentinos),
%       observado(E, olor_quemado),
%       \+ observado(E, no_enciende),
%       \+ descartado(E, fuente_sobrecargada).
regla_aprendida(fuente_sobrecargada, 'Fuente de poder sobrecargada', fuente_poder, [apagados_repentinos, olor_quemado], [no_enciende], media, alta, 'Revisar el consumo del equipo e instalar una fuente de mayor potencia.').
%% === FIN CONOCIMIENTO APRENDIDO ===
```

**Integración con el motor.** La regla genérica **R26** (`diagnostico/3`) evalúa cada `regla_aprendida/8`. Además `gravedad/2`, `accion/2`, `evidencia_tipica/2`, `componente_diagnostico/2`, `traza_diagnostico/3`, `negacion_traza/4` y `dato_recomendado/5` tienen una cláusula para las reglas aprendidas, de modo que el diagnóstico nuevo aparece en los resultados, en la explicación (regla R26, hechos y exclusiones) y en las sugerencias de datos faltantes, igual que los originales.

La pestaña «Reglas aprendidas» lista y elimina reglas (`retract/1` y reescritura del bloque) y muestra el bloque tal como está en el archivo. La pestaña «Vocabulario» enseña frases nuevas (`alias_aprendido/2`) que la DCG reconoce dentro de cualquier oración. Si existe un `aliases_aprendidos.json` de la versión anterior, sus alias se migran al `.pl` al iniciar y el JSON se renombra a `aliases_aprendidos.json.migrado`.

### 3. (Opcional híbrido) Pre-procesamiento numérico

`preprocesamiento.py` entrena un `DecisionTreeClassifier` de scikit-learn por variable con el dataset sintético `datos_preprocesamiento.csv` (regenerable con `py preprocesamiento.py --generar`) y convierte lecturas continuas en hechos discretos `dato(Variable, Nivel)` antes de enviarlos a Prolog. Si scikit-learn no está instalado, usa una heurística por umbrales con las mismas etiquetas.

| Variable | Niveles |
| --- | --- |
| Temperatura del procesador (°C) | normal (<70), elevada (70–85), alta (86–94), crítica (≥95) |
| Antigüedad (años) | nuevo (<2), medio (2–4), antiguo (≥5) |
| Horas de uso diario | bajo (<4), moderado (4–9), intensivo (≥10) |
| Ocupación del disco (%) | normal (<75), alto (75–89), crítico (≥90) |

Prolog los usa en R3b (sobrecalentamiento), R7b (equipo antiguo), R8b (factor de riesgo) y R6b (indicios sobre componentes). En la interfaz están en «Lecturas numéricas (clasificador ligero)»; el clasificador también recibe la temperatura y la antigüedad que extrajo la DCG.

### 4. Guion para el video de persistencia

1. Abre una terminal en la carpeta del proyecto y muestra que el bloque está vacío:
   `Select-String -Path base_conocimiento.pl -Pattern "CONOCIMIENTO APRENDIDO" -Context 0,3`
2. Inicia la aplicación: `py -m streamlit run main.py`.
3. En el modo normal escribe *«se apaga de repente y huele a quemado»* y pulsa **Analizar**. Muestra los hechos que extrajo la DCG y que no hay un diagnóstico confirmado.
4. Pulsa **Ir al modo experto**, intenta entrar con una contraseña incorrecta (se rechaza) y luego entra con `experto` / tu contraseña.
5. En «Nuevo diagnóstico» crea *Fuente de poder sobrecargada*: componente fuente de poder; síntomas requeridos «El equipo se apaga de repente» y «Hay olor a quemado»; excluyente «El equipo no enciende»; certeza media; gravedad alta; una acción. Pulsa **Inyectar regla y guardarla en el .pl**.
6. Abre «Reglas aprendidas» → «Ver el bloque persistido en base_conocimiento.pl» y muestra la regla escrita. Opcional: en «Vocabulario» enseña *«se muere el pc»* → «El equipo se apaga de repente».
7. Vuelve al modo normal, repite la oración del paso 3 y muestra que ahora aparece **Fuente de poder sobrecargada**, con la regla R26 en la explicación.
8. **Reinicia:** cierra la app con Ctrl+C en la terminal y vuelve a ejecutar `py -m streamlit run main.py`. Recarga el navegador.
9. Sin entrar al modo experto, escribe *«se muere el pc y huele a quemado»* y analiza: el diagnóstico aprendido sigue funcionando, porque se cargó desde el `.pl`.
10. Muestra el archivo `base_conocimiento.pl` en VS Code (final del archivo) y, si quieres, prueba en `swipl`: `?- consult('base_conocimiento.pl'), listar_reglas_aprendidas(L).`
11. Para dejar la base limpia, elimina la regla desde «Reglas aprendidas».

Para ensayar sin tocar la base real puedes apuntar la app a una copia: `$env:HARDDIAG_BASE_CONOCIMIENTO = "C:\ruta\copia.pl"; py -m streamlit run main.py`.

## Entregable 4: contradicciones, pruebas de estrés y sustentación

### 1. Manejo de contradicciones (parte I de `base_conocimiento.pl`)

Antes de inferir, Prolog revisa que los hechos del caso sean lógicamente compatibles. Si no lo son, `diagnosticar_todos/3` y `analizar_caso/2` devuelven el estado **`entrada_contradictoria`** y **no emiten diagnóstico, sospechosos, explicación ni sugerencias**: es mejor pedir una aclaración que concluir sobre datos incoherentes. La interfaz muestra cada contradicción con su motivo.

| Tipo | Ejemplo | Por qué se bloquea |
| --- | --- | --- |
| `sintomas_incompatibles` | `no_enciende` + `ventiladores_giran` | Un equipo sin energía no puede tener ventiladores girando, pantalla azul, lentitud, clics del disco... |
| `afirmado_y_negado` | «huele a quemado y no huele a quemado» | El mismo síntoma se reporta y se niega. |
| `lectura_imposible` | `temp_cpu(500)` o `temp_cpu(3)` | Fuera del rango físico 10–125 °C. |
| `lecturas_discrepantes` | `temp_cpu(40)` + `temp_cpu(99)` | Dos lecturas del mismo caso difieren en más de 15 °C. |
| `nivel_discordante` | `temp_cpu(97)` + `dato(temperatura_cpu, normal)` | La lectura y su nivel discreto no coinciden. |
| `datos_duplicados` | `prueba(cambio_cable, ok)` + `prueba(cambio_cable, falla)` | Dos valores distintos para el mismo dato (prueba, pitidos, equipo, nivel). |

No se bloquea lo que sí puede ocurrir: `no_enciende` con `led_encendido` (LED de reserva), `no_enciende` con pitidos de la BIOS, `pantalla_negra` con `lineas_en_pantalla` (caso de GPU). La detección vive solo en Prolog; Python únicamente invoca `contradicciones_caso/2` (`MotorInferencia.verificar_consistencia`) y presenta el resultado.

**Negación en la DCG.** La auditoría de entradas ambiguas descubrió que «mi pc *no* huele a quemado» se leía como `olor_quemado`. La DCG ahora produce `ausente(olor_quemado)` (un síntoma precedido por *no* o *ni*), y «sí enciende» produce `ausente(no_enciende)`. Estos hechos no son evidencia para el diagnóstico, pero permiten detectar `afirmado_y_negado`. También se aceptan temperaturas de hasta 500 °C en la oración (para señalarlas como imposibles en lugar de ignorarlas) y varias antigüedades («un portátil de 2 años y un escritorio de 9 años» → dos equipos distintos).

### 2. Pruebas de estrés

```powershell
swipl -q -f none -g correr_pruebas -t halt pruebas_estres.pl   # solo necesita SWI-Prolog
py pruebas.py                                                 # incluye el bloque «CONSISTENCIA»
```

`pruebas_estres.pl` ejecuta 62 verificaciones: 20 contradicciones que deben bloquearse, 13 combinaciones coherentes que no deben bloquearse (falsos positivos), 15 oraciones ambiguas enviadas a la DCG, 8 entradas malformadas (no es lista, variables sueltas, temperaturas negativas, `ausente/1` inventado...) y 6 propiedades verificadas sobre **todos los pares de los 19 síntomas** (171 pares): estado siempre válido, una contradicción nunca emite diagnóstico, el resultado no depende del orden de los hechos, `analizar_caso/2` coincide con `consultar_caso/2`, los 19 síntomas juntos se bloquean y una entrada de 600 hechos se resuelve en menos de 0,1 s. La salida queda en `evidencia_estres.txt`; `pruebas.py` repite lo esencial a través de PySwip y también ejecuta esta batería.

### 3. Informe técnico

`informe_tecnico.pdf` consolida la arquitectura final, el árbol lógico principal y el reporte de las pruebas de estrés (fuente en `informe_tecnico.html`).

### 4. Sustentación: dónde modificar en vivo

| Integrante | Tarea típica | Dónde |
| --- | --- | --- |
| A (motor simbólico) | Cambiar un corte `!` o la gramática | `clasificar_item/2`, `estado_caso/2` y `cobertura/3` (cortes); `hecho//1`, `sintoma//1`, `sintoma_negado//1` y `vocabulario/2` (DCG); `incompatible_dirigido/3` y `contradiccion/2` (consistencia). |
| B (integración) | Captura en Python o traza de la caja blanca | `preparar_entrada()` y `mostrar_resultado()` en `main.py`; `MotorInferencia.analizar_caso()` y `formatear_respuesta()` en `motor_inferencia.py`; `presentar_hecho()`/`presentar_negacion()` (traza). |

Para agregar una incompatibilidad basta una cláusula: `incompatible_dirigido(ventilador_detenido, temp_cpu_baja, 'Motivo').` — y comprobarla con `swipl -g correr_pruebas -t halt pruebas_estres.pl`.

## ¿Qué contiene el proyecto?

| Archivo | Descripción |
| --- | --- |
| `base_conocimiento.pl` | Base Prolog: hechos, reglas R1–R26, diagnóstico, trazas y sugerencias (partes A–F), DCG de lenguaje natural (parte G), adquisición de conocimiento (parte H), consistencia de hechos (parte I) y el bloque de conocimiento aprendido. |
| `motor_inferencia.py` | Adaptador PySwip: carga Prolog, envía oraciones a la DCG, inyecta reglas y alias con `assertz/1`, los persiste en el `.pl` y convierte respuestas, explicaciones y sugerencias. |
| `main.py` | Interfaz Streamlit: diagnóstico normal, inicio de sesión y panel del modo experto. |
| `autenticacion.py` | Verificación del rol Experto con hashes PBKDF2 y comando `--configurar`. |
| `config_experto.json` | Usuario experto y hash de su contraseña. |
| `preprocesamiento.py` | Clasificador ligero (scikit-learn) que discretiza lecturas numéricas. |
| `datos_preprocesamiento.csv` | Dataset sintético con el que se entrena el clasificador. |
| `main_consola.py` | Interfaz interactiva original por consola (acepta oraciones libres). |
| `pruebas.py` | Casos del motor, integración, DCG, consistencia (Entregable 4) y persistencia de reglas aprendidas. |
| `pruebas_estres.pl` | Batería de estrés en Prolog puro (contradicciones, DCG ambigua, robustez, propiedades); salida en `evidencia_estres.txt`. |
| `informe_tecnico.pdf` | Informe técnico del Entregable 4 (fuente `informe_tecnico.html`). |
| `evidencia_pruebas.txt` | Salida guardada por `pruebas.py`. |
| `requirements.txt` | Dependencias Python del proyecto. |
| `web_app.py`, `index.html` | Interfaz web HTTP anterior; se conserva como alternativa, pero el entregable principal es la interfaz Streamlit. |
| `ficha_proyecto.md` | Ficha académica, alcance e integrantes. |
| `diccionario_predicados.md` | Referencia de predicados Prolog. |

## Arquitectura

```text
Formulario Streamlit (main.py) ── login de experto (autenticacion.py)
        ↓ oración libre / entrada formal / lecturas numéricas / reglas nuevas
Adaptador PySwip (motor_inferencia.py) ── preprocesamiento.py (dato/2)
        ↓ parsear_oracion_texto/3 · analizar_caso/2 · assertz/1 · retract/1
Base SWI-Prolog (base_conocimiento.pl)
        ↓ DCG, diagnóstico (R1–R26), traza, exclusiones, sugerencias
        ↓ bloque de conocimiento aprendido (persistencia)
Presentación en Streamlit
```

La inferencia, el análisis sintáctico del lenguaje natural, la validación de reglas nuevas, la explicación y la priorización de datos faltantes se realizan en Prolog. Python se ocupa de la interfaz, del control de acceso, de la discretización numérica y de escribir en el archivo el texto que Prolog genera.

## Base de conocimiento: hechos y reglas

Los catálogos relacionados están almacenados como hechos compactos para consultar información de componentes, pruebas, resultados, umbrales, diagnósticos y acciones recomendadas. La traza informa reglas solo cuando la ruta Prolog correspondiente tuvo éxito. El panel de información faltante se basa en catálogos, evidencias típicas y pruebas que existen en la propia base.

Los componentes cubiertos son fuente de poder, placa base, procesador/refrigeración, memoria RAM, almacenamiento y tarjeta gráfica/video. Los diagnósticos incluyen fallas de fuente, video, placa base, refrigeración, RAM, disco y batería CMOS, más los que el experto agregue en caliente.

## Ejecutar pruebas

```powershell
py pruebas.py
```

El script ejecuta 58 verificaciones y guarda la salida en `evidencia_pruebas.txt`:

- 11 casos base del motor (diagnóstico, exclusiones, bordes).
- 9 comprobaciones de integración: explicación, datos insuficientes, varias hipótesis, sugerencias, entrada sin diagnóstico, inventario, descripción natural, **oración completa → DCG → diagnóstico** y **preprocesamiento → `dato/2` → R3b**.
- 10 oraciones en español analizadas por la DCG.
- 24 verificaciones de consistencia del Entregable 4 (10 contradicciones, 7 oraciones ambiguas, 5 coherentes, 1 de `analizar_caso` y la batería `pruebas_estres.pl`).
- 4 fases de persistencia sobre una **copia temporal** de `base_conocimiento.pl`; cada fase corre en un proceso de Python nuevo (equivale a reiniciar la app): crear la regla y un alias, verificar tras el reinicio que siguen en el `.pl` y diagnostican (y que la condición excluyente funciona), eliminarlos y verificar tras otro reinicio que ya no existen.

El comando debe terminar con código 0 e informar todas las verificaciones aprobadas.

## Ejecutar la consola original

La consola anterior se conserva en:

```powershell
py main_consola.py
```

## Solución de problemas

### `swipl` no se reconoce

Instala SWI-Prolog, comprueba su carpeta `bin` en `PATH`, reinicia VS Code y vuelve a comprobar:

```powershell
swipl --version
```

### PySwip no encuentra SWI-Prolog

Verifica que SWI-Prolog está instalado, que `PATH` incluye su carpeta `bin`, que Python y SWI-Prolog tienen la misma arquitectura y que reiniciaste la terminal después del cambio. Reinstala dependencias si hace falta:

```powershell
py -m pip install -r requirements.txt
```

### Streamlit no se reconoce

Ejecuta el módulo con el intérprete de Python:

```powershell
py -m streamlit run main.py
```

### Error al abrir `base_conocimiento.pl`

Ejecuta el comando desde la carpeta del proyecto. El motor también localiza la base respecto a `motor_inferencia.py`, por lo que no es necesario codificar una ruta absoluta.

## Alcance y limitaciones

El sistema orienta sobre fallas de hardware de computadores personales. No diagnostica fallas de software, sistema operativo, virus, redes, impresoras, teléfonos o consolas, y no reemplaza pruebas físicas ni la evaluación de un técnico. Los códigos de pitidos pueden variar según el fabricante del BIOS.
