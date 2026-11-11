"""
preprocesamiento.py
===================
Pre-procesamiento numérico (componente híbrido opcional del Entregable 3).

Convierte lecturas continuas del equipo en hechos discretos que Prolog
entiende, antes de inyectarlos en la consulta:

    temperatura de CPU 97 °C   ->  dato(temperatura_cpu, critica)
    antigüedad 7 años          ->  dato(antiguedad, antiguo)
    12 horas de uso diario     ->  dato(horas_uso, intensivo)
    disco al 93 %              ->  dato(uso_disco, critico)

Por cada variable se entrena un ``DecisionTreeClassifier`` de scikit-learn con
el dataset sintético ``datos_preprocesamiento.csv`` incluido en el repositorio.
Si scikit-learn no está instalado se usa una heurística por umbrales que
produce las mismas etiquetas. Los umbrales coinciden con los de la base de
conocimiento (A.8): 85 °C de temperatura máxima, 95 °C crítica y 5 años de
antigüedad crítica.

Regenerar el dataset:  python preprocesamiento.py --generar
"""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass

RUTA_DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "datos_preprocesamiento.csv")

# variable -> (descripción, unidad, rango válido, [(límite inferior, nivel)])
# Un valor recibe el nivel del mayor límite inferior que alcanza.
VARIABLES = {
    "temperatura_cpu": ("Temperatura del procesador", "°C", (0, 150),
                        [(0, "normal"), (70, "elevada"), (86, "alta"), (95, "critica")]),
    "antiguedad": ("Antigüedad del equipo", "años", (0, 40),
                   [(0, "nuevo"), (2, "medio"), (5, "antiguo")]),
    "horas_uso": ("Horas de uso diario", "h", (0, 24),
                  [(0, "bajo"), (4, "moderado"), (10, "intensivo")]),
    "uso_disco": ("Ocupación del disco", "%", (0, 100),
                  [(0, "normal"), (75, "alto"), (90, "critico")]),
}


@dataclass
class HechoDiscreto:
    """Resultado de discretizar una lectura continua."""
    variable: str
    valor: float
    nivel: str
    metodo: str

    @property
    def termino(self) -> str:
        """Término que se envía a Prolog: ``dato(Variable, Nivel)``."""
        return f"dato({self.variable}, {self.nivel})"


def nivel_por_umbral(variable: str, valor: float) -> str:
    """Heurística por umbrales: también etiqueta el dataset sintético."""
    nivel = VARIABLES[variable][3][0][1]
    for limite, etiqueta in VARIABLES[variable][3]:
        if valor >= limite:
            nivel = etiqueta
    return nivel


def generar_dataset(ruta: str = RUTA_DATASET) -> None:
    """Escribe el dataset sintético (un registro por valor entero del rango)."""
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["variable", "valor", "nivel"])
        for variable, (_, _, (minimo, maximo), _) in VARIABLES.items():
            for valor in range(minimo, maximo + 1):
                escritor.writerow([variable, valor, nivel_por_umbral(variable, valor)])


class Preprocesador:
    """Clasificador ligero de lecturas continuas."""

    def __init__(self, ruta_dataset: str = RUTA_DATASET) -> None:
        self._modelos: dict = {}
        self.metodo = "umbrales"
        try:
            from sklearn.tree import DecisionTreeClassifier
        except ImportError:
            return
        if not os.path.isfile(ruta_dataset):
            return

        muestras: dict[str, tuple[list[list[float]], list[str]]] = {}
        with open(ruta_dataset, encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                x, y = muestras.setdefault(fila["variable"], ([], []))
                x.append([float(fila["valor"])])
                y.append(fila["nivel"])
        for variable, (x, y) in muestras.items():
            if variable in VARIABLES:
                modelo = DecisionTreeClassifier(max_depth=3, random_state=0)
                modelo.fit(x, y)
                self._modelos[variable] = modelo
        if self._modelos:
            self.metodo = "árbol de decisión (scikit-learn)"

    def clasificar(self, variable: str, valor: float) -> HechoDiscreto:
        if variable not in VARIABLES:
            raise ValueError(f"Variable desconocida: {variable}")
        minimo, maximo = VARIABLES[variable][2]
        if not minimo <= valor <= maximo:
            raise ValueError(
                f"{VARIABLES[variable][0]} fuera de rango ({minimo}-{maximo} {VARIABLES[variable][1]})."
            )
        modelo = self._modelos.get(variable)
        if modelo is not None:
            nivel = str(modelo.predict([[float(valor)]])[0])
            metodo = "árbol de decisión"
        else:
            nivel = nivel_por_umbral(variable, valor)
            metodo = "umbrales"
        return HechoDiscreto(variable, valor, nivel, metodo)

    def discretizar(self, **lecturas: float | None) -> list[HechoDiscreto]:
        """Clasifica las lecturas indicadas; ignora las que vengan en ``None``."""
        return [
            self.clasificar(variable, valor)
            for variable, valor in lecturas.items()
            if valor is not None
        ]


if __name__ == "__main__":
    if "--generar" in sys.argv:
        generar_dataset()
        print(f"Dataset escrito en {RUTA_DATASET}")
    else:
        preprocesador = Preprocesador()
        print(f"Método: {preprocesador.metodo}")
        for hecho in preprocesador.discretizar(temperatura_cpu=97, antiguedad=7,
                                               horas_uso=12, uso_disco=93):
            print(f"  {hecho.variable} = {hecho.valor} -> {hecho.termino}")
