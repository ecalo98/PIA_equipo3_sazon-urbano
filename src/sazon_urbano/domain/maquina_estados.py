"""Máquina de estados genérica: una tabla (estado, acción) -> estado nuevo.

Toda transición válida está escrita en una sola tabla; cualquier otra se rechaza con
`TransicionDeEstadoInvalida`. Así no hay `if estado == ...` regados por el dominio y el diagrama de estados
se genera de la misma tabla que usa el código.
"""
from __future__ import annotations

from enum import Enum

from .errores import TransicionDeEstadoInvalida


class MaquinaDeEstados:
    def __init__(self, nombre: str, transiciones: dict):
        self.nombre = nombre
        self._transiciones = dict(transiciones)

    def acciones_permitidas(self, estado: Enum) -> list:
        return [accion for (origen, accion) in self._transiciones if origen is estado]

    def puede(self, estado: Enum, accion: Enum) -> bool:
        return (estado, accion) in self._transiciones

    def transicionar(self, estado: Enum, accion: Enum) -> Enum:
        """Devuelve el estado nuevo o lanza TransicionDeEstadoInvalida."""
        try:
            return self._transiciones[(estado, accion)]
        except KeyError:
            raise TransicionDeEstadoInvalida(estado, accion, self.acciones_permitidas(estado)) from None

    def es_final(self, estado: Enum) -> bool:
        return not self.acciones_permitidas(estado)

    def transiciones(self) -> list:
        """Lista (origen, accion, destino), en el orden en que se definieron."""
        return [(o, a, d) for (o, a), d in self._transiciones.items()]

    def a_plantuml(self, estado_inicial: Enum) -> str:
        lineas = [f"@startuml estados-{self.nombre}", f"title Máquina de estados: {self.nombre}",
                  "skinparam shadowing false", f"[*] --> {estado_inicial.name}"]
        for origen, accion, destino in self.transiciones():
            lineas.append(f"{origen.name} --> {destino.name} : {accion.value}")
        for estado in dict.fromkeys(d for _, _, d in self.transiciones()):
            if self.es_final(estado):
                lineas.append(f"{estado.name} --> [*]")
        lineas.append("@enduml")
        return "\n".join(lineas) + "\n"
