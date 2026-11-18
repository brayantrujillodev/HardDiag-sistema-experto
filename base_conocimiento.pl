:- encoding(utf8).
%% =============================================================================
%%  base_conocimiento.pl
%%  Sistema Experto de Diagnóstico y Soporte Técnico para Fallos de Hardware
%%  Fundación Escuela Tecnológica de Neiva – Jesús Oviedo Pérez
%%
%%  ESTRUCTURA DEL ARCHIVO
%%    PARTE A. HECHOS     (conocimiento del dominio + casos de ejemplo)
%%    PARTE B. REGLAS     (3.1) encadenamiento en tres niveles
%%                        Nivel 1: validación preliminar (solo hechos base)
%%                        Nivel 2: inferencia intermedia (nivel 1 + hechos)
%%                        Nivel 3: conclusión final (nivel 2 + nivel 1 + hechos)
%%    PARTE C. LISTAS Y CONTROL DE FLUJO (3.2) listas, corte (!) y negación (\+)
%%    PARTE D. RECOLECCIÓN Y SEVERIDAD   (3.3) findall/3, sort/2 y severidad
%%    PARTE E. INTERFAZ PARA PYTHON      predicados que invoca el puente
%%    PARTE F. EXPLICABILIDAD            trazas y datos faltantes
%%    PARTE G. LENGUAJE NATURAL (DCG)    oraciones libres -> hechos simbólicos
%%    PARTE H. MODO EXPERTO              reglas y alias aprendidos en caliente
%%    PARTE I. CONSISTENCIA              contradicciones entre hechos (bloquean el diagnóstico)
%%    CONOCIMIENTO APRENDIDO             bloque final que escribe el modo experto
%%
%%  PREVENCIÓN DE CICLOS
%%    Las reglas están estratificadas: un predicado solo llama a predicados de
%%    un nivel inferior (N3 -> N2 -> N1 -> hechos). No hay recursión sobre el
%%    mismo predicado salvo en listas, y allí SIEMPRE se consume la cabeza
%%    antes de la llamada recursiva (recursión por la derecha, sobre la cola).
%%    No existe recursión izquierda. La meta que liga la variable del equipo
%%    (un hecho o una regla de nivel inferior) va siempre primero, y \+ solo
%%    se aplica con todas sus variables ya instanciadas.
%%
%%  USO RÁPIDO (SWI-Prolog):
%%    ?- consult('base_conocimiento.pl').
%%    ?- consultar_texto('no_enciende, olor_quemado', Respuesta).
%%    ?- consultar_texto('mi pc no prende y huele a quemado', Respuesta).
%%    ?- parsear_oracion('la cpu esta a 97 grados y el ventilador suena fuerte',
%%                       Hechos, NoReconocidas).
%%
%%  La base contiene exactamente 46 hechos: componentes, síntomas, catálogos
%%  compactos, umbrales y ocho casos de ejemplo. Los predicados de acceso a
%%  esos catálogos son reglas auxiliares; las reglas de inferencia son R1-R26
%%  (R26 evalúa las reglas que el experto aprende en caliente).
%% =============================================================================

% Los datos de un caso son dinámicos: la parte C los carga desde una lista
% enviada por Python y los elimina al terminar (ver cargar_caso/2).
% discreto/3 guarda los niveles que calcula el preprocesamiento numérico de
% Python (preprocesamiento.py) a partir de lecturas continuas.
:- dynamic equipo/3, observado/2, medicion/3, pitidos/2, prueba/3, discreto/3.

% Conocimiento adquirido en caliente desde el modo experto (parte H). Sus
% hechos se escriben al final de este archivo, dentro del bloque de
% conocimiento aprendido, para que sobrevivan a un reinicio del programa.
:- dynamic regla_aprendida/8, alias_aprendido/2.


%% =============================================================================
%%  PARTE A. HECHOS
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  A.1 Componentes de hardware cubiertos
%%      componente(Id, Descripcion)
%% -----------------------------------------------------------------------------
componente(fuente_poder,   'Fuente de poder').
componente(placa_base,     'Placa base').
componente(procesador,     'Procesador y refrigeración').
componente(memoria_ram,    'Memoria RAM').
componente(almacenamiento, 'Almacenamiento (HDD/SSD)').
componente(tarjeta_video,  'Tarjeta gráfica y video').

%% -----------------------------------------------------------------------------
%%  A.2 Catálogo de síntomas que el usuario puede reportar
%%      sintoma_catalogo(Sintoma, Descripcion)
%% -----------------------------------------------------------------------------
sintoma_catalogo(no_enciende,          'El equipo no enciende').
sintoma_catalogo(led_encendido,        'Algún LED del equipo está encendido').
sintoma_catalogo(apagados_repentinos,  'El equipo se apaga de repente').
sintoma_catalogo(olor_quemado,         'Hay olor a quemado').
sintoma_catalogo(pitidos_arranque,     'Se oyen pitidos al arrancar').
sintoma_catalogo(hora_incorrecta,      'La fecha y hora se pierden').
sintoma_catalogo(error_bios,           'Aparece un error en la BIOS').
sintoma_catalogo(reinicios_aleatorios, 'El equipo se reinicia solo').
sintoma_catalogo(ventilador_ruidoso,   'El ventilador hace ruido excesivo').
sintoma_catalogo(ventilador_detenido,  'El ventilador no gira').
sintoma_catalogo(ventiladores_giran,   'Los ventiladores giran al encender').
sintoma_catalogo(lentitud,             'El equipo va muy lento').
sintoma_catalogo(pantalla_azul,        'Aparece pantalla azul').
sintoma_catalogo(bloqueos,             'El equipo se congela').
sintoma_catalogo(arranque_lento,       'El arranque tarda demasiado').
sintoma_catalogo(ruido_clic,           'El disco hace clics').
sintoma_catalogo(disco_no_encontrado,  'Aparece "disco no encontrado"').
sintoma_catalogo(pantalla_negra,       'La pantalla queda en negro').
sintoma_catalogo(lineas_en_pantalla,   'Aparecen líneas en la pantalla').
sintoma_catalogo(artefactos_video,     'Aparecen artefactos en la imagen').

%% -----------------------------------------------------------------------------
%%  A.3 Síntomas y componentes con los que se asocian
%%      sintoma_componente(Sintoma, ComponenteAsociado)
%% -----------------------------------------------------------------------------
relaciones_sintoma([
    no_enciende-fuente_poder,
    no_enciende-placa_base,
    apagados_repentinos-fuente_poder,
    olor_quemado-fuente_poder,
    pitidos_arranque-memoria_ram,
    pitidos_arranque-placa_base,
    hora_incorrecta-placa_base,
    error_bios-placa_base,
    reinicios_aleatorios-procesador,
    reinicios_aleatorios-fuente_poder,
    ventilador_ruidoso-procesador,
    ventilador_detenido-procesador,
    lentitud-procesador,
    lentitud-almacenamiento,
    pantalla_azul-memoria_ram,
    bloqueos-memoria_ram,
    bloqueos-almacenamiento,
    arranque_lento-almacenamiento,
    ruido_clic-almacenamiento,
    disco_no_encontrado-almacenamiento,
    pantalla_negra-tarjeta_video,
    lineas_en_pantalla-tarjeta_video,
    artefactos_video-tarjeta_video
]).

%% -----------------------------------------------------------------------------
%%  A.4 Códigos de pitidos de la BIOS (referenciales: varían según fabricante)
%%      codigo_pitido(Patron, ComponenteIndicado)
%% -----------------------------------------------------------------------------
catalogo_pitidos([
    tres_cortos-memoria_ram,
    un_largo_dos_cortos-tarjeta_video,
    cortos_repetidos-fuente_poder,
    un_largo_tres_cortos-placa_base
]).

%% -----------------------------------------------------------------------------
%%  A.5 Pruebas simples que el usuario puede realizar
%%      prueba_catalogo(Nombre, Descripcion)
%% -----------------------------------------------------------------------------
catalogo_pruebas([
    fuente_con_probador-'Probar la fuente con un probador de fuentes',
    cambio_cable-'Cambiar el cable de video',
    otro_monitor-'Conectar otro monitor',
    gpu_en_otro_equipo-'Probar la tarjeta gráfica en otro equipo',
    reasentar_ram-'Sacar y volver a colocar la memoria RAM',
    smart_disco-'Revisar el estado de salud del disco',
    cambio_bateria-'Cambiar la batería CMOS'
]).

%% -----------------------------------------------------------------------------
%%  A.6 Resultados válidos de una prueba
%%      resultado_prueba(Resultado, Descripcion)
%% -----------------------------------------------------------------------------
catalogo_resultados([
    falla-'La prueba detectó una falla',
    ok-'El componente pasó la prueba',
    resuelve-'La acción resolvió el problema',
    no_resuelve-'La acción no resolvió el problema'
]).

%% -----------------------------------------------------------------------------
%%  A.7 Tipos de equipo aceptados
%%      tipo_equipo(Tipo, Descripcion)
%% -----------------------------------------------------------------------------
catalogo_tipos_equipo([
    escritorio-'Computador de escritorio',
    portatil-'Computador portátil',
    desconocido-'Tipo de equipo no indicado'
]).

%% -----------------------------------------------------------------------------
%%  A.8 Umbrales de decisión
%%      umbral(Parametro, Valor)
%% -----------------------------------------------------------------------------
umbral(temp_cpu_max_celsius,     85).
umbral(temp_cpu_critica_celsius, 95).
umbral(antiguedad_critica_anios, 5).

%% -----------------------------------------------------------------------------
%%  A.9 Gravedad base de cada diagnóstico posible
%%      gravedad(Diagnostico, Nivel)         Nivel: baja | media | alta
%% -----------------------------------------------------------------------------
catalogo_gravedades([
    fuente_poder_defectuosa-alta,
    cable_o_monitor_defectuoso-baja,
    gpu_defectuosa-alta,
    placa_base_defectuosa-alta,
    refrigeracion_deficiente-media,
    ram_mal_asentada-baja,
    ram_defectuosa-media,
    disco_fallando-alta,
    bateria_cmos_agotada-baja
]).

%% -----------------------------------------------------------------------------
%%  A.10 Peso numérico de cada nivel de severidad
%%       peso_gravedad(Nivel, Peso)
%% -----------------------------------------------------------------------------
catalogo_pesos([
    baja-1,
    media-2,
    alta-3,
    critica-4
]).

%% -----------------------------------------------------------------------------
%%  A.11 Acción recomendada para cada diagnóstico
%%       accion(Diagnostico, TextoDeLaAccion)
%% -----------------------------------------------------------------------------
catalogo_acciones([
    fuente_poder_defectuosa-'Desconectar el equipo y reemplazar la fuente de poder.',
    cable_o_monitor_defectuoso-'Reemplazar el cable de video o el monitor que falló en la prueba.',
    gpu_defectuosa-'Reemplazar la tarjeta gráfica o llevar el equipo a un técnico.',
    placa_base_defectuosa-'Llevar el equipo a un técnico para revisar y reparar la placa base.',
    refrigeracion_deficiente-'Limpiar el polvo, cambiar la pasta térmica y reemplazar el ventilador.',
    ram_mal_asentada-'Reasentar el módulo de RAM y limpiar los contactos.',
    ram_defectuosa-'Reemplazar el módulo de memoria RAM defectuoso.',
    disco_fallando-'Respaldar la información de inmediato y reemplazar el disco.',
    bateria_cmos_agotada-'Cambiar la batería CMOS (CR2032) de la placa base.'
]).

%% -----------------------------------------------------------------------------
%%  A.12 Evidencia típica de cada diagnóstico (lista de condiciones)
%%       evidencia_tipica(Diagnostico, ListaDeCondiciones)
%%       Condiciones especiales: temp_cpu_alta y equipo_antiguo (ver C.2).
%% -----------------------------------------------------------------------------
catalogo_evidencia([
    fuente_poder_defectuosa-[no_enciende, olor_quemado, prueba(fuente_con_probador, falla)],
    cable_o_monitor_defectuoso-[pantalla_negra, ventiladores_giran, prueba(cambio_cable, resuelve)],
    gpu_defectuosa-[pantalla_negra, ventiladores_giran,
                    prueba(cambio_cable, no_resuelve), prueba(otro_monitor, no_resuelve)],
    placa_base_defectuosa-[no_enciende, prueba(fuente_con_probador, ok),
                           pitidos(un_largo_tres_cortos)],
    refrigeracion_deficiente-[temp_cpu_alta, ventilador_ruidoso],
    ram_mal_asentada-[pantalla_azul, prueba(reasentar_ram, resuelve)],
    ram_defectuosa-[pitidos(tres_cortos), pantalla_azul,
                    prueba(reasentar_ram, no_resuelve)],
    disco_fallando-[arranque_lento, ruido_clic, prueba(smart_disco, falla)],
    bateria_cmos_agotada-[hora_incorrecta, equipo_antiguo]
]).

%% -----------------------------------------------------------------------------
%%  A.13 Ocho casos de ejemplo para consultas manuales
%% -----------------------------------------------------------------------------
caso_ejemplo(fuente, [no_enciende, olor_quemado,
                      prueba(fuente_con_probador, falla)]).
caso_ejemplo(cable_video, [pantalla_negra, ventiladores_giran,
                           prueba(cambio_cable, resuelve)]).
caso_ejemplo(grafica, [pantalla_negra, ventiladores_giran,
                       prueba(cambio_cable, no_resuelve),
                       prueba(otro_monitor, no_resuelve)]).
caso_ejemplo(placa_base, [no_enciende, prueba(fuente_con_probador, ok),
                          pitidos(un_largo_tres_cortos)]).
caso_ejemplo(refrigeracion, [temp_cpu(97), ventilador_ruidoso]).
caso_ejemplo(memoria_ram, [pantalla_azul, prueba(reasentar_ram, resuelve)]).
caso_ejemplo(disco, [arranque_lento, ruido_clic,
                     prueba(smart_disco, falla)]).
caso_ejemplo(bateria_cmos, [hora_incorrecta, equipo(escritorio, 7)]).

%% -----------------------------------------------------------------------------
%%  A.15 Niveles discretos que produce el preprocesamiento numérico de Python
%%       (preprocesamiento.py) a partir de lecturas continuas. Llegan en la
%%       lista de entrada como dato(Variable, Nivel).
%% -----------------------------------------------------------------------------
catalogo_variables_discretas([
    temperatura_cpu-[normal, elevada, alta, critica],
    antiguedad-[nuevo, medio, antiguo],
    horas_uso-[bajo, moderado, intensivo],
    uso_disco-[normal, alto, critico]
]).

%% -----------------------------------------------------------------------------
%%  A.14 Reglas auxiliares para consultar los catálogos compactos.
%%       Estos accesores mantienen la interfaz usada por las reglas de R1-R25.
%% -----------------------------------------------------------------------------
sintoma_componente(Sintoma, Componente) :-
    relaciones_sintoma(Relaciones),
    member(Sintoma-Componente, Relaciones).

codigo_pitido(Patron, Componente) :-
    catalogo_pitidos(Codigos),
    member(Patron-Componente, Codigos).

prueba_catalogo(Nombre, Descripcion) :-
    catalogo_pruebas(Pruebas),
    member(Nombre-Descripcion, Pruebas).

resultado_prueba(Resultado, Descripcion) :-
    catalogo_resultados(Resultados),
    member(Resultado-Descripcion, Resultados).

tipo_equipo(Tipo, Descripcion) :-
    catalogo_tipos_equipo(Tipos),
    member(Tipo-Descripcion, Tipos).

gravedad(Diagnostico, Nivel) :-
    catalogo_gravedades(Gravedades),
    member(Diagnostico-Nivel, Gravedades).
gravedad(Diagnostico, Nivel) :-
    regla_aprendida(Diagnostico, _, _, _, _, _, Nivel, _).

nivel_danio(Diagnostico, leve) :-
    gravedad(Diagnostico, baja).
nivel_danio(Diagnostico, moderado) :-
    gravedad(Diagnostico, media).
nivel_danio(Diagnostico, grave) :-
    gravedad(Diagnostico, alta).

peso_gravedad(Nivel, Peso) :-
    catalogo_pesos(Pesos),
    member(Nivel-Peso, Pesos).

accion(Diagnostico, Accion) :-
    catalogo_acciones(Acciones),
    member(Diagnostico-Accion, Acciones).
accion(Diagnostico, Accion) :-
    regla_aprendida(Diagnostico, _, _, _, _, _, _, Accion).

evidencia_tipica(Diagnostico, Evidencia) :-
    catalogo_evidencia(Evidencias),
    member(Diagnostico-Evidencia, Evidencias).
evidencia_tipica(Diagnostico, Evidencia) :-
    regla_aprendida(Diagnostico, _, _, Evidencia, _, _, _, _).

nivel_discreto(Variable, Nivel) :-
    catalogo_variables_discretas(Variables),
    member(Variable-Niveles, Variables),
    member(Nivel, Niveles).


%% =============================================================================
%%  PARTE B. REGLAS DE INFERENCIA CON ENCADENAMIENTO (3.1)
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  NIVEL 1 – VALIDACIÓN PRELIMINAR
%%  Clasifican datos de entrada o verifican condiciones elementales.
%%  Solo consultan hechos base.
%% -----------------------------------------------------------------------------

% R1. El equipo no recibe energía: no enciende y no muestra ningún LED.
%     \+ se justifica porque "no hay LED" es ausencia de información: se
%     verifica por fallo. E ya está ligada por la meta anterior.
sin_energia(E) :-
    observado(E, no_enciende),
    \+ observado(E, led_encendido).

% R2. El equipo arranca (ventiladores giran) pero no entrega imagen.
sin_video(E) :-
    observado(E, pantalla_negra),
    observado(E, ventiladores_giran).

% R3. La temperatura medida del procesador supera el umbral permitido.
sobrecalentamiento(E) :-
    medicion(E, temp_cpu, T),
    umbral(temp_cpu_max_celsius, Max),
    T > Max.
% R3b. El clasificador numérico de Python ya discretizó la temperatura como
%      alta o crítica (mismos umbrales que A.8).
sobrecalentamiento(E) :-
    discreto(E, temperatura_cpu, Nivel),
    memberchk(Nivel, [alta, critica]).

% R4. Los pitidos de la BIOS apuntan a un componente determinado.
pitidos_error(E, Componente) :-
    pitidos(E, Patron),
    codigo_pitido(Patron, Componente).

% R5. El equipo muestra inestabilidad general (tres formas de manifestarse).
inestabilidad(E) :-
    observado(E, reinicios_aleatorios).
inestabilidad(E) :-
    observado(E, pantalla_azul).
inestabilidad(E) :-
    observado(E, bloqueos).

% R6. Un síntoma observado en el equipo se asocia a un componente.
sintoma_de(E, Componente) :-
    observado(E, Sintoma),
    sintoma_componente(Sintoma, Componente).

% R6b. Una lectura numérica discretizada también es un indicio sobre un
%      componente (no basta por sí sola para un diagnóstico).
indicio_discreto(E, procesador) :-
    discreto(E, temperatura_cpu, Nivel),
    memberchk(Nivel, [alta, critica]).
indicio_discreto(E, procesador) :-
    discreto(E, horas_uso, intensivo).
indicio_discreto(E, almacenamiento) :-
    discreto(E, uso_disco, critico).

% R7. El equipo supera la antigüedad crítica.
equipo_antiguo(E) :-
    equipo(E, _Tipo, Anios),
    umbral(antiguedad_critica_anios, Limite),
    Anios >= Limite.
% R7b. El clasificador numérico ya clasificó la antigüedad como 'antiguo'.
equipo_antiguo(E) :-
    discreto(E, antiguedad, antiguo).

% R8. Factor de riesgo inmediato: olor a quemado o temperatura crítica.
factor_riesgo(E) :-
    observado(E, olor_quemado).
factor_riesgo(E) :-
    medicion(E, temp_cpu, T),
    umbral(temp_cpu_critica_celsius, Critica),
    T >= Critica.
% R8b. Temperatura crítica según el clasificador numérico.
factor_riesgo(E) :-
    discreto(E, temperatura_cpu, critica).

%% -----------------------------------------------------------------------------
%%  NIVEL 2 – INFERENCIA INTERMEDIA
%%  Combinan reglas de nivel 1 con hechos para deducir estados intermedios.
%% -----------------------------------------------------------------------------

% R9. Falla de alimentación: sin energía y la fuente falla al probarla.
falla_energia(E) :-
    sin_energia(E),
    prueba(E, fuente_con_probador, falla).
% R9b. Sin energía y con olor a quemado, sin prueba de fuente que lo contradiga.
%      \+ evita que las dos cláusulas den la misma conclusión dos veces.
falla_energia(E) :-
    sin_energia(E),
    observado(E, olor_quemado),
    \+ prueba(E, fuente_con_probador, falla).

% R10. Falla externa de video: se corrige cambiando cable o monitor.
falla_cable_o_monitor(E) :-
    sin_video(E),
    prueba(E, cambio_cable, resuelve).
falla_cable_o_monitor(E) :-
    sin_video(E),
    prueba(E, otro_monitor, resuelve).

% R11. Falla interna de video: sin imagen y las pruebas externas no la corrigen.
%      once/1 basta con un síntoma de video: no importa cuántos haya.
falla_video_interno(E) :-
    sin_video(E),
    once(sintoma_de(E, tarjeta_video)),
    prueba(E, cambio_cable, no_resuelve),
    prueba(E, otro_monitor, no_resuelve).

% R12. Refrigeración deficiente: sobrecalentamiento con ventilador anómalo.
falla_refrigeracion(E) :-
    sobrecalentamiento(E),
    observado(E, ventilador_ruidoso).
falla_refrigeracion(E) :-
    sobrecalentamiento(E),
    observado(E, ventilador_detenido).

% R13. Memoria sospechosa: los pitidos la señalan, o hay inestabilidad
%      asociada a la RAM (y los pitidos no lo habían concluido ya).
memoria_sospechosa(E) :-
    pitidos_error(E, memoria_ram).
memoria_sospechosa(E) :-
    once(inestabilidad(E)),
    once(sintoma_de(E, memoria_ram)),
    \+ pitidos_error(E, memoria_ram).

% R14. Memoria mal asentada: sospechosa y reasentarla resuelve el problema.
memoria_mal_asentada(E) :-
    memoria_sospechosa(E),
    prueba(E, reasentar_ram, resuelve).

% R15. Memoria defectuosa: sospechosa y reasentarla no resuelve el problema.
memoria_defectuosa(E) :-
    memoria_sospechosa(E),
    prueba(E, reasentar_ram, no_resuelve).

% R16. Almacenamiento degradado: síntomas de disco y la prueba de estado detecta fallas.
almacenamiento_degradado(E) :-
    once(sintoma_de(E, almacenamiento)),
    prueba(E, smart_disco, falla).

% R17. Batería CMOS agotada: la hora se pierde en un equipo antiguo.
bateria_cmos_agotada(E) :-
    observado(E, hora_incorrecta),
    equipo_antiguo(E).

% R18. Diagnósticos DESCARTADOS por una prueba que los contradice.
%      Se usan con \+ en el nivel 3 (criterio de exclusión).
descartado(E, fuente_poder_defectuosa) :-
    prueba(E, fuente_con_probador, ok).
descartado(E, gpu_defectuosa) :-
    prueba(E, gpu_en_otro_equipo, ok).
descartado(E, disco_fallando) :-
    prueba(E, smart_disco, ok).
descartado(E, bateria_cmos_agotada) :-
    prueba(E, cambio_bateria, no_resuelve).

% R19. La placa base es sospechosa si no hay energía, la fuente pasó la prueba
%      y los pitidos de BIOS apuntan a la placa.
placa_base_sospechosa(E) :-
    sin_energia(E),
    prueba(E, fuente_con_probador, ok),
    pitidos_error(E, placa_base).

% R20. La combinación de señales de R19 permite diagnosticar la placa base.
placa_base_defectuosa(E) :-
    placa_base_sospechosa(E).

%% -----------------------------------------------------------------------------
%%  NIVEL 3 – CONCLUSIÓN FINAL
%%  Determinan el diagnóstico o la recomendación integrando las reglas
%%  intermedias.
%%  diagnostico(Equipo, Diagnostico, Certeza)         Certeza: alta | media
%%
%%  Cada cláusula exige la regla de nivel 2 y NO estar descartada (\+). E y el
%%  diagnóstico ya están ligados cuando se evalúa \+ descartado/2.
%% -----------------------------------------------------------------------------

% R21. Diagnósticos (una cláusula por conclusión posible).
diagnostico(E, fuente_poder_defectuosa, alta) :-
    falla_energia(E),
    \+ descartado(E, fuente_poder_defectuosa).
diagnostico(E, cable_o_monitor_defectuoso, alta) :-
    falla_cable_o_monitor(E),
    \+ descartado(E, cable_o_monitor_defectuoso).
diagnostico(E, gpu_defectuosa, media) :-
    falla_video_interno(E),
    \+ descartado(E, gpu_defectuosa).
diagnostico(E, placa_base_defectuosa, alta) :-
    placa_base_defectuosa(E),
    \+ descartado(E, placa_base_defectuosa).
diagnostico(E, refrigeracion_deficiente, alta) :-
    falla_refrigeracion(E),
    \+ descartado(E, refrigeracion_deficiente).
diagnostico(E, ram_mal_asentada, alta) :-
    memoria_mal_asentada(E),
    \+ descartado(E, ram_mal_asentada).
diagnostico(E, ram_defectuosa, alta) :-
    memoria_defectuosa(E),
    \+ descartado(E, ram_defectuosa).
diagnostico(E, disco_fallando, alta) :-
    almacenamiento_degradado(E),
    \+ descartado(E, disco_fallando).
diagnostico(E, bateria_cmos_agotada, alta) :-
    bateria_cmos_agotada(E),
    \+ descartado(E, bateria_cmos_agotada).
% R26. Diagnósticos aprendidos en caliente desde el modo experto (parte H).
%      Cada regla_aprendida/8 lista las condiciones que deben cumplirse y las
%      que la excluyen. \+ se evalúa con E y las exclusiones ya instanciadas.
diagnostico(E, Diagnostico, Certeza) :-
    regla_aprendida(Diagnostico, _Nombre, _Componente, Requeridas, Excluyentes,
                    Certeza, _Gravedad, _Accion),
    cumple_condiciones(E, Requeridas),
    \+ ( member(Condicion, Excluyentes), condicion_caso(E, Condicion) ),
    \+ descartado(E, Diagnostico).

% R22. Recomendación: la acción asociada a cada diagnóstico del equipo.
recomendacion(E, Accion) :-
    diagnostico(E, Diagnostico, _Certeza),
    accion(Diagnostico, Accion).

% R23. Se debe escalar a un técnico si algún diagnóstico es de gravedad alta
%      o si su certeza es solo media.
requiere_tecnico(E) :-
    diagnostico(E, Diagnostico, _Certeza),
    gravedad(Diagnostico, alta).
requiere_tecnico(E) :-
    diagnostico(E, _Diagnostico, media).

% R24. Un diagnóstico de refrigeración con un factor de riesgo requiere atención
%      técnica, especialmente cuando la temperatura es crítica.
requiere_tecnico(E) :-
    diagnostico(E, refrigeracion_deficiente, _Certeza),
    factor_riesgo(E).

% R25. Caso sin conclusión: el equipo está registrado pero ninguna regla aplica.
sin_diagnostico(E) :-
    equipo(E, _Tipo, _Anios),
    \+ diagnostico(E, _Diagnostico, _Certeza).

% Auxiliares de R26: una condición de regla aprendida se comprueba contra el
% caso cargado. Las condiciones especiales reutilizan reglas de nivel 1.
% condicion_caso(+E, +Condicion)  (cláusulas excluyentes con corte)
condicion_caso(E, temp_cpu_alta)  :- !, once(sobrecalentamiento(E)).
condicion_caso(E, equipo_antiguo) :- !, once(equipo_antiguo(E)).
condicion_caso(E, pitidos(P))     :- !, pitidos(E, P).
condicion_caso(E, prueba(N, R))   :- !, prueba(E, N, R).
condicion_caso(E, Sintoma)        :- observado(E, Sintoma).

% cumple_condiciones(+E, +Condiciones): recursión por la cola de la lista.
cumple_condiciones(_, []).
cumple_condiciones(E, [Condicion|Resto]) :-
    condicion_caso(E, Condicion),
    cumple_condiciones(E, Resto).


%% =============================================================================
%%  PARTE C. PROCESAMIENTO DE LISTAS Y CONTROL DE FLUJO (3.2)
%%
%%  Python envía una LISTA de condiciones. Formatos aceptados:
%%      sintoma                     p. ej. no_enciende, pantalla_negra
%%      temp_cpu(Grados)            medición numérica
%%      pitidos(Patron)             patrón de pitidos de la BIOS
%%      prueba(Nombre, Resultado)   prueba simple realizada
%%      equipo(Tipo, Anios)         tipo y antigüedad del equipo
%%      dato(Variable, Nivel)       lectura discretizada por preprocesamiento.py
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  C.1 Clasificación y filtrado de la lista de entrada
%% -----------------------------------------------------------------------------

% clasificar_item(+Item, -Tipo)
% Las cláusulas son MUTUAMENTE EXCLUYENTES: el corte (!) confirma la primera
% que aplica y evita que el backtracking pruebe las demás. La última cláusula
% es el VALOR POR DEFECTO (fallback): todo lo no reconocido es 'desconocido'.
clasificar_item(Item, desconocido) :-
    \+ ground(Item), !.                      % variables sueltas no se aceptan
clasificar_item(temp_cpu(V), medicion) :-
    number(V), !.
clasificar_item(pitidos(P), pitidos) :-
    codigo_pitido(P, _), !.
clasificar_item(prueba(N, R), prueba) :-
    prueba_catalogo(N, _),
    resultado_prueba(R, _), !.
clasificar_item(equipo(T, A), equipo) :-
    tipo_equipo(T, _),
    integer(A), A >= 0, !.
clasificar_item(dato(V, N), discreto) :-
    nivel_discreto(V, N), !.
clasificar_item(ausente(S), ausencia) :-     % síntoma negado ("no huele a quemado")
    atom(S),
    sintoma_catalogo(S, _), !.
clasificar_item(S, sintoma) :-
    atom(S),
    sintoma_catalogo(S, _), !.
clasificar_item(_, desconocido).             % fallback por defecto

% validar_entrada(+Entrada, -Validos, -Descartados)
% Recorre la lista (recursión por la cola) separando elementos válidos de
% elementos no reconocidos.
validar_entrada([], [], []).
validar_entrada([Item|Resto], [Item|Validos], Descartados) :-
    clasificar_item(Item, Tipo),
    Tipo \== desconocido, !,                 % corte: cláusulas excluyentes
    validar_entrada(Resto, Validos, Descartados).
validar_entrada([Item|Resto], Validos, [Item|Descartados]) :-
    validar_entrada(Resto, Validos, Descartados).

%% -----------------------------------------------------------------------------
%%  C.2 Subconjuntos y conteo de condiciones cumplidas
%% -----------------------------------------------------------------------------

% evidencia_presente(+Condicion, +Lista)
% Dos condiciones especiales se evalúan contra los datos; el resto debe
% aparecer literalmente en la lista. Los cortes hacen excluyentes las cláusulas.
evidencia_presente(temp_cpu_alta, Lista) :-
    !,
    (   member(temp_cpu(V), Lista),
        umbral(temp_cpu_max_celsius, Max),
        V > Max
    ;   member(dato(temperatura_cpu, Nivel), Lista),
        memberchk(Nivel, [alta, critica])
    ), !.
evidencia_presente(equipo_antiguo, Lista) :-
    !,
    (   member(equipo(_, A), Lista),
        umbral(antiguedad_critica_anios, Limite),
        A >= Limite
    ;   memberchk(dato(antiguedad, antiguo), Lista)
    ), !.
evidencia_presente(Condicion, Lista) :-
    memberchk(Condicion, Lista).

% contiene_todos(+Requisitos, +Lista)
% Verdadero si la lista contiene TODOS los requisitos (subconjunto).
contiene_todos([], _).
contiene_todos([Req|Resto], Lista) :-
    evidencia_presente(Req, Lista),
    contiene_todos(Resto, Lista).

% contar_presentes(+Requisitos, +Lista, -N)
% Cuenta cuántos requisitos de la primera lista están presentes en la segunda.
contar_presentes([], _, 0).
contar_presentes([Req|Resto], Lista, N) :-
    evidencia_presente(Req, Lista), !,       % corte: presente -> suma 1
    contar_presentes(Resto, Lista, N0),
    N is N0 + 1.
contar_presentes([_|Resto], Lista, N) :-
    contar_presentes(Resto, Lista, N).

% contar_ocurrencias(+Elemento, +Lista, -N)
contar_ocurrencias(_, [], 0).
contar_ocurrencias(X, [X|Resto], N) :- !,
    contar_ocurrencias(X, Resto, N0),
    N is N0 + 1.
contar_ocurrencias(X, [_|Resto], N) :-
    contar_ocurrencias(X, Resto, N).

% cobertura(+Validos, +Diagnostico, -Porcentaje)
% Porcentaje (0-100) de la evidencia típica del diagnóstico que está presente.
cobertura(Validos, Diagnostico, 100) :-
    evidencia_tipica(Diagnostico, Evidencia),
    contiene_todos(Evidencia, Validos), !.   % corte: ya está completa
cobertura(Validos, Diagnostico, Porcentaje) :-
    evidencia_tipica(Diagnostico, Evidencia),
    contar_presentes(Evidencia, Validos, N),
    length(Evidencia, Total),
    Total > 0,
    Porcentaje is round(100 * N / Total).

%% -----------------------------------------------------------------------------
%%  C.3 Carga temporal de un caso a partir de la lista
%%      Reutiliza las reglas de la parte B sobre un caso identificado por Id.
%% -----------------------------------------------------------------------------

% cargar_caso(+Id, +Validos)
cargar_caso(Id, Validos) :-
    limpiar_caso(Id),
    cargar_items(Id, Validos),
    registrar_equipo_por_defecto(Id).

cargar_items(_, []).
cargar_items(Id, [Item|Resto]) :-
    cargar_item(Id, Item),
    cargar_items(Id, Resto).

% cargar_item(+Id, +Item): una cláusula por tipo de dato, excluyentes con (!).
cargar_item(Id, temp_cpu(V))    :- !, assertz(medicion(Id, temp_cpu, V)).
cargar_item(Id, pitidos(P))     :- !, assertz(pitidos(Id, P)).
cargar_item(Id, prueba(N, R))   :- !, assertz(prueba(Id, N, R)).
cargar_item(Id, equipo(T, A))   :- !, assertz(equipo(Id, T, A)).
cargar_item(Id, dato(V, N))     :- !, assertz(discreto(Id, V, N)).
% ausente(S) solo sirve para detectar contradicciones (parte I): no es evidencia.
cargar_item(_, ausente(_))      :- !.
cargar_item(Id, Sintoma)        :- assertz(observado(Id, Sintoma)).

% Si la lista no trae el equipo, se registra con tipo desconocido y 0 años.
% \+ equipo(Id,_,_): Id está instanciado, por lo que la negación es segura.
registrar_equipo_por_defecto(Id) :-
    \+ equipo(Id, _, _), !,
    assertz(equipo(Id, desconocido, 0)).
registrar_equipo_por_defecto(_).

% limpiar_caso(+Id)
limpiar_caso(Id) :-
    retractall(equipo(Id, _, _)),
    retractall(observado(Id, _)),
    retractall(medicion(Id, _, _)),
    retractall(pitidos(Id, _)),
    retractall(prueba(Id, _, _)),
    retractall(discreto(Id, _, _)).


%% =============================================================================
%%  PARTE D. RECOLECCIÓN Y SEVERIDAD (3.3)
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  D.1 Severidad y prioridad
%% -----------------------------------------------------------------------------

% severidad(+Id, +Diagnostico, -Nivel, -Peso)
% Reglas excluyentes ordenadas de la más específica a la más general.
% Un factor de riesgo eleva a 'critica' cualquier diagnóstico que no sea de
% gravedad baja. \== se evalúa con G ya instanciada por gravedad/2.
severidad(Id, Diagnostico, critica, Peso) :-
    factor_riesgo(Id),
    gravedad(Diagnostico, Gravedad),
    Gravedad \== baja, !,
    peso_gravedad(critica, Peso).
severidad(_, Diagnostico, Nivel, Peso) :-
    gravedad(Diagnostico, Nivel),
    peso_gravedad(Nivel, Peso), !.
severidad(_, _, media, 2).                   % fallback: severidad por defecto

% prioridad(+Peso, +Cobertura, -Prioridad)
% La severidad domina (centenas); la cobertura de evidencia desempata.
prioridad(Peso, Cobertura, Prioridad) :-
    Prioridad is Peso * 100 + Cobertura.

%% -----------------------------------------------------------------------------
%%  D.2 Recolección de todos los diagnósticos de un caso
%% -----------------------------------------------------------------------------

% diagnosticar_todos(+Entrada, -Estado, -Diagnosticos)
% Agrupa en UNA lista, sin duplicados y ordenada por prioridad, todos los
% diagnósticos del caso. Cada elemento es una lista:
%     [Diagnostico, Certeza, Severidad, NivelDanio, Prioridad, Cobertura, Accion]
% Estado: ok | datos_insuficientes | entrada_vacia | entrada_invalida
%         | entrada_contradictoria (parte I: se bloquea antes de inferir)
diagnosticar_todos(Entrada, entrada_invalida, []) :-
    \+ is_list(Entrada), !.
diagnosticar_todos([], entrada_vacia, []) :- !.
diagnosticar_todos(Entrada, Estado, Diagnosticos) :-
    validar_entrada(Entrada, Validos, _Descartados),
    (   detectar_contradicciones(Validos, [_|_])
    ->  Estado = entrada_contradictoria, Diagnosticos = []
    ;   evaluar_validos(Validos, Estado, Diagnosticos)
    ).

evaluar_validos([], entrada_invalida, []) :- !.
evaluar_validos(Validos, Estado, Diagnosticos) :-
    setup_call_cleanup(
        cargar_caso(caso_tmp, Validos),
        recolectar_diagnosticos(caso_tmp, Validos, Diagnosticos),
        limpiar_caso(caso_tmp)),
    estado_caso(Diagnosticos, Estado).

% estado_caso(+Diagnosticos, -Estado)  (cláusulas excluyentes con corte)
estado_caso([], datos_insuficientes) :- !.
estado_caso(_, ok).

% recolectar_diagnosticos(+Id, +Validos, -Ordenados)
recolectar_diagnosticos(Id, Validos, Ordenados) :-
    findall(D-C, diagnostico(Id, D, C), Crudos),
    sort(Crudos, Unicos),                    % sort/2 elimina duplicados
    findall(P-Fila,
            ( member(D-C, Unicos),
              fila_diagnostico(Id, Validos, D, C, P, Fila) ),
            Pares),
    sort(1, @>=, Pares, Descendente),        % mayor prioridad primero
    pairs_values(Descendente, Ordenados).

fila_diagnostico(Id, Validos, D, C, Prioridad,
                 [D, C, Sev, NivelDanio, Prioridad, Cob, Accion]) :-
    severidad(Id, D, Sev, Peso),
    nivel_danio(D, NivelDanio),
    cobertura(Validos, D, Cob),
    prioridad(Peso, Cob, Prioridad),
    accion(D, Accion).

%% -----------------------------------------------------------------------------
%%  D.3 Componentes sospechosos (útil cuando faltan datos)
%% -----------------------------------------------------------------------------

% componentes_sospechosos(+Entrada, -Sospechosos)
% Lista [[Componente, Cantidad], ...] ordenada de mayor a menor cantidad de
% indicios (síntomas y pitidos que apuntan a ese componente).
componentes_sospechosos(Entrada, []) :-
    \+ is_list(Entrada), !.
componentes_sospechosos(Entrada, Sospechosos) :-
    validar_entrada(Entrada, Validos, _),
    setup_call_cleanup(
        cargar_caso(caso_tmp, Validos),
        recolectar_sospechas(caso_tmp, Sospechosos),
        limpiar_caso(caso_tmp)).

recolectar_sospechas(Id, Sospechosos) :-
    findall(C, ( sintoma_de(Id, C)
               ; pitidos_error(Id, C)
               ; indicio_discreto(Id, C) ), Todos),
    sort(Todos, Unicos),
    findall(N-C, ( member(C, Unicos), contar_ocurrencias(C, Todos, N) ), Pares),
    sort(0, @>=, Pares, Descendente),
    findall([C, N], member(N-C, Descendente), Sospechosos).


%% =============================================================================
%%  PARTE E. INTERFAZ PARA PYTHON
%%  Python solo invoca estos predicados y presenta lo que devuelven.
%% =============================================================================

% consultar_caso(+Entrada, -Respuesta)
% Respuesta = [Estado, Diagnosticos, Sospechosos, Descartados]
consultar_caso(Entrada, [Estado, Diagnosticos, Sospechosos, Descartados]) :-
    diagnosticar_todos(Entrada, Estado, Diagnosticos),
    (   Estado == entrada_contradictoria
    ->  Sospechosos = []                     % no se sospecha sobre datos incoherentes
    ;   componentes_sospechosos(Entrada, Sospechosos)
    ),
    descartados_como_texto(Entrada, Descartados).

% descartados_como_texto(+Entrada, -ListaDeAtomos)
descartados_como_texto(Entrada, []) :-
    \+ is_list(Entrada), !.
descartados_como_texto(Entrada, Textos) :-
    validar_entrada(Entrada, _Validos, Descartados),
    findall(Texto,
            ( member(Item, Descartados), format(atom(Texto), '~w', [Item]) ),
            Textos).

% consultar_texto(+Texto, -Respuesta)
% Igual que consultar_caso/2. Acepta la sintaxis formal separada por comas
% ('no_enciende, olor_quemado, temp_cpu(90)') o una oración en español, que
% se analiza con la DCG de la parte G ('mi pc no prende y huele a quemado').
consultar_texto(Texto, Respuesta) :-
    texto_a_lista(Texto, Lista), !,
    consultar_caso(Lista, Respuesta).
consultar_texto(Texto, Respuesta) :-
    parsear_oracion(Texto, Hechos, _NoReconocidas),
    Hechos \== [], !,
    consultar_caso(Hechos, Respuesta).
consultar_texto(_, [entrada_invalida, [], [], []]).   % fallback: sin datos válidos

% texto_a_lista(+Texto, -Lista): lee la sintaxis formal como lista Prolog.
texto_a_lista(Texto, Lista) :-
    atomic_list_concat(['[', Texto, ']'], Atomo),
    catch(term_to_atom(Lista, Atomo), _, fail),
    is_list(Lista).

% listar_sintomas(-Lista)  ->  [[Sintoma, Descripcion], ...]
listar_sintomas(Lista) :-
    findall([S, D], sintoma_catalogo(S, D), Lista).

%% -----------------------------------------------------------------------------
%%  F. EXPLICABILIDAD Y DATOS FALTANTES
%%  Las trazas solo se producen después de que diagnostico/3 tuvo éxito. Cada
%%  ruta vuelve a comprobar las reglas intermedias que justifican el diagnóstico.
%% -----------------------------------------------------------------------------

% analizar_caso(+Entrada, -Reporte)
% Reporte = [Estado, Diagnosticos, Sospechosos, Descartados,
%            Explicaciones, Sugerencias]
analizar_caso(Entrada, [entrada_invalida, [], [], [], [], []]) :-
    \+ is_list(Entrada), !.
analizar_caso([], [entrada_vacia, [], [], [], [], Sugerencias]) :-
    !,
    sugerencia_entrada_vacia(Sugerencias).
analizar_caso(Entrada, [entrada_contradictoria, [], [], DescartadosTexto, [], []]) :-
    validar_entrada(Entrada, Validos, Descartados),
    detectar_contradicciones(Validos, [_|_]), !,   % parte I: bloquea el diagnóstico
    atomizar_descartados(Descartados, DescartadosTexto).
analizar_caso(Entrada, Reporte) :-
    validar_entrada(Entrada, Validos, Descartados),
    setup_call_cleanup(
        cargar_caso(caso_tmp, Validos),
        reporte_cargado(caso_tmp, Validos, Descartados, Reporte),
        limpiar_caso(caso_tmp)).

reporte_cargado(Id, Validos, Descartados,
                [Estado, Diagnosticos, Sospechosos, DescartadosTexto,
                 Explicaciones, Sugerencias]) :-
    ( Validos = []
    -> Estado = entrada_invalida,
       Diagnosticos = [],
       Sospechosos = [],
       Explicaciones = [],
       Sugerencias = []
    ; recolectar_diagnosticos(Id, Validos, Diagnosticos),
      estado_caso(Diagnosticos, Estado),
      recolectar_sospechas(Id, Sospechosos),
      ( Diagnosticos = []
      -> explicacion_sin_diagnostico(Id, Validos, Explicaciones),
         sugerencias_faltantes(Id, Validos, Sugerencias)
      ; explicar_diagnosticos(Id, Validos, Diagnosticos, Explicaciones),
        sugerencias_para_hipotesis(Id, Validos, Diagnosticos, Sugerencias)
      )
    ),
    atomizar_descartados(Descartados, DescartadosTexto).

atomizar_descartados(Items, Textos) :-
    findall(Texto,
            ( member(Item, Items), format(atom(Texto), '~w', [Item]) ),
            Textos).

explicar_diagnosticos(_, _, [], []).
explicar_diagnosticos(Id, Validos,
                      [[D, C, Sev, NivelDanio, Prioridad, Cob, Accion]|Resto],
                      [[D, C, Sev, NivelDanio, Prioridad, Cob, Accion,
                        Reglas, Hechos, Negaciones, Alternativas]|Explicaciones]) :-
    traza_diagnostico(Id, D, Reglas),
    hechos_comprobados(Id, Reglas, Hechos),
    negaciones_comprobadas(Id, D, Reglas, Negaciones),
    alternativas_descartadas(Id, Alternativas),
    explicar_diagnosticos(Id, Validos, Resto, Explicaciones).

traza_diagnostico(Id, fuente_poder_defectuosa, Reglas) :-
    sin_energia(Id),
    falla_energia(Id),
    ( prueba(Id, fuente_con_probador, falla)
    -> Reglas = ['R1', 'R9', 'R21']
    ; Reglas = ['R1', 'R9b', 'R21']
    ).
traza_diagnostico(Id, cable_o_monitor_defectuoso, ['R2', 'R10', 'R21']) :-
    falla_cable_o_monitor(Id).
traza_diagnostico(Id, gpu_defectuosa, ['R2', 'R6', 'R11', 'R21']) :-
    falla_video_interno(Id).
traza_diagnostico(Id, placa_base_defectuosa,
                  ['R1', 'R4', 'R19', 'R20', 'R21']) :-
    placa_base_defectuosa(Id).
traza_diagnostico(Id, refrigeracion_deficiente, Reglas) :-
    once(falla_refrigeracion(Id)),
    regla_temperatura(Id, ReglaTemperatura),
    ( factor_riesgo(Id)
    -> Reglas = [ReglaTemperatura, 'R8', 'R12', 'R21']
    ; Reglas = [ReglaTemperatura, 'R12', 'R21']
    ).
traza_diagnostico(Id, ram_mal_asentada, Reglas) :-
    memoria_mal_asentada(Id),
    traza_memoria(Id, Reglas, ['R14', 'R21']).
traza_diagnostico(Id, ram_defectuosa, Reglas) :-
    memoria_defectuosa(Id),
    traza_memoria(Id, Reglas, ['R15', 'R21']).
traza_diagnostico(Id, disco_fallando, ['R6', 'R16', 'R21']) :-
    almacenamiento_degradado(Id).
traza_diagnostico(Id, bateria_cmos_agotada, [ReglaAntiguedad, 'R17', 'R21']) :-
    once(bateria_cmos_agotada(Id)),
    regla_antiguedad(Id, ReglaAntiguedad).
traza_diagnostico(Id, Diagnostico, ['R26']) :-
    regla_aprendida(Diagnostico, _, _, Requeridas, _, _, _, _),
    cumple_condiciones(Id, Requeridas).

% La medición directa (R3, R7) tiene prioridad sobre el dato discretizado
% por el clasificador numérico (R3b, R7b).
regla_temperatura(Id, 'R3') :-
    medicion(Id, temp_cpu, T),
    umbral(temp_cpu_max_celsius, Max),
    T > Max, !.
regla_temperatura(_, 'R3b').

regla_antiguedad(Id, 'R7') :-
    equipo(Id, _, Anios),
    umbral(antiguedad_critica_anios, Limite),
    Anios >= Limite, !.
regla_antiguedad(_, 'R7b').

traza_memoria(Id, Reglas, ReglasFinales) :-
    ( pitidos_error(Id, memoria_ram)
    -> Reglas = ['R4', 'R13'|ReglasFinales]
    ; inestabilidad(Id),
      sintoma_de(Id, memoria_ram),
      \+ pitidos_error(Id, memoria_ram),
      Reglas = ['R5', 'R6', 'R13'|ReglasFinales]
    ).

hechos_comprobados(Id, Reglas, Hechos) :-
    findall(Texto, hecho_observado(Id, Texto), Observados),
    findall(Texto, hecho_medicion(Id, Texto), Mediciones),
    findall(Texto, hecho_pitido(Id, Texto), Pitidos),
    findall(Texto, hecho_prueba(Id, Texto), Pruebas),
    findall(Texto, hecho_equipo(Id, Texto), Equipos),
    findall(Texto, hecho_discreto(Id, Texto), Discretos),
    findall(Texto,
            ( member(Regla, ['R6', 'R11', 'R13', 'R16']),
              memberchk(Regla, Reglas),
              hecho_asociacion_sintoma(Id, Texto)
            ),
            Asociaciones),
    findall(Texto,
            ( memberchk('R4', Reglas), hecho_asociacion_pitido(Id, Texto) ),
            Codigos),
    findall(Texto, umbral_traza(Reglas, Id, Texto), Umbrales),
    append([Observados, Mediciones, Pitidos, Pruebas, Equipos, Discretos,
            Asociaciones, Codigos, Umbrales], Hechos).

hecho_observado(Id, Texto) :-
    observado(Id, Sintoma),
    format(atom(Texto), 'observado(~w)', [Sintoma]).
hecho_medicion(Id, Texto) :-
    medicion(Id, temp_cpu, Valor),
    format(atom(Texto), 'temp_cpu(~w °C)', [Valor]).
hecho_pitido(Id, Texto) :-
    pitidos(Id, Patron),
    format(atom(Texto), 'pitidos(~w)', [Patron]).
hecho_prueba(Id, Texto) :-
    prueba(Id, Nombre, Resultado),
    format(atom(Texto), 'prueba(~w, ~w)', [Nombre, Resultado]).
hecho_equipo(Id, Texto) :-
    equipo(Id, Tipo, Anios),
    ( Tipo \== desconocido ; Anios > 0 ),
    format(atom(Texto), 'equipo(~w, ~w años)', [Tipo, Anios]).
hecho_discreto(Id, Texto) :-
    discreto(Id, Variable, Nivel),
    format(atom(Texto), 'dato(~w, ~w)', [Variable, Nivel]).
hecho_asociacion_sintoma(Id, Texto) :-
    observado(Id, Sintoma),
    sintoma_componente(Sintoma, Componente),
    format(atom(Texto), 'sintoma_componente(~w, ~w)', [Sintoma, Componente]).
hecho_asociacion_pitido(Id, Texto) :-
    pitidos(Id, Patron),
    codigo_pitido(Patron, Componente),
    format(atom(Texto), 'codigo_pitido(~w, ~w)', [Patron, Componente]).
umbral_traza(Reglas, Id, Texto) :-
    memberchk('R3', Reglas),
    medicion(Id, temp_cpu, _),
    umbral(temp_cpu_max_celsius, Umbral),
    format(atom(Texto), 'umbral(temp_cpu_max_celsius, ~w)', [Umbral]).
umbral_traza(Reglas, Id, Texto) :-
    memberchk('R7', Reglas),
    equipo(Id, _, Anios),
    Anios > 0,
    umbral(antiguedad_critica_anios, Umbral),
    format(atom(Texto), 'umbral(antiguedad_critica_anios, ~w)', [Umbral]).

negaciones_comprobadas(Id, Diagnostico, Reglas, Negaciones) :-
    findall(Texto, negacion_traza(Id, Diagnostico, Reglas, Texto), Negaciones).

negacion_traza(Id, Diagnostico, Reglas, Texto) :-
    memberchk('R21', Reglas),
    \+ descartado(Id, Diagnostico),
    format(atom(Texto),
           'R21: \\+ descartado(~w) tuvo éxito; no se encontró una prueba contradictoria.',
           [Diagnostico]).
negacion_traza(Id, _, Reglas, Texto) :-
    memberchk('R1', Reglas),
    \+ observado(Id, led_encendido),
    format(atom(Texto),
           'R1: \\+ observado(led_encendido) tuvo éxito; no se reportó un LED encendido.',
           []).
negacion_traza(Id, fuente_poder_defectuosa, Reglas, Texto) :-
    memberchk('R9b', Reglas),
    \+ prueba(Id, fuente_con_probador, falla),
    format(atom(Texto),
           'R9b: \\+ prueba(fuente_con_probador, falla) tuvo éxito.',
           []).
negacion_traza(Id, ram_defectuosa, Reglas, Texto) :-
    memberchk('R13', Reglas),
    \+ pitidos_error(Id, memoria_ram),
    format(atom(Texto),
           'R13: \\+ pitidos_error(memoria_ram) tuvo éxito; la sospecha provino de inestabilidad y síntomas de RAM.',
           []).
negacion_traza(Id, ram_mal_asentada, Reglas, Texto) :-
    memberchk('R13', Reglas),
    \+ pitidos_error(Id, memoria_ram),
    format(atom(Texto),
           'R13: \\+ pitidos_error(memoria_ram) tuvo éxito; la sospecha provino de inestabilidad y síntomas de RAM.',
           []).
negacion_traza(Id, Diagnostico, Reglas, Texto) :-
    memberchk('R26', Reglas),
    \+ descartado(Id, Diagnostico),
    format(atom(Texto),
           'R26: \\+ descartado(~w) tuvo éxito; no se encontró una prueba contradictoria.',
           [Diagnostico]).
negacion_traza(Id, Diagnostico, Reglas, Texto) :-
    memberchk('R26', Reglas),
    regla_aprendida(Diagnostico, _, _, _, Excluyentes, _, _, _),
    member(Condicion, Excluyentes),
    \+ condicion_caso(Id, Condicion),
    format(atom(Texto),
           'R26: \\+ ~w tuvo éxito; no está presente la condición que excluye la regla.',
           [Condicion]).

alternativas_descartadas(Id, Alternativas) :-
    findall(Texto,
            ( descartado(Id, Diagnostico),
              prueba(Id, Nombre, Resultado),
              razon_descartado(Diagnostico, Nombre, Resultado, Razon),
              format(atom(Texto), '~w: ~w', [Diagnostico, Razon])
            ),
            Alternativas).

razon_descartado(fuente_poder_defectuosa, fuente_con_probador, ok,
                 'la prueba del probador indicó que la fuente pasó').
razon_descartado(gpu_defectuosa, gpu_en_otro_equipo, ok,
                 'la tarjeta gráfica funcionó en otro equipo').
razon_descartado(disco_fallando, smart_disco, ok,
                 'la revisión del estado del disco no detectó una falla').
razon_descartado(bateria_cmos_agotada, cambio_bateria, no_resuelve,
                 'cambiar la batería no resolvió el problema').

explicacion_sin_diagnostico(Id, Validos,
    [[sin_diagnostico, '', '', '', 0, 0, '', ['R25'], Hechos, [Negacion], []]]) :-
    sin_diagnostico(Id),
    hechos_comprobados(Id, ['R25'], Hechos),
    format(atom(Negacion),
           'R25: \\+ diagnostico(~w, _, _) tuvo éxito; ninguna conclusión final se derivó.',
           [Id]),
    Validos = [_|_].

sugerencias_faltantes(Id, Validos, Sugerencias) :-
    findall(D,
            ( candidato_diagnostico(Id, Validos, D),
              \+ diagnostico(Id, D, _),
              \+ descartado(Id, D)
            ),
            CandidatosDuplicados),
    sort(CandidatosDuplicados, Candidatos),
    ( Candidatos = []
    -> sugerencias_generales(Validos, Sugerencias)
    ; construir_sugerencias(Candidatos, Validos, Sugerencias)
    ).

sugerencias_para_hipotesis(Id, Validos, Diagnosticos, Sugerencias) :-
    ( Diagnosticos = [_,_|_]
    -> findall(D,
               ( candidato_diagnostico(Id, Validos, D),
                 \+ descartado(Id, D)
               ),
               CandidatosDuplicados),
       sort(CandidatosDuplicados, Candidatos),
       construir_sugerencias(Candidatos, Validos, Sugerencias)
    ; Sugerencias = []
    ).

candidato_diagnostico(Id, Validos, Diagnostico) :-
    componente_diagnostico(Diagnostico, Componente),
    sintoma_de(Id, Componente),
    Validos \= [].
candidato_diagnostico(_, Validos, Diagnostico) :-
    evidencia_tipica(Diagnostico, Evidencias),
    member(Evidencia, Evidencias),
    evidencia_presente(Evidencia, Validos).

componente_diagnostico(fuente_poder_defectuosa, fuente_poder).
componente_diagnostico(cable_o_monitor_defectuoso, tarjeta_video).
componente_diagnostico(gpu_defectuosa, tarjeta_video).
componente_diagnostico(placa_base_defectuosa, placa_base).
componente_diagnostico(refrigeracion_deficiente, procesador).
componente_diagnostico(ram_mal_asentada, memoria_ram).
componente_diagnostico(ram_defectuosa, memoria_ram).
componente_diagnostico(disco_fallando, almacenamiento).
componente_diagnostico(bateria_cmos_agotada, placa_base).
componente_diagnostico(Diagnostico, Componente) :-
    regla_aprendida(Diagnostico, _, Componente, _, _, _, _, _).

construir_sugerencias([], _, []).
construir_sugerencias(Candidatos, Validos, Sugerencias) :-
    findall(Clave, (member(D, Candidatos), dato_recomendado(D, Clave, _, _, _),
                    \+ dato_ya_informado(Clave, Validos)), ClavesDuplicadas),
    sort(ClavesDuplicadas, Claves),
    findall(Prioridad-[Descripcion, Razon, Hipotesis],
            ( member(Clave, Claves),
              findall(D, (member(D, Candidatos),
                          dato_recomendado(D, Clave, _, _, _)), Hipotesis),
              once(( member(Dato, Hipotesis),
                     dato_recomendado(Dato, Clave, Descripcion, Razon, Base) )),
              length(Hipotesis, Cantidad),
              Prioridad is Base + Cantidad * 10
            ),
            Pares),
    sort(1, @>=, Pares, Ordenadas),
    tomar_sugerencias(Ordenadas, 5, Sugerencias).

tomar_sugerencias([], _, []).
tomar_sugerencias(_, 0, []) :- !.
tomar_sugerencias([_-Sugerencia|Resto], N, [Sugerencia|Sugerencias]) :-
    N > 0,
    N1 is N - 1,
    tomar_sugerencias(Resto, N1, Sugerencias).

dato_ya_informado(cambio_cable, Validos) :-
    member(prueba(cambio_cable, _), Validos).
dato_ya_informado(otro_monitor, Validos) :-
    member(prueba(otro_monitor, _), Validos).
dato_ya_informado(fuente_con_probador, Validos) :-
    member(prueba(fuente_con_probador, _), Validos).
dato_ya_informado(gpu_en_otro_equipo, Validos) :-
    member(prueba(gpu_en_otro_equipo, _), Validos).
dato_ya_informado(reasentar_ram, Validos) :-
    member(prueba(reasentar_ram, _), Validos).
dato_ya_informado(smart_disco, Validos) :-
    member(prueba(smart_disco, _), Validos).
dato_ya_informado(cambio_bateria, Validos) :-
    member(prueba(cambio_bateria, _), Validos).
dato_ya_informado(temperatura, Validos) :-
    member(temp_cpu(_), Validos).
dato_ya_informado(temperatura, Validos) :-
    member(dato(temperatura_cpu, _), Validos).
dato_ya_informado(patron_pitidos, Validos) :-
    member(pitidos(_), Validos).
dato_ya_informado(antiguedad, Validos) :-
    member(equipo(_, _), Validos).
dato_ya_informado(antiguedad, Validos) :-
    member(dato(antiguedad, _), Validos).
dato_ya_informado(Sintoma, Validos) :-
    sintoma_catalogo(Sintoma, _),
    memberchk(Sintoma, Validos).

dato_recomendado(cable_o_monitor_defectuoso, cambio_cable,
    'Prueba: cambia el cable de video y registra si resuelve el problema.',
    'R10 utiliza esta prueba para confirmar una falla externa; si no resuelve, ayuda a diferenciarla de una falla interna de video.',
    100).
dato_recomendado(gpu_defectuosa, cambio_cable,
    'Prueba: cambia el cable de video y registra si resuelve el problema.',
    'R10 y R11 distinguen entre una falla externa y una posible falla interna de video.',
    100).
dato_recomendado(gpu_defectuosa, otro_monitor,
    'Prueba: conecta otro monitor y registra el resultado.',
    'R11 requiere que el cambio de monitor tampoco resuelva la falta de imagen.',
    75).
dato_recomendado(fuente_poder_defectuosa, fuente_con_probador,
    'Prueba: revisa la fuente con un probador y registra si falla o pasa.',
    'R9 evalúa la falla de la fuente; si pasa la prueba, evita ese diagnóstico.',
    95).
dato_recomendado(placa_base_defectuosa, fuente_con_probador,
    'Prueba: revisa la fuente con un probador y registra si falla o pasa.',
    'R19 solo considera la placa base en esta ruta cuando la fuente pasó la prueba.',
    95).
dato_recomendado(placa_base_defectuosa, patron_pitidos,
    'Dato: indica el patrón de pitidos al encender, si lo escuchas.',
    'R4 y R19 relacionan el código de pitidos con una posible falla de placa base.',
    80).
dato_recomendado(ram_mal_asentada, reasentar_ram,
    'Prueba: vuelve a colocar la RAM y registra si el problema se resuelve.',
    'R14 y R15 distinguen una RAM mal asentada de una RAM posiblemente defectuosa.',
    95).
dato_recomendado(ram_defectuosa, reasentar_ram,
    'Prueba: vuelve a colocar la RAM y registra si el problema se resuelve.',
    'R14 y R15 distinguen una RAM mal asentada de una RAM posiblemente defectuosa.',
    95).
dato_recomendado(disco_fallando, smart_disco,
    'Prueba: consulta el estado de salud del disco y registra si indica una falla.',
    'R16 usa el resultado de la revisión del disco junto con síntomas de almacenamiento.',
    95).
dato_recomendado(refrigeracion_deficiente, temperatura,
    'Dato: proporciona la temperatura del procesador en °C, si puedes consultarla.',
    'R3 y R12 necesitan comprobar sobrecalentamiento y una anomalía de ventilación.',
    85).
dato_recomendado(refrigeracion_deficiente, ventilador,
    'Dato: indica si el ventilador hace ruido o dejó de girar.',
    'R12 combina sobrecalentamiento con un ventilador ruidoso o detenido.',
    80).
dato_recomendado(bateria_cmos_agotada, antiguedad,
    'Dato: indica el tipo y la antigüedad aproximada del equipo.',
    'R7 y R17 necesitan comprobar que el equipo alcanzó el umbral de antigüedad.',
    75).
% Reglas aprendidas: cada condición requerida es un dato que conviene pedir.
dato_recomendado(Diagnostico, Clave, Descripcion, Razon, 70) :-
    regla_aprendida(Diagnostico, Nombre, _, Requeridas, _, _, _, _),
    member(Condicion, Requeridas),
    clave_condicion(Condicion, Clave, Descripcion),
    format(atom(Razon),
           'R26: la regla aprendida «~w» necesita comprobar esta condición.',
           [Nombre]).

% clave_condicion(+Condicion, -Clave, -Descripcion)  (excluyentes con corte)
clave_condicion(temp_cpu_alta, temperatura,
    'Dato: proporciona la temperatura del procesador en °C, si puedes consultarla.') :- !.
clave_condicion(equipo_antiguo, antiguedad,
    'Dato: indica el tipo y la antigüedad aproximada del equipo.') :- !.
clave_condicion(pitidos(_), patron_pitidos,
    'Dato: indica el patrón de pitidos al encender, si lo escuchas.') :- !.
clave_condicion(prueba(Nombre, _), Nombre, Descripcion) :- !,
    prueba_catalogo(Nombre, Texto),
    format(atom(Descripcion), 'Prueba: «~w»; registra el resultado.', [Texto]).
clave_condicion(Sintoma, Sintoma, Descripcion) :-
    sintoma_catalogo(Sintoma, Texto),
    format(atom(Descripcion), 'Síntoma: confirma si ocurre esto: «~w».', [Texto]).

sugerencias_generales(Validos, [[Descripcion, Razon, []]]) :-
    memberchk(led_encendido, Validos), !,
    Descripcion = 'Añade cualquier otro síntoma observable del catálogo.',
    Razon = 'R6 relaciona síntomas observados con componentes; el LED por sí solo no identifica una causa en las reglas actuales.'.
sugerencias_generales(_, [[Descripcion, Razon, []]]) :-
    Descripcion = 'Selecciona uno o más síntomas observables del catálogo.',
    Razon = 'La base de conocimiento necesita síntomas u otros datos de entrada para evaluar sus reglas de diagnóstico.'.

sugerencia_entrada_vacia([[Descripcion, Razon, []]]) :-
    Descripcion = 'Selecciona al menos un síntoma observable para iniciar el diagnóstico.',
    Razon = 'Sin condiciones de entrada, Prolog no puede comprobar ninguna regla de diagnóstico.'.


%% =============================================================================
%%  PARTE I. CONSISTENCIA DE LOS HECHOS (Entregable 4)
%%
%%  Antes de inferir, el sistema comprueba que los hechos del caso no se
%%  contradigan según el dominio (p. ej. "no enciende" y "los ventiladores
%%  giran"). Si hay alguna contradicción, diagnosticar_todos/3 y analizar_caso/2
%%  responden con el estado 'entrada_contradictoria' y NO emiten diagnóstico:
%%  es preferible pedir una aclaración que concluir sobre datos incompatibles.
%%
%%  Cada contradicción es una lista [Tipo, Elementos, Motivo] (átomos):
%%     sintomas_incompatibles   dos hechos que no pueden darse a la vez
%%     afirmado_y_negado        un síntoma reportado y negado ("no huele a quemado")
%%     lectura_imposible        temperatura fuera del rango físico plausible
%%     lecturas_discrepantes    dos temperaturas muy distintas en el mismo caso
%%     nivel_discordante        una lectura numérica y su nivel discreto no coinciden
%%     datos_duplicados         dos valores distintos para el mismo dato
%%                              (prueba, patrón de pitidos, equipo, nivel)
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  I.1 Conocimiento de incompatibilidades
%% -----------------------------------------------------------------------------

% Síntomas que solo puede presentar un equipo que recibe energía y arranca.
% (led_encendido no está: un LED de reserva sí puede verse sin que arranque.)
sintoma_requiere_energia(ventiladores_giran).
sintoma_requiere_energia(ventilador_ruidoso).
sintoma_requiere_energia(pitidos_arranque).
sintoma_requiere_energia(pantalla_azul).
sintoma_requiere_energia(lineas_en_pantalla).
sintoma_requiere_energia(artefactos_video).
sintoma_requiere_energia(lentitud).
sintoma_requiere_energia(arranque_lento).
sintoma_requiere_energia(bloqueos).
sintoma_requiere_energia(reinicios_aleatorios).
sintoma_requiere_energia(ruido_clic).

% limite_plausible(+Variable, -Minimo, -Maximo): rango físico razonable.
limite_plausible(temp_cpu, 10, 125).
% Diferencia máxima tolerada entre dos lecturas de temperatura del mismo caso.
tolerancia_lecturas(temp_cpu, 15).

% incompatible_dirigido(?A, ?B, -Motivo): A excluye a B. Se declara en un solo
% sentido; incompatible/3 lo hace simétrico.
incompatible_dirigido(no_enciende, S, Motivo) :-
    sintoma_requiere_energia(S),
    format(atom(Motivo),
           'Si el equipo no enciende no puede presentar «~w».', [S]).
incompatible_dirigido(pantalla_negra, S, Motivo) :-
    S = pantalla_azul,
    format(atom(Motivo),
           'Una pantalla en negro (sin imagen) no puede estar a la vez en «~w».', [S]).
incompatible_dirigido(ventilador_detenido, S, Motivo) :-
    memberchk(S, [ventiladores_giran, ventilador_ruidoso]),
    format(atom(Motivo),
           'Un ventilador detenido no puede cumplir a la vez «~w».', [S]).
incompatible_dirigido(disco_no_encontrado, prueba(smart_disco, _),
    'Si el disco no es detectado no se puede leer su estado de salud (SMART).').

incompatible(A, B, Motivo) :- incompatible_dirigido(A, B, Motivo).
incompatible(A, B, Motivo) :- incompatible_dirigido(B, A, Motivo).

% Nivel discreto que corresponde a una lectura numérica (mismos cortes que
% preprocesamiento.py: temperatura 70/86/95 °C, antigüedad 2/5 años).
nivel_temperatura(V, normal)  :- V < 70, !.
nivel_temperatura(V, elevada) :- V < 86, !.
nivel_temperatura(V, alta)    :- V < 95, !.
nivel_temperatura(_, critica).

nivel_antiguedad(A, nuevo)   :- A < 2, !.
nivel_antiguedad(A, medio)   :- A < 5, !.
nivel_antiguedad(_, antiguo).

%% -----------------------------------------------------------------------------
%%  I.2 Detección de contradicciones
%% -----------------------------------------------------------------------------

% contradiccion(+Validos, -[Tipo, Elementos, Motivo])
contradiccion(Validos, [sintomas_incompatibles, Texto, Motivo]) :-
    member(A, Validos), member(B, Validos),
    A @< B,                                   % cada par se reporta una vez
    incompatible(A, B, Motivo),
    elementos_texto([A, B], Texto).
contradiccion(Validos, [afirmado_y_negado, Texto, Motivo]) :-
    member(ausente(S), Validos),
    memberchk(S, Validos),
    elementos_texto([S, ausente(S)], Texto),
    format(atom(Motivo),
           'Se reportó «~w» y a la vez se dijo que NO ocurre.', [S]).
contradiccion(Validos, [lectura_imposible, Texto, Motivo]) :-
    member(temp_cpu(V), Validos),
    limite_plausible(temp_cpu, Min, Max),
    ( V < Min ; V > Max ),
    elementos_texto([temp_cpu(V)], Texto),
    format(atom(Motivo),
           'Una temperatura de ~w °C está fuera del rango posible (~w a ~w °C).',
           [V, Min, Max]).
contradiccion(Validos, [lecturas_discrepantes, Texto, Motivo]) :-
    member(temp_cpu(V1), Validos), member(temp_cpu(V2), Validos),
    V1 < V2,
    tolerancia_lecturas(temp_cpu, Tol),
    V2 - V1 > Tol,
    elementos_texto([temp_cpu(V1), temp_cpu(V2)], Texto),
    format(atom(Motivo),
           'Dos lecturas de temperatura (~w y ~w °C) difieren en más de ~w grados.',
           [V1, V2, Tol]).
contradiccion(Validos, [nivel_discordante, Texto, Motivo]) :-
    member(temp_cpu(V), Validos),
    member(dato(temperatura_cpu, Nivel), Validos),
    nivel_temperatura(V, Esperado),
    Esperado \== Nivel,
    elementos_texto([temp_cpu(V), dato(temperatura_cpu, Nivel)], Texto),
    format(atom(Motivo),
           '~w °C corresponde al nivel «~w», no a «~w».', [V, Esperado, Nivel]).
contradiccion(Validos, [nivel_discordante, Texto, Motivo]) :-
    member(equipo(Tipo, A), Validos),
    member(dato(antiguedad, Nivel), Validos),
    nivel_antiguedad(A, Esperado),
    Esperado \== Nivel,
    elementos_texto([equipo(Tipo, A), dato(antiguedad, Nivel)], Texto),
    format(atom(Motivo),
           '~w años corresponde al nivel «~w», no a «~w».', [A, Esperado, Nivel]).
contradiccion(Validos, [datos_duplicados, Texto, Motivo]) :-
    member(prueba(N, R1), Validos), member(prueba(N, R2), Validos),
    R1 @< R2,
    elementos_texto([prueba(N, R1), prueba(N, R2)], Texto),
    format(atom(Motivo),
           'La prueba «~w» tiene dos resultados distintos (~w y ~w).', [N, R1, R2]).
contradiccion(Validos, [datos_duplicados, Texto, Motivo]) :-
    member(pitidos(P1), Validos), member(pitidos(P2), Validos),
    P1 @< P2,
    elementos_texto([pitidos(P1), pitidos(P2)], Texto),
    format(atom(Motivo),
           'Se informaron dos patrones de pitidos distintos (~w y ~w).', [P1, P2]).
contradiccion(Validos, [datos_duplicados, Texto, Motivo]) :-
    member(equipo(T1, A1), Validos), member(equipo(T2, A2), Validos),
    equipo(T1, A1) @< equipo(T2, A2),
    elementos_texto([equipo(T1, A1), equipo(T2, A2)], Texto),
    Motivo = 'Se informaron dos equipos distintos (tipo o antigüedad) en el mismo caso.'.
contradiccion(Validos, [datos_duplicados, Texto, Motivo]) :-
    member(dato(V, N1), Validos), member(dato(V, N2), Validos),
    N1 @< N2,
    elementos_texto([dato(V, N1), dato(V, N2)], Texto),
    format(atom(Motivo),
           'La variable «~w» tiene dos niveles distintos (~w y ~w).', [V, N1, N2]).

elementos_texto(Elementos, Texto) :-
    maplist([E, A]>>format(atom(A), '~w', [E]), Elementos, Atomos),
    atomic_list_concat(Atomos, ' + ', Texto).

% detectar_contradicciones(+Validos, -Contradicciones)
% Sin duplicados y en orden estable. Lista vacía = el caso es consistente.
detectar_contradicciones(Validos, Contradicciones) :-
    findall(C, contradiccion(Validos, C), Crudas),
    list_to_set(Crudas, Contradicciones).

% contradicciones_caso(+Entrada, -Contradicciones)
% Interfaz para Python: filtra la entrada y la revisa.
contradicciones_caso(Entrada, []) :-
    \+ is_list(Entrada), !.
contradicciones_caso(Entrada, Contradicciones) :-
    validar_entrada(Entrada, Validos, _),
    detectar_contradicciones(Validos, Contradicciones).


%% =============================================================================
%%  PARTE G. LENGUAJE NATURAL: GRAMÁTICA DE CLÁUSULAS DEFINIDAS (DCG)
%%
%%  Python envía la oración tal como la escribió el usuario. Prolog:
%%    1. la normaliza (minúsculas, sin tildes ni signos) y la divide en
%%       palabras con tokenizar/2;
%%    2. la analiza con la DCG oracion//1: una oración es una secuencia de
%%       sintagmas (síntomas, mediciones, pitidos y datos del equipo) unidos
%%       por conectores y acompañados de palabras de relleno;
%%    3. devuelve los hechos simbólicos y las palabras que no reconoció.
%%
%%  Ejemplo:
%%    ?- parsear_oracion('Mi PC no prende y huele a quemado', Hechos, NoRec).
%%    Hechos = [no_enciende, olor_quemado], NoRec = [].
%% =============================================================================

%% -----------------------------------------------------------------------------
%%  G.1 Normalización y tokenización
%% -----------------------------------------------------------------------------

% tokenizar(+Texto, -Palabras)
% Las comas, puntos y puntos y coma se conservan como el token ',' porque
% separan sintagmas; el resto de signos se convierte en espacios.
tokenizar(Texto, Palabras) :-
    text_to_string(Texto, Cadena),
    string_lower(Cadena, Minusculas),
    string_codes(Minusculas, Codigos),
    maplist(codigo_normalizado, Codigos, Partes),
    append(Partes, Normalizados),
    string_codes(Limpia, Normalizados),
    split_string(Limpia, " ", " ", Trozos),
    exclude(==(""), Trozos, Validos),
    maplist(atom_string, Palabras, Validos).

% codigo_normalizado(+Codigo, -Codigos)  (cláusulas excluyentes con corte)
codigo_normalizado(C, [C]) :- between(0'a, 0'z, C), !.
codigo_normalizado(C, [C]) :- between(0'0, 0'9, C), !.
codigo_normalizado(C, [B]) :- letra_con_tilde(C, B), !.
codigo_normalizado(C, Codigos) :-
    memberchk(C, [0'°, 0'º]), !,
    string_codes(" grados ", Codigos).
codigo_normalizado(C, Codigos) :-
    string_codes(",;.:", Separadores),
    memberchk(C, Separadores), !,
    string_codes(" , ", Codigos).
codigo_normalizado(_, [0'\s]).                 % cualquier otro signo: espacio

letra_con_tilde(C, B) :-
    member(Base-Variantes, [0'a-"áàäâ", 0'e-"éèëê", 0'i-"íìïî",
                            0'o-"óòöô", 0'u-"úùüû", 0'n-"ñ", 0'c-"ç"]),
    string_codes(Variantes, Codigos),
    memberchk(C, Codigos), !,
    B = Base.

%% -----------------------------------------------------------------------------
%%  G.2 Léxico
%%      vocabulario(Categoria, Palabras)   (palabras ya normalizadas)
%% -----------------------------------------------------------------------------
vocabulario(determinante,  [el, la, los, las, un, una, unos, unas, mi, mis,
                            su, sus, tu, tus, este, estos, estas, ese, esa,
                            esos, esas]).
vocabulario(preposicion,   [a, al, de, del, en, con, por, para, desde, hasta,
                            sobre, entre]).
vocabulario(conector,      [y, e, ni, o, u, pero, ademas, tambien, luego,
                            entonces, mientras, aparte, ',']).
vocabulario(negacion,      [no, ni, nunca]).
vocabulario(intensificador, [muy, mucho, muchisimo, demasiado, bastante, super,
                            re, tan, algo]).
vocabulario(verbo_estado,  [esta, estan, queda, quedan, quedo, pone, ponen,
                            puso, vuelve, vuelven, volvio, sale, salen, aparece,
                            aparecen, muestra, muestran, es, son, va, van, anda,
                            andan, funciona, funcionan, ve, ven, se_ve, corre]).
vocabulario(sustantivo_equipo, [computador, computadora, computadores, pc,
                            ordenador, equipo, maquina, servidor, sistema,
                            aparato, compu]).
vocabulario(relleno,       [se, me, le, lo, les, nos, que, cuando, presenta,
                            presento, tiene, tienen, hay, hace, hacen, solo,
                            sola, solos, repente, veces, vez, siempre,
                            constantemente, frecuentemente, seguido,
                            ultimamente, aleatoriamente, inesperadamente,
                            repentinamente, rato, despues, antes, hoy, ayer,
                            dia, dias, semana, semanas, minutos, horas,
                            jugando, juego, juegos, usar, uso, usando,
                            trabajando, ya, aun, todavia, creo, parece, noto,
                            veo, note, pasa, sucede, ocurre, problema,
                            problemas, falla, fallas, encender, prender,
                            arrancar, iniciar, enciendo, prendo, cada, nada,
                            todo, toda, todos, otro, otra, momento, momentos,
                            antiguedad, mas, menos, como, porque, pues, raro,
                            rara, poco, bien, mal, tengo, tenemos, aproximadamente,
                            casi, c, suena, hola, buenas, ayuda, favor]).

% Vocabulario específico del dominio.
vocabulario(encender,      [enciende, encienden, prende, prenden, arranca,
                            arrancan, inicia, inician, bootea, energiza]).
vocabulario(energia,       [energia, corriente, electricidad, poder]).
vocabulario(luz,           [led, leds, luz, luces, bombillo, bombillos,
                            indicador, indicadores, piloto]).
vocabulario(encendido,     [encendido, encendida, encendidos, encendidas,
                            prendido, prendida, prendidos, prendidas, enciende,
                            encienden, prende, prenden]).
vocabulario(apagar,        [apaga, apagan, apago, apagando, apagarse]).
vocabulario(apagon,        [apagados, apagones, apagon]).
vocabulario(repentino,     [repentino, repentinos, aleatorios, inesperados]).
vocabulario(oler,          [huele, huelen, olor, olores]).
vocabulario(quemado,       [quemado, quemada, quemados, humo]).
vocabulario(pitido,        [pitido, pitidos, pita, pitea, bip, bips, beep,
                            beeps, pitazo, pitazos, pitar]).
vocabulario(largo,         [largo, larga, largos]).
vocabulario(corto,         [corto, cortos, corta, cortas]).
vocabulario(repetido,      [repetidos, repetido, seguidos, continuos,
                            constantes]).
vocabulario(error,         [error, errores, fallo, fallos]).
vocabulario(bios,          [bios, uefi, cmos, setup]).
vocabulario(hora,          [hora, fecha, reloj, horario]).
vocabulario(verbo_hora,    [pierde, pierden, perdio, desconfigura,
                            desconfiguran, borra, borran, atrasa, atrasan,
                            resetea, resetean, reinicia, reinician, cambia,
                            cambian]).
vocabulario(hora_mal,      [incorrecta, incorrecto, incorrectas, mal,
                            equivocada, desconfigurada, desconfiguradas,
                            atrasada, atrasadas, pierde, pierden, borra,
                            borran, atrasa, atrasan, reinicia, resetea]).
vocabulario(reiniciar,     [reinicia, reinician, reinicio, reinicios,
                            reiniciando, reiniciarse]).
vocabulario(ventilador,    [ventilador, ventiladores, fan, fans, abanico,
                            abanicos, cooler, coolers]).
vocabulario(girar,         [gira, giran, funciona, funcionan, mueve, mueven,
                            prende, prenden, enciende, encienden]).
vocabulario(detenido,      [detenido, detenidos, detenida, parado, parados,
                            quieto, quietos, trabado, trabados, frenado]).
vocabulario(verbo_ruido,   [hace, hacen, suena, suenan, esta, estan, emite,
                            emiten, tiene, tienen, zumba, zumban]).
vocabulario(ruido,         [ruido, ruidos, ruidoso, ruidosos, fuerte, duro,
                            alto, raro, raros, escandaloso, zumbido,
                            zumbidos]).
vocabulario(lento,         [lento, lenta, lentos, lentas, lentitud,
                            lentisimo, lentamente]).
vocabulario(demorar,       [demora, demoran, tarda, tardan]).
vocabulario(prep_inicio,   [en, al, para]).
vocabulario(iniciar,       [iniciar, arrancar, encender, prender, cargar,
                            bootear, iniciarse, prenderse, arranque, inicio,
                            encendido]).
vocabulario(arranque,      [arranque, inicio, encendido, booteo]).
vocabulario(pantalla,      [pantalla, pantallas, monitor, monitores, display,
                            pantallazo, pantallazos]).
vocabulario(azul,          [azul, azules]).
vocabulario(negro,         [negra, negro, negras, negros, oscura, oscuro,
                            apagada, apagado]).
vocabulario(dar,           [da, dan, muestra, muestran, hay, sale, salen,
                            tiene, tienen, aparece, envia, manda]).
vocabulario(senal_video,   [imagen, video, senal]).
vocabulario(verbo_pantalla, [enciende, prende, muestra, ve, da, funciona]).
vocabulario(linea,         [linea, lineas, raya, rayas, franja, franjas]).
vocabulario(parpadear,     [parpadea, parpadean, titila, titilan, parpadeo]).
vocabulario(artefacto,     [artefacto, artefactos, pixel, pixeles, puntos,
                            manchas, glitch, glitches, cuadros, cuadritos]).
vocabulario(distorsion,    [distorsionada, distorsionado, deformada,
                            pixelada, pixelado, rara, corrupta, cortada]).
vocabulario(congelar,      [congela, congelan, cuelga, cuelgan, traba, traban,
                            bloquea, bloquean, tilda, tildan, pega, pegan]).
vocabulario(quedar,        [queda, quedan, quedo]).
vocabulario(congelado,     [congelado, congelada, congelados, pegado, pegada,
                            trabado, trabada, colgado, colgada, bloqueado,
                            bloqueada]).
vocabulario(responder,     [responde, responden]).
vocabulario(bloqueo,       [bloqueo, bloqueos, congelamiento, congelamientos,
                            cuelgue, cuelgues]).
vocabulario(disco,         [disco, discos, hdd, ssd]).
vocabulario(clic,          [clic, clics, click, clicks, tic, tics, clac,
                            golpeteo, golpeteos]).
vocabulario(detectar,      [detecta, detectan, reconoce, reconocen, encuentra,
                            encuentran, lee, leen, ve, aparece]).
vocabulario(detectado,     [encontrado, detectado, reconocido, aparece,
                            funciona, detecta, reconoce, lee]).
vocabulario(unidad_temp,   [grados, grado, celsius, centigrados, c]).
vocabulario(palabra_temp,  [temperatura, temperaturas, temp, cpu,
                            procesador]).
vocabulario(puente_temp,   [esta, estan, llega, llego, marca, alcanza, sube,
                            de, del, la, el, a, en, los, es, son, hasta, por,
                            encima, arriba, cpu, procesador, temperatura, su,
                            aproximadamente, unos, casi, mas]).
vocabulario(anios,         [anos, ano]).

% lexico(?Categoria, +Palabra)
lexico(Categoria, Palabra) :-
    vocabulario(Categoria, Palabras),
    memberchk(Palabra, Palabras).

% Los números pueden venir en cifras o en palabras.
numero_palabra(un, 1).      numero_palabra(uno, 1).    numero_palabra(una, 1).
numero_palabra(dos, 2).     numero_palabra(tres, 3).   numero_palabra(cuatro, 4).
numero_palabra(cinco, 5).   numero_palabra(seis, 6).   numero_palabra(siete, 7).
numero_palabra(ocho, 8).    numero_palabra(nueve, 9).  numero_palabra(diez, 10).
numero_palabra(once, 11).   numero_palabra(doce, 12).  numero_palabra(quince, 15).
numero_palabra(veinte, 20).

tipo_palabra(portatil, portatil).
tipo_palabra(laptop, portatil).
tipo_palabra(notebook, portatil).
tipo_palabra(escritorio, escritorio).
tipo_palabra(torre, escritorio).
tipo_palabra(desktop, escritorio).
tipo_palabra(mesa, escritorio).

%% -----------------------------------------------------------------------------
%%  G.3 Alias de entrada libre
%%      alias_sintoma(Sintoma, Frase): frases sinónimas de un síntoma. Los
%%      alias que el experto enseña desde la interfaz son hechos
%%      alias_aprendido/2 del bloque de conocimiento aprendido.
%% -----------------------------------------------------------------------------
alias_sintoma(no_enciende, 'no enciende').
alias_sintoma(no_enciende, 'no prende').
alias_sintoma(no_enciende, 'no arranca').
alias_sintoma(no_enciende, 'no hay energia').
alias_sintoma(no_enciende, 'no tiene corriente').
alias_sintoma(no_enciende, 'no da señales de vida').
alias_sintoma(no_enciende, 'no arranca el computador').
alias_sintoma(olor_quemado, 'olor a quemado').
alias_sintoma(olor_quemado, 'olor quemado').
alias_sintoma(olor_quemado, 'huele a quemado').
alias_sintoma(olor_quemado, 'sale humo').
alias_sintoma(pantalla_negra, 'pantalla negra').
alias_sintoma(pantalla_negra, 'pantalla en negro').
alias_sintoma(pantalla_negra, 'monitor negro').
alias_sintoma(pantalla_negra, 'no muestra imagen').
alias_sintoma(pantalla_negra, 'pantalla no se ve').
alias_sintoma(pantalla_negra, 'sin imagen').
alias_sintoma(pantalla_negra, 'no da video').
alias_sintoma(pantalla_negra, 'monitor sin señal').
alias_sintoma(error_bios, 'error en la bios').
alias_sintoma(error_bios, 'error de bios').
alias_sintoma(error_bios, 'mensaje de error de la bios').
alias_sintoma(pantalla_azul, 'pantalla azul').
alias_sintoma(pantalla_azul, 'pantalla en azul').
alias_sintoma(pantalla_azul, 'pantallazo azul').
alias_sintoma(reinicios_aleatorios, 'se reinicia solo').
alias_sintoma(reinicios_aleatorios, 'se reinicia de repente').
alias_sintoma(reinicios_aleatorios, 'reinicia constantemente').
alias_sintoma(apagados_repentinos, 'se apaga inesperadamente').
alias_sintoma(apagados_repentinos, 'se apaga despues de un rato').
alias_sintoma(apagados_repentinos, 'se apaga jugando').
alias_sintoma(apagados_repentinos, 'se apaga al jugar').
alias_sintoma(apagados_repentinos, 'se apaga cuando juego').
alias_sintoma(ventilador_ruidoso, 'ventilador ruidoso').
alias_sintoma(ventilador_ruidoso, 'ventilador suena duro').
alias_sintoma(ventilador_ruidoso, 'ruido del ventilador').
alias_sintoma(ventilador_ruidoso, 'se calienta').
alias_sintoma(ventilador_ruidoso, 'se sobrecalienta').
alias_sintoma(ventilador_ruidoso, 'temperatura muy alta').
alias_sintoma(ventilador_ruidoso, 'equipo muy caliente').
alias_sintoma(ventilador_detenido, 'ventilador no gira').
alias_sintoma(ventilador_detenido, 'ventilador detenido').
alias_sintoma(ventiladores_giran, 'ventiladores giran').
alias_sintoma(lentitud, 'va lento').
alias_sintoma(lentitud, 'computador lento').
alias_sintoma(lentitud, 'computadora lenta').
alias_sintoma(lentitud, 'se demora mucho').
alias_sintoma(arranque_lento, 'arranque lento').
alias_sintoma(arranque_lento, 'tarda en iniciar').
alias_sintoma(arranque_lento, 'demora al arrancar').
alias_sintoma(ruido_clic, 'disco hace clic').
alias_sintoma(ruido_clic, 'disco hace ruido').
alias_sintoma(ruido_clic, 'ruido en el disco duro').
alias_sintoma(disco_no_encontrado, 'disco no encontrado').
alias_sintoma(disco_no_encontrado, 'no detecta el disco').
alias_sintoma(disco_no_encontrado, 'no reconoce el disco duro').
alias_sintoma(disco_no_encontrado, 'disco duro no funciona').
alias_sintoma(lineas_en_pantalla, 'líneas en la pantalla').
alias_sintoma(lineas_en_pantalla, 'rayas en la pantalla').
alias_sintoma(lineas_en_pantalla, 'pantalla con rayas').
alias_sintoma(lineas_en_pantalla, 'pantalla parpadea').
alias_sintoma(artefactos_video, 'artefactos en la pantalla').
alias_sintoma(artefactos_video, 'imagen distorsionada').
alias_sintoma(artefactos_video, 'pixeles de colores').
alias_sintoma(bloqueos, 'se congela').
alias_sintoma(bloqueos, 'se queda congelado').
alias_sintoma(bloqueos, 'se queda pegado').
alias_sintoma(bloqueos, 'no responde').
alias_sintoma(bloqueos, 'deja de responder').
alias_sintoma(Sintoma, Frase) :-
    alias_aprendido(Sintoma, Frase).

listar_aliases(Lista) :-
    findall([Sintoma, Frase], alias_sintoma(Sintoma, Frase), Lista).

%% -----------------------------------------------------------------------------
%%  G.4 Gramática
%% -----------------------------------------------------------------------------

% oracion(-Items): una oración es una secuencia de sintagmas.
% Items contiene hecho(H) por cada sintagma reconocido y desconocida(P) por
% cada palabra que no pertenece al léxico.
oracion(Items) --> sintagmas(Items).

sintagmas(Items) -->
    sintagma(Primero), !,
    sintagmas(Resto),
    { append(Primero, Resto, Items) }.
sintagmas([]) --> [].

% Prioridad: un sintagma con significado, luego conectores y relleno; lo
% demás se informa como palabra no reconocida.
sintagma([hecho(H)])       --> hecho_mas_largo(H), !.
sintagma([])               --> palabra(conector), !.
sintagma([])               --> relleno, !.
sintagma([desconocida(P)]) --> [P].

% hecho_mas_largo(-Hecho)
% Prueba todas las lecturas posibles desde la posición actual y se queda con
% la que consume más palabras ("tres pitidos cortos" gana a "tres pitidos").
% Ante un empate se respeta el orden de las cláusulas de hecho//1.
hecho_mas_largo(Hecho, S0, S) :-
    findall(H-S1, ( hecho(H, S0, S1), S1 \== S0 ), Lecturas),
    Lecturas = [Primera|Otras],
    mas_larga(Otras, Primera, Hecho-S).

mas_larga([], Mejor, Mejor).
mas_larga([H-S|Resto], H0-S0, Mejor) :-
    length(S, L), length(S0, L0),
    (   L < L0
    ->  mas_larga(Resto, H-S, Mejor)
    ;   mas_larga(Resto, H0-S0, Mejor)
    ).

% hecho(-Hecho): sintagmas que producen un hecho simbólico.
hecho(pitidos(P))       --> patron_pitidos(P).
hecho(temp_cpu(T))      --> temperatura(T).
hecho(antiguedad(A))    --> antiguedad(A).
hecho(tipo_equipo(T))   --> tipo_de_equipo(T).
hecho(S)                --> sintoma(S).
hecho(S)                --> frase_alias(S).
hecho(S)                --> identificador_sintoma(S).
hecho(ausente(S))       --> sintoma_negado(S).
hecho(ausente(no_enciende)) --> encendido_afirmado.

% Negación (Entregable 4): "no huele a quemado" NO es olor_quemado. Un síntoma
% precedido por 'no' o 'ni' (y, a lo sumo, dos palabras de enlace) produce
% ausente(S). hecho_mas_largo/3 prefiere esta lectura a la del síntoma suelto
% porque consume la negación. Los síntomas que ya son negativos por definición
% (no_enciende, ventilador_detenido, disco_no_encontrado) no se vuelven a negar.
sintoma_negado(S) -->
    negador, enlace_negacion,
    ( sintoma(S) ; frase_alias(S) ),
    { \+ memberchk(S, [no_enciende, ventilador_detenido, disco_no_encontrado]) },
    opcional([nunca]).

negador --> [no].
negador --> [ni].

enlace_negacion --> [].
enlace_negacion --> palabra_de_enlace, enlace_negacion_resto.
enlace_negacion_resto --> [].
enlace_negacion_resto --> palabra_de_enlace.
palabra_de_enlace --> [P], { memberchk(P, [se, me, hay, tiene, tienen, presenta,
                                            sale, esta, sigue, veo, noto, tengo,
                                            hace, nada]) }.

% "mi pc sí enciende", "el equipo enciende normal": el equipo SÍ arranca, lo
% que contradice 'no_enciende' si el usuario también lo reportó.
encendido_afirmado -->
    opcional(palabra(sustantivo_equipo)),
    (   [si], palabra(encender)
    ;   palabra(encender), ( [normal] ; [normalmente] ; [bien] )
    ).

% Un alias (base o aprendido) es una secuencia fija de palabras.
frase_alias(Sintoma) -->
    { alias_sintoma(Sintoma, Frase), tokenizar(Frase, Palabras), Palabras \== [] },
    Palabras.

% El nombre interno de un síntoma ("pantalla_azul") también se acepta.
identificador_sintoma(Sintoma) -->
    { sintoma_catalogo(Sintoma, _), atomic_list_concat(Partes, '_', Sintoma) },
    Partes.

% --- No terminales auxiliares --------------------------------------------------
palabra(Categoria) --> [P], { lexico(Categoria, P) }.

relleno --> [P], { palabra_de_relleno(P) }.

palabra_de_relleno(P) :-
    member(Categoria, [determinante, preposicion, intensificador, verbo_estado,
                       sustantivo_equipo, relleno]),
    lexico(Categoria, P), !.

opcional(G) --> G.
opcional(_) --> [].

det_opt            --> opcional(palabra(determinante)).
se_opt             --> [].
se_opt             --> [se].
se_opt             --> [se, me].
se_opt             --> [me].
verbo_estado_opt   --> opcional(palabra(verbo_estado)).
intensificador_opt --> [].
intensificador_opt --> palabra(intensificador), intensificador_opt.
negacion           --> palabra(negacion).
conector_opt       --> opcional(palabra(conector)).
pantalla           --> det_opt, palabra(pantalla).
disco              --> det_opt, palabra(disco), opcional([duro]).
de_colores         --> [de], ( [colores] ; [color] ).
de_colores         --> ( [raros] ; [raras] ).

numero(N) --> [P], { atom_number(P, N), integer(N) }.
numero(N) --> [P], { numero_palabra(P, N) }.

% --- Mediciones y datos del equipo -------------------------------------------
% "95 grados", "la cpu esta a 97 grados", "temperatura de 90"
temperatura(T) -->
    numero(T), palabra(unidad_temp),
    { between(0, 500, T) }.
temperatura(T) -->
    det_opt, palabra(palabra_temp), puente_temp, numero(T),
    opcional(palabra(unidad_temp)),
    { between(0, 500, T) }.

puente_temp --> [].
puente_temp --> palabra(puente_temp), puente_temp.

% "7 años", "siete años de antigüedad"
antiguedad(A) -->
    numero(A), palabra(anios), opcional(([de], ([antiguedad] ; [uso]))),
    { between(0, 60, A) }.

% "portátil", "computador de escritorio", "un pc de mesa"
tipo_de_equipo(T) -->
    det_opt, opcional(palabra(sustantivo_equipo)), opcional(palabra(preposicion)),
    [P], { tipo_palabra(P, T) }.

% --- Pitidos de la BIOS ---------------------------------------------------------
% "tres pitidos cortos", "un pitido largo y dos cortos", "pitidos repetidos"
patron_pitidos(tres_cortos) -->
    numero(3), opcional(palabra(pitido)), palabra(corto).
patron_pitidos(Patron) -->
    numero(1), opcional(palabra(pitido)), palabra(largo), conector_opt,
    numero(N), opcional(palabra(pitido)), palabra(corto),
    { patron_largo_cortos(N, Patron) }.
patron_pitidos(cortos_repetidos) -->
    palabra(pitido), opcional(palabra(corto)), palabra(repetido).

patron_largo_cortos(2, un_largo_dos_cortos).
patron_largo_cortos(3, un_largo_tres_cortos).

% --- Síntomas: energía ----------------------------------------------------------
sintoma(no_enciende) -->
    negacion, se_opt, palabra(encender).
sintoma(no_enciende) -->
    negacion, [hay], palabra(energia).
sintoma(led_encendido) -->
    det_opt, palabra(luz), se_opt, verbo_estado_opt, palabra(encendido).
sintoma(apagados_repentinos) -->
    se_opt, palabra(apagar).
sintoma(apagados_repentinos) -->
    palabra(apagon), opcional(palabra(repentino)).
sintoma(olor_quemado) -->
    palabra(oler), opcional([a]), palabra(quemado).
sintoma(olor_quemado) -->
    [humo].

% --- Síntomas: placa base y BIOS -------------------------------------------------
sintoma(pitidos_arranque) -->
    opcional(numero(_)), palabra(pitido).
sintoma(error_bios) -->
    palabra(error), opcional([en]), det_opt, palabra(bios).
sintoma(error_bios) -->
    palabra(bios), opcional(palabra(error)).
sintoma(hora_incorrecta) -->
    se_opt, palabra(verbo_hora), det_opt, palabra(hora), y_hora_opt.
sintoma(hora_incorrecta) -->
    det_opt, palabra(hora), y_hora_opt, se_opt, verbo_estado_opt,
    palabra(hora_mal).

% --- Síntomas: procesador y refrigeración ----------------------------------------
sintoma(reinicios_aleatorios) -->
    se_opt, palabra(reiniciar).
sintoma(ventilador_detenido) -->
    det_opt, palabra(ventilador), negacion, se_opt, palabra(girar).
sintoma(ventilador_detenido) -->
    det_opt, palabra(ventilador), verbo_estado_opt, palabra(detenido).
sintoma(ventiladores_giran) -->
    det_opt, palabra(ventilador), opcional([si]), se_opt, palabra(girar).
sintoma(ventilador_ruidoso) -->
    det_opt, palabra(ventilador), opcional(palabra(verbo_ruido)),
    intensificador_opt, palabra(ruido).
sintoma(ventilador_ruidoso) -->
    palabra(ruido), palabra(preposicion), det_opt, palabra(ventilador).
sintoma(lentitud) -->
    verbo_estado_opt, intensificador_opt, palabra(lento).
sintoma(lentitud) -->
    se_opt, palabra(demorar), intensificador_opt.

% --- Síntomas: memoria e inestabilidad -------------------------------------------
sintoma(pantalla_azul) -->
    pantalla, se_opt, verbo_estado_opt, opcional(palabra(preposicion)),
    palabra(azul).
sintoma(pantalla_azul) -->
    [bsod].
sintoma(bloqueos) -->
    se_opt, palabra(congelar).
sintoma(bloqueos) -->
    se_opt, palabra(quedar), palabra(congelado).
sintoma(bloqueos) -->
    negacion, palabra(responder).
sintoma(bloqueos) -->
    [deja, de, responder].
sintoma(bloqueos) -->
    palabra(bloqueo).

% --- Síntomas: almacenamiento -----------------------------------------------------
sintoma(arranque_lento) -->
    det_opt, palabra(arranque), verbo_estado_opt, intensificador_opt,
    palabra(lento).
sintoma(arranque_lento) -->
    se_opt, palabra(demorar), intensificador_opt, palabra(prep_inicio),
    det_opt, palabra(iniciar).
sintoma(arranque_lento) -->
    verbo_estado_opt, intensificador_opt, palabra(lento),
    palabra(prep_inicio), det_opt, palabra(iniciar).
sintoma(arranque_lento) -->
    palabra(encender), intensificador_opt, palabra(lento).
sintoma(ruido_clic) -->
    disco, opcional(palabra(verbo_ruido)), opcional(palabra(determinante)),
    intensificador_opt, ( palabra(clic) ; palabra(ruido) ).
sintoma(ruido_clic) -->
    opcional(palabra(verbo_ruido)), opcional(palabra(determinante)),
    palabra(clic), opcional((palabra(preposicion), disco)).
sintoma(ruido_clic) -->
    palabra(ruido), palabra(preposicion), disco.
sintoma(disco_no_encontrado) -->
    disco, negacion, se_opt, palabra(detectado).
sintoma(disco_no_encontrado) -->
    negacion, se_opt, palabra(detectar), disco.

% --- Síntomas: video ---------------------------------------------------------------
sintoma(pantalla_negra) -->
    pantalla, se_opt, verbo_estado_opt, opcional(palabra(preposicion)),
    palabra(negro).
sintoma(pantalla_negra) -->
    pantalla, se_opt, palabra(apagar).
sintoma(pantalla_negra) -->
    pantalla, negacion, se_opt, palabra(verbo_pantalla),
    opcional((det_opt, palabra(senal_video))).
sintoma(pantalla_negra) -->
    opcional(pantalla), [sin], palabra(senal_video).
sintoma(pantalla_negra) -->
    negacion, se_opt, palabra(dar), det_opt, palabra(senal_video).
sintoma(pantalla_negra) -->
    negacion, se_opt, [ve], opcional([nada]),
    opcional((palabra(preposicion), pantalla)).
sintoma(lineas_en_pantalla) -->
    palabra(linea), opcional(de_colores),
    opcional((palabra(preposicion), pantalla)).
sintoma(lineas_en_pantalla) -->
    pantalla, [con], palabra(linea).
sintoma(lineas_en_pantalla) -->
    pantalla, palabra(parpadear).
sintoma(lineas_en_pantalla) -->
    palabra(parpadear), opcional(pantalla).
sintoma(artefactos_video) -->
    palabra(artefacto), opcional(de_colores),
    opcional((palabra(preposicion), det_opt, ( palabra(pantalla) ; [imagen] ))).
sintoma(artefactos_video) -->
    det_opt, [imagen], se_opt, verbo_estado_opt, palabra(distorsion).

y_hora_opt --> [].
y_hora_opt --> ( [y] ; [e] ), det_opt, palabra(hora).

%% -----------------------------------------------------------------------------
%%  G.5 Interfaz de la DCG para Python
%% -----------------------------------------------------------------------------

% parsear_oracion(+Texto, -Hechos, -NoReconocidas)
% Hechos usa los mismos formatos que consultar_caso/2 (síntomas, temp_cpu/1,
% pitidos/1 y equipo/2), sin duplicados y en el orden en que aparecen.
parsear_oracion(Texto, Hechos, NoReconocidas) :-
    tokenizar(Texto, Palabras),
    phrase(oracion(Items), Palabras), !,
    findall(H, member(hecho(H), Items), Crudos),
    findall(P, member(desconocida(P), Items), Desconocidas),
    combinar_equipo(Crudos, Combinados),
    list_to_set(Combinados, Hechos),
    list_to_set(Desconocidas, NoReconocidas).

% El tipo y la antigüedad pueden aparecer separados en la oración
% ("mi portátil ... tiene 7 años"); se combinan en un solo equipo/2.
% Sin antigüedad el tipo solo no aporta a ninguna regla y se omite.
combinar_equipo(Crudos, Hechos) :-
    partition(dato_de_equipo, Crudos, DatosEquipo, Otros),
    findall(A, member(antiguedad(A), DatosEquipo), Edades0),
    list_to_set(Edades0, Edades),
    findall(T, member(tipo_equipo(T), DatosEquipo), Tipos0),
    list_to_set(Tipos0, Tipos),
    (   Edades == []
    ->  Hechos = Otros
    ;   emparejar_equipos(Edades, Tipos, Equipos),
        append(Otros, Equipos, Hechos)
    ).

% emparejar_equipos(+Edades, +Tipos, -Equipos)
% Una antigüedad distinta por cada "equipo" mencionado: así "mi portátil de 2
% años y mi escritorio de 9 años" llega a la parte I como dos equipos distintos
% (contradicción) en lugar de descartar en silencio el segundo.
emparejar_equipos([], _, []).
emparejar_equipos([A|Resto], Tipos, [equipo(T, A)|Equipos]) :-
    (   Tipos = []  -> T = desconocido, Siguientes = []
    ;   Tipos = [T] -> Siguientes = Tipos
    ;   Tipos = [T|Siguientes]
    ),
    emparejar_equipos(Resto, Siguientes, Equipos).

dato_de_equipo(antiguedad(_)).
dato_de_equipo(tipo_equipo(_)).

% parsear_oracion_texto(+Texto, -HechosTexto, -NoReconocidas)
% Igual que parsear_oracion/3, con cada hecho escrito como átomo Prolog.
parsear_oracion_texto(Texto, HechosTexto, NoReconocidas) :-
    parsear_oracion(Texto, Hechos, NoReconocidas),
    maplist(termino_a_atomo, Hechos, HechosTexto).

termino_a_atomo(Termino, Atomo) :-
    format(atom(Atomo), '~q', [Termino]).


%% =============================================================================
%%  PARTE H. ADQUISICIÓN DINÁMICA DE CONOCIMIENTO (MODO EXPERTO)
%%
%%  regla_aprendida(Id, Nombre, Componente, Requeridas, Excluyentes,
%%                  Certeza, Gravedad, Accion)
%%    Requeridas y Excluyentes son listas de condiciones: síntomas del
%%    catálogo, pitidos(Patron), prueba(Nombre, Resultado), temp_cpu_alta o
%%    equipo_antiguo. La regla genérica R26 (parte B) las evalúa.
%%
%%  Python valida la regla con validar_regla/8, la inyecta con assertz/1 y
%%  reescribe el bloque de conocimiento aprendido al final de este archivo
%%  con el texto que produce contenido_aprendido/1.
%% =============================================================================

% validar_regla(+Id, +Nombre, +Componente, +Requeridas, +Excluyentes,
%               +Certeza, +Gravedad, +Accion)
validar_regla(Id, Nombre, Componente, Requeridas, Excluyentes,
              Certeza, Gravedad, Accion) :-
    identificador_valido(Id),
    \+ gravedad(Id, _),                      % no reemplaza otro diagnóstico
    atom(Nombre), Nombre \== '',
    atom(Accion), Accion \== '',
    atom(Componente), componente(Componente, _),
    memberchk(Certeza, [alta, media]),
    memberchk(Gravedad, [baja, media, alta]),
    is_list(Requeridas), Requeridas \== [],
    is_list(Excluyentes),
    forall(member(C, Requeridas), condicion_valida(C)),
    forall(member(C, Excluyentes), condicion_valida(C)),
    once(( member(S, Requeridas), atom(S), sintoma_catalogo(S, _) )),
    \+ ( member(C, Requeridas), memberchk(C, Excluyentes) ).

identificador_valido(Id) :-
    atom(Id),
    atom_codes(Id, [Primero|Resto]),
    between(0'a, 0'z, Primero),
    forall(member(C, Resto),
           ( between(0'a, 0'z, C) ; between(0'0, 0'9, C) ; C =:= 0'_ )).

% condicion_valida(+Condicion)  (cláusulas excluyentes con corte)
condicion_valida(C) :- \+ ground(C), !, fail.
condicion_valida(temp_cpu_alta) :- !.
condicion_valida(equipo_antiguo) :- !.
condicion_valida(pitidos(P)) :- !, codigo_pitido(P, _).
condicion_valida(prueba(N, R)) :- !, prueba_catalogo(N, _), resultado_prueba(R, _).
condicion_valida(S) :- atom(S), sintoma_catalogo(S, _).

% aprender_regla/8: validación más assertz/1 en una sola llamada (útil desde
% la consola de SWI-Prolog; la persistencia la hace Python).
aprender_regla(Id, Nombre, Componente, Requeridas, Excluyentes,
               Certeza, Gravedad, Accion) :-
    validar_regla(Id, Nombre, Componente, Requeridas, Excluyentes,
                  Certeza, Gravedad, Accion),
    assertz(regla_aprendida(Id, Nombre, Componente, Requeridas, Excluyentes,
                            Certeza, Gravedad, Accion)).

% olvidar_regla(+Id)
olvidar_regla(Id) :-
    retract(regla_aprendida(Id, _, _, _, _, _, _, _)).

% listar_reglas_aprendidas(-Lista)
% [[Id, Nombre, Componente, Requeridas, Excluyentes, Certeza, Gravedad, Accion]]
% con las condiciones escritas como átomos.
listar_reglas_aprendidas(Lista) :-
    findall([Id, Nombre, Componente, ReqTexto, ExclTexto, Certeza, Gravedad, Accion],
            ( regla_aprendida(Id, Nombre, Componente, Req, Excl,
                              Certeza, Gravedad, Accion),
              maplist(termino_a_atomo, Req, ReqTexto),
              maplist(termino_a_atomo, Excl, ExclTexto) ),
            Lista).

% agregar_alias(+Frase, +Sintoma): enseña una frase nueva para un síntoma.
agregar_alias(Frase, Sintoma) :-
    atom(Frase),
    atom(Sintoma),
    sintoma_catalogo(Sintoma, _),
    \+ alias_sintoma(Sintoma, Frase),
    assertz(alias_aprendido(Sintoma, Frase)).

% olvidar_alias(+Sintoma, +Frase)
olvidar_alias(Sintoma, Frase) :-
    retract(alias_aprendido(Sintoma, Frase)).

listar_aliases_aprendidos(Lista) :-
    findall([Sintoma, Frase], alias_aprendido(Sintoma, Frase), Lista).

% contenido_aprendido(-Texto)
% Cláusulas del bloque de conocimiento aprendido, listas para escribirse en
% el archivo. portray_clause/1 cita los átomos para que el archivo vuelva a
% cargarse con consult/1. Cada regla va precedida de un comentario con la
% regla lógica equivalente.
contenido_aprendido(Texto) :-
    with_output_to(string(Cadena), escribir_conocimiento_aprendido),
    atom_string(Texto, Cadena).

escribir_conocimiento_aprendido :-
    forall(alias_aprendido(Sintoma, Frase),
           portray_clause(alias_aprendido(Sintoma, Frase))),
    forall(regla_aprendida(Id, Nombre, Componente, Req, Excl,
                           Certeza, Gravedad, Accion),
           ( nl,
             comentar_regla(Id, Nombre, Req, Excl, Certeza),
             portray_clause(regla_aprendida(Id, Nombre, Componente, Req, Excl,
                                            Certeza, Gravedad, Accion)) )).

comentar_regla(Id, Nombre, Requeridas, Excluyentes, Certeza) :-
    format('% R26 aprendida: ~w~n', [Nombre]),
    format('%   diagnostico(E, ~q, ~q) :-~n', [Id, Certeza]),
    forall(member(C, Requeridas),
           ( condicion_como_meta(C, Meta), format('%       ~w,~n', [Meta]) )),
    forall(member(C, Excluyentes),
           ( condicion_como_meta(C, Meta), format('%       \\+ ~w,~n', [Meta]) )),
    format('%       \\+ descartado(E, ~q).~n', [Id]).

condicion_como_meta(temp_cpu_alta, 'sobrecalentamiento(E)') :- !.
condicion_como_meta(equipo_antiguo, 'equipo_antiguo(E)') :- !.
condicion_como_meta(pitidos(P), Meta) :- !,
    format(atom(Meta), 'pitidos(E, ~q)', [P]).
condicion_como_meta(prueba(N, R), Meta) :- !,
    format(atom(Meta), 'prueba(E, ~q, ~q)', [N, R]).
condicion_como_meta(Sintoma, Meta) :-
    format(atom(Meta), 'observado(E, ~q)', [Sintoma]).


%% =============================================================================
%%  CONOCIMIENTO APRENDIDO
%%  Lo escribe motor_inferencia.py desde el modo experto. No lo edites a mano:
%%  el bloque entre las dos marcas se reemplaza completo cada vez que el
%%  experto agrega o elimina un alias o una regla.
%% =============================================================================
%% === INICIO CONOCIMIENTO APRENDIDO (no editar a mano) ===
%% === FIN CONOCIMIENTO APRENDIDO ===
