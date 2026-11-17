:- encoding(utf8).
%% =============================================================================
%%  pruebas_estres.pl  -  Entregable 4: pruebas de estrés del motor simbólico
%%
%%  Ejecución (desde la carpeta del proyecto):
%%      swipl -q -f none -g correr_pruebas -t halt pruebas_estres.pl
%%  Código de salida: 0 si todo pasa, 1 si algún caso falla.
%%
%%  No necesita Python: ejercita directamente la base de conocimiento, es decir,
%%  la parte I (consistencia), la DCG (negación y ambigüedad) y la robustez del
%%  flujo analizar_caso/2. pruebas.py repite lo esencial a través de PySwip.
%%
%%  Grupos:
%%    A. Contradicciones que DEBEN bloquearse (estado entrada_contradictoria).
%%    B. Combinaciones coherentes que NO deben bloquearse (falsos positivos).
%%    C. Entradas ambiguas en lenguaje natural enviadas a la DCG.
%%    D. Robustez: entradas malformadas y casos extremos.
%%    E. Propiedades: sin diagnóstico si hay contradicción, independencia del
%%       orden y recorrido exhaustivo de pares de síntomas.
%% =============================================================================

:- set_stream(user_output, encoding(utf8)).
:- initialization(consult('base_conocimiento.pl')).
:- dynamic fallo/1.

%% --- A. Contradicciones: caso(Id, Descripcion, Entrada, TipoEsperado) -------
contradictorio(a01, 'No enciende y los ventiladores giran',
    [no_enciende, ventiladores_giran], sintomas_incompatibles).
contradictorio(a02, 'No enciende y aparece pantalla azul',
    [no_enciende, pantalla_azul], sintomas_incompatibles).
contradictorio(a03, 'No enciende pero el disco hace clics',
    [no_enciende, ruido_clic], sintomas_incompatibles).
contradictorio(a04, 'Pantalla negra y pantalla azul',
    [pantalla_negra, pantalla_azul], sintomas_incompatibles).
contradictorio(a05, 'Ventilador detenido y ventilador ruidoso',
    [ventilador_detenido, ventilador_ruidoso], sintomas_incompatibles).
contradictorio(a06, 'Ventilador detenido y ventiladores girando',
    [ventilador_detenido, ventiladores_giran], sintomas_incompatibles).
contradictorio(a07, 'Disco no detectado pero con prueba SMART',
    [disco_no_encontrado, prueba(smart_disco, ok)], sintomas_incompatibles).
contradictorio(a08, 'Olor a quemado reportado y negado',
    [olor_quemado, ausente(olor_quemado)], afirmado_y_negado).
contradictorio(a09, 'No enciende y "sí enciende"',
    [no_enciende, ausente(no_enciende)], afirmado_y_negado).
contradictorio(a10, 'CPU a 500 grados (imposible)',
    [temp_cpu(500)], lectura_imposible).
contradictorio(a11, 'CPU a 3 grados en un equipo funcionando',
    [temp_cpu(3), ventilador_ruidoso], lectura_imposible).
contradictorio(a12, 'Dos lecturas de temperatura muy distintas',
    [temp_cpu(40), temp_cpu(99)], lecturas_discrepantes).
contradictorio(a13, '97 °C pero nivel discreto "normal"',
    [temp_cpu(97), dato(temperatura_cpu, normal)], nivel_discordante).
contradictorio(a14, '30 °C pero nivel discreto "critica"',
    [temp_cpu(30), dato(temperatura_cpu, critica)], nivel_discordante).
contradictorio(a15, 'Equipo de 9 años con nivel "nuevo"',
    [equipo(portatil, 9), dato(antiguedad, nuevo)], nivel_discordante).
contradictorio(a16, 'Misma prueba con resultados opuestos',
    [prueba(cambio_cable, ok), prueba(cambio_cable, falla)], datos_duplicados).
contradictorio(a17, 'Dos patrones de pitidos distintos',
    [pitidos(tres_cortos), pitidos(cortos_repetidos)], datos_duplicados).
contradictorio(a18, 'Dos equipos distintos',
    [equipo(portatil, 2), equipo(escritorio, 9)], datos_duplicados).
contradictorio(a19, 'Dos niveles para la misma variable',
    [dato(uso_disco, normal), dato(uso_disco, critico)], datos_duplicados).
contradictorio(a20, 'Contradicción escondida entre muchos hechos válidos',
    [olor_quemado, hora_incorrecta, equipo(escritorio, 7), prueba(reasentar_ram, resuelve),
     lentitud, no_enciende, prueba(fuente_con_probador, ok)], sintomas_incompatibles).

%% --- B. Coherentes: no deben bloquearse. Estado esperado -------------------
coherente(b01, 'No enciende con LED de reserva',
    [no_enciende, led_encendido], datos_insuficientes).
coherente(b02, 'No enciende, olor a quemado y fuente defectuosa',
    [no_enciende, olor_quemado, prueba(fuente_con_probador, falla)], ok).
coherente(b03, 'No enciende y pitidos de la BIOS (placa base)',
    [no_enciende, prueba(fuente_con_probador, ok), pitidos(un_largo_tres_cortos)], ok).
coherente(b04, 'Pantalla negra con ventiladores girando y cable cambiado',
    [pantalla_negra, ventiladores_giran, prueba(cambio_cable, resuelve)], ok).
coherente(b05, 'Refrigeración: 97 °C y ventilador ruidoso',
    [temp_cpu(97), ventilador_ruidoso], ok).
coherente(b06, '97 °C con nivel discreto "critica"',
    [temp_cpu(97), dato(temperatura_cpu, critica)], datos_insuficientes).
coherente(b07, 'Dos lecturas de temperatura cercanas',
    [temp_cpu(90), temp_cpu(95), ventilador_ruidoso], ok).
coherente(b08, 'Mismo resultado de prueba repetido',
    [pantalla_negra, ventiladores_giran, prueba(cambio_cable, resuelve),
     prueba(cambio_cable, resuelve)], ok).
coherente(b09, 'Ausencia de un síntoma distinto del reportado',
    [olor_quemado, ausente(lentitud)], datos_insuficientes).
coherente(b10, 'Equipo antiguo con nivel "antiguo"',
    [hora_incorrecta, equipo(escritorio, 7), dato(antiguedad, antiguo)], ok).
coherente(b11, 'Pantalla azul y reinicios (RAM)',
    [pantalla_azul, reinicios_aleatorios, prueba(reasentar_ram, resuelve)], ok).
coherente(b13, 'Pantalla negra con líneas y ventiladores (caso GPU)',
    [pantalla_negra, ventiladores_giran, lineas_en_pantalla, prueba(cambio_cable, no_resuelve),
     prueba(otro_monitor, no_resuelve)], ok).
coherente(b12, 'Temperatura de 10 grados (límite inferior plausible)',
    [temp_cpu(10), ventilador_ruidoso], datos_insuficientes).

%% --- C. Lenguaje natural ambiguo: oracion(Id, Texto, Hechos esperados, Estado) --
natural(c01, 'mi pc no huele a quemado', [ausente(olor_quemado)], datos_insuficientes).
natural(c02, 'no se apaga nunca', [ausente(apagados_repentinos)], datos_insuficientes).
natural(c03, 'el computador si enciende', [ausente(no_enciende)], datos_insuficientes).
natural(c04, 'mi pc no prende pero los ventiladores giran',
    [no_enciende, ventiladores_giran], entrada_contradictoria).
natural(c05, 'huele a quemado y no huele a quemado',
    [olor_quemado, ausente(olor_quemado)], entrada_contradictoria).
natural(c06, 'no enciende y el pc enciende normal',
    [no_enciende, ausente(no_enciende)], entrada_contradictoria).
natural(c07, 'la cpu esta a 200 grados', [temp_cpu(200)], entrada_contradictoria).
natural(c08, 'la cpu esta a 60 grados y a 99 grados',
    [temp_cpu(60), temp_cpu(99)], entrada_contradictoria).
natural(c09, 'mi portatil de 2 años y mi escritorio de 9 años',
    [equipo(portatil, 2), equipo(escritorio, 9)], entrada_contradictoria).
natural(c10, 'no enciende ni huele a quemado',
    [no_enciende, ausente(olor_quemado)], datos_insuficientes).
natural(c11, 'no se reinicia ni se apaga',
    [ausente(reinicios_aleatorios), ausente(apagados_repentinos)], datos_insuficientes).
natural(c12, 'Mi PC NO PRENDE, y huele a quemado!!!', [no_enciende, olor_quemado],
    ok).
natural(c13, 'la pantalla esta negra y la pantalla se pone azul',
    [pantalla_negra, pantalla_azul], entrada_contradictoria).
natural(c14, 'mi portátil de 7 años pierde la fecha y hora',
    [hora_incorrecta, equipo(portatil, 7)], ok).
natural(c15, 'el pc va lento y la cpu está a 95 grados', [lentitud, temp_cpu(95)],
    datos_insuficientes).

%% --- D. Robustez: robusto(Id, Descripcion, Entrada, EstadoEsperado) ----------
robusto(d01, 'Entrada que no es lista', foo, entrada_invalida).
robusto(d02, 'Lista vacía', [], entrada_vacia).
robusto(d03, 'Solo elementos desconocidos', [xyz, temp_cpu(abc), 42], entrada_invalida).
robusto(d04, 'Variable sin instanciar dentro de la lista', [_, no_enciende],
    datos_insuficientes).
robusto(d05, 'ausente/1 con síntoma inexistente', [ausente(inventado)], entrada_invalida).
robusto(d06, 'Duplicados exactos', [pantalla_negra, pantalla_negra, pantalla_negra],
    datos_insuficientes).
robusto(d07, 'Temperatura negativa', [temp_cpu(-40)], entrada_contradictoria).
robusto(d08, 'Temperatura decimal fuera de rango', [temp_cpu(150.5), lentitud],
    entrada_contradictoria).

%% =============================================================================
%%  Ejecución
%% =============================================================================
correr_pruebas :-
    retractall(fallo(_)),
    format("~n=== PRUEBAS DE ESTRÉS - HARDDIAG (Entregable 4) ===~n"),
    grupo('A. Contradicciones que deben bloquearse', Ga, Ta, grupo_a),
    grupo('B. Combinaciones coherentes (no deben bloquearse)', Gb, Tb, grupo_b),
    grupo('C. Lenguaje natural ambiguo (DCG)', Gc, Tc, grupo_c),
    grupo('D. Robustez ante entradas malformadas', Gd, Td, grupo_d),
    propiedades(Ge, Te),
    Total is Ta + Tb + Tc + Td + Te,
    Pasan is Ga + Gb + Gc + Gd + Ge,
    format("~n=== RESULTADO: ~d de ~d verificaciones aprobadas ===~n", [Pasan, Total]),
    (   Pasan =:= Total
    ->  format("TODAS LAS PRUEBAS PASARON~n")
    ;   format("HAY PRUEBAS FALLIDAS~n"), halt(1)
    ).

grupo(Titulo, Pasan, Total, Meta) :-
    format("~n--- ~w ---~n", [Titulo]),
    findall(R, call(Meta, R), Resultados),
    length(Resultados, Total),
    include(==(ok), Resultados, Oks),
    length(Oks, Pasan).

informar(Id, Desc, Entrada, Esperado, Obtenido, Resultado) :-
    (   Esperado == Obtenido -> Resultado = ok, Marca = 'OK  '
    ;   Resultado = fallo, Marca = 'FALLO', assertz(fallo(Id))
    ),
    format("[~w] ~w ~w~n        entrada : ~q~n        esperado: ~w | obtenido: ~w~n",
           [Marca, Id, Desc, Entrada, Esperado, Obtenido]).

estado_de(Entrada, Estado) :-
    (   catch(consultar_caso(Entrada, [Estado|_]), _, fail) -> true
    ;   Estado = excepcion
    ).

grupo_a(R) :-
    contradictorio(Id, Desc, Entrada, Tipo),
    estado_de(Entrada, Estado),
    contradicciones_caso(Entrada, Cs),
    ( memberchk([Tipo|_], Cs) -> TipoOk = Tipo ; TipoOk = sin_tipo ),
    ( Estado == entrada_contradictoria, TipoOk == Tipo
    -> Obtenido = Tipo ; Obtenido = fallo(Estado, TipoOk) ),
    informar(Id, Desc, Entrada, Tipo, Obtenido, R).

grupo_b(R) :-
    coherente(Id, Desc, Entrada, Esperado),
    estado_de(Entrada, Estado),
    informar(Id, Desc, Entrada, Esperado, Estado, R).

grupo_c(R) :-
    natural(Id, Texto, HechosEsperados, EstadoEsperado),
    parsear_oracion(Texto, Hechos, _),
    estado_de(Hechos, Estado),
    (   Hechos == HechosEsperados, Estado == EstadoEsperado
    ->  Obtenido = EstadoEsperado
    ;   Obtenido = fallo(Hechos, Estado)
    ),
    informar(Id, Texto, HechosEsperados, EstadoEsperado, Obtenido, R).

grupo_d(R) :-
    robusto(Id, Desc, Entrada, Esperado),
    estado_de(Entrada, Estado),
    informar(Id, Desc, Entrada, Esperado, Estado, R).

%% --- E. Propiedades -----------------------------------------------------------
propiedades(Pasan, Total) :-
    format("~n--- E. Propiedades y recorrido exhaustivo ---~n"),
    findall(S, sintoma_catalogo(S, _), Sintomas),
    length(Sintomas, NS),
    % E1: ningún estado inesperado ni excepción para TODOS los pares de síntomas.
    findall(Par-Estado,
            ( member(A, Sintomas), member(B, Sintomas), A @< B, Par = [A, B],
              estado_de(Par, Estado) ),
            Pares),
    length(Pares, NPares),
    findall(P, ( member(P-E, Pares), \+ memberchk(E, [ok, datos_insuficientes,
                                                      entrada_contradictoria]) ),
            Raros),
    resultado_prop('E1 todos los pares de síntomas dan un estado válido',
                   NPares, Raros == [], P1),
    % E2: contradictorio  =>  cero diagnósticos y cero sospechosos.
    findall(Par, ( member(Par-entrada_contradictoria, Pares),
                   consultar_caso(Par, [_, D, S, _]), ( D \== [] ; S \== [] ) ),
            ConDiag),
    resultado_prop('E2 una contradicción nunca emite diagnóstico', NPares,
                   ConDiag == [], P2),
    % E3: el resultado no depende del orden de la entrada.
    findall(Par, ( member(Par-Estado, Pares), reverse(Par, Inv),
                   estado_de(Inv, Otro), Otro \== Estado ), Sensibles),
    resultado_prop('E3 el estado no depende del orden de los hechos', NPares,
                   Sensibles == [], P3),
    % E4: los 19 síntomas a la vez (caso extremo): debe bloquearse y no fallar.
    estado_de(Sintomas, EstadoTodos),
    resultado_prop('E4 todos los síntomas juntos se bloquean', NS,
                   EstadoTodos == entrada_contradictoria, P4),
    % E5: análisis completo (explicación) coherente con consultar_caso.
    findall(Par, ( member(Par-Estado, Pares), analizar_caso(Par, [EA|_]),
                   EA \== Estado ), Distintos),
    resultado_prop('E5 analizar_caso/2 coincide con consultar_caso/2', NPares,
                   Distintos == [], P5),
    % E6: carga: lista de 600 hechos repetidos se resuelve sin error.
    findall(pantalla_negra, between(1, 600, _), Larga),
    statistics(cputime, T0),
    estado_de(Larga, EstadoLarga),
    statistics(cputime, T1), Seg is T1 - T0,
    format("        600 hechos repetidos: ~w en ~3f s~n", [EstadoLarga, Seg]),
    resultado_prop('E6 entrada larga resuelta sin error', 600,
                   ( EstadoLarga == datos_insuficientes, Seg < 5 ), P6),
    Props = [P1, P2, P3, P4, P5, P6],
    include(==(ok), Props, Oks),
    length(Oks, Pasan),
    length(Props, Total).

resultado_prop(Nombre, N, Condicion, R) :-
    (   call(Condicion) -> R = ok, Marca = 'OK  '
    ;   R = fallo, Marca = 'FALLO', assertz(fallo(Nombre))
    ),
    format("[~w] ~w (~d casos)~n", [Marca, Nombre, N]).
