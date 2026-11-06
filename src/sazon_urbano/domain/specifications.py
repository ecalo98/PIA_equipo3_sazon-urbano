"""Patrón Specification: reglas de negocio pequeñas, con nombre propio y combinables.

Cada Specification responde una pregunta de sí/no sobre un candidato (`es_satisfecha_por`).
Se combinan con AND (`&`), OR (`|`) y NOT (`~`) sin escribir condicionales anidados.

Trazabilidad:
- MontoMinimoDomicilio ........ RN-01, NEC-12, US-03
- PromocionActiva ............. RN-04, RN-05 (una sola promoción, elegida explícitamente)
- Autorizado .................. RN-03, RN-10 (alcance acotado, ver docs/analisis D-03)
- ActorActivo ................. regla adicional del paquete del PIA (D-04)
- ActorPreferente + TotalMinimo → `beneficio_referencia`: solo ELEGIBILIDAD, nunca descuento (D-02)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .valores import Canal, Dinero


class Specification(ABC):
    """Contrato común. Las subclases solo implementan `es_satisfecha_por` y `descripcion`."""

    @abstractmethod
    def es_satisfecha_por(self, candidato) -> bool: ...

    @property
    @abstractmethod
    def descripcion(self) -> str: ...

    # -- combinadores ---------------------------------------------------------
    def y(self, otra: "Specification") -> "Specification":
        return YSpecification(self, otra)

    def o(self, otra: "Specification") -> "Specification":
        return OSpecification(self, otra)

    def no(self) -> "Specification":
        return NoSpecification(self)

    __and__ = y
    __or__ = o
    __invert__ = no

    # -- explicación (para respuestas 422 de la API y para evidencias de prueba) ---
    def motivos_de_rechazo(self, candidato) -> list[str]:
        """Lista vacía si se cumple; si no, las condiciones concretas que fallaron."""
        return [] if self.es_satisfecha_por(candidato) else [f"No cumple: {self.descripcion}"]

    def __repr__(self) -> str:
        return f"<{self.descripcion}>"


# -- combinadores -------------------------------------------------------------
class YSpecification(Specification):
    def __init__(self, izquierda: Specification, derecha: Specification):
        self._izq, self._der = izquierda, derecha

    def es_satisfecha_por(self, candidato) -> bool:
        return self._izq.es_satisfecha_por(candidato) and self._der.es_satisfecha_por(candidato)

    @property
    def descripcion(self) -> str:
        return f"({self._izq.descripcion} Y {self._der.descripcion})"

    def motivos_de_rechazo(self, candidato) -> list[str]:
        return self._izq.motivos_de_rechazo(candidato) + self._der.motivos_de_rechazo(candidato)


class OSpecification(Specification):
    def __init__(self, izquierda: Specification, derecha: Specification):
        self._izq, self._der = izquierda, derecha

    def es_satisfecha_por(self, candidato) -> bool:
        return self._izq.es_satisfecha_por(candidato) or self._der.es_satisfecha_por(candidato)

    @property
    def descripcion(self) -> str:
        return f"({self._izq.descripcion} O {self._der.descripcion})"

    def motivos_de_rechazo(self, candidato) -> list[str]:
        if self.es_satisfecha_por(candidato):
            return []
        return [f"No cumple ninguna alternativa: {self.descripcion}"]


class NoSpecification(Specification):
    def __init__(self, interna: Specification):
        self._interna = interna

    def es_satisfecha_por(self, candidato) -> bool:
        return not self._interna.es_satisfecha_por(candidato)

    @property
    def descripcion(self) -> str:
        return f"NO {self._interna.descripcion}"

    def motivos_de_rechazo(self, candidato) -> list[str]:
        return [] if self.es_satisfecha_por(candidato) else [f"Se cumple lo que no debía: {self._interna.descripcion}"]


# -- Specifications concretas -------------------------------------------------
class ActorActivo(Specification):
    descripcion = "actor activo"

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.actor_activo


class ActorPreferente(Specification):
    descripcion = "actor preferente"

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.actor_preferente


class TieneLineas(Specification):
    descripcion = "al menos una línea de detalle"

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.num_lineas >= 1


class Autorizado(Specification):
    descripcion = "autorización registrada"

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.autorizado


class PromocionActiva(Specification):
    descripcion = "promoción activa"

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.promocion_activa


class TotalMinimo(Specification):
    def __init__(self, minimo: Dinero):
        self._minimo = minimo

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.total >= self._minimo

    @property
    def descripcion(self) -> str:
        return f"total >= {self._minimo.monto} {self._minimo.moneda}"


class MontoMinimoDomicilio(Specification):
    """RN-01. Solo exige el mínimo cuando el canal es domicilio; los demás canales pasan."""

    def __init__(self, minimo: Dinero):
        self._minimo = minimo

    def es_satisfecha_por(self, candidato) -> bool:
        return candidato.canal is not Canal.DOMICILIO or candidato.total >= self._minimo

    @property
    def descripcion(self) -> str:
        return f"domicilio con total >= {self._minimo.monto} {self._minimo.moneda}"


# -- reglas del paquete del PIA, armadas con las piezas anteriores ------------
def puede_procesarse() -> Specification:
    """actor activo AND operación con al menos una línea AND autorización."""
    return ActorActivo() & TieneLineas() & Autorizado()


def beneficio_referencia(minimo: Dinero = Dinero.mxn(1500)) -> Specification:
    """actor preferente AND total >= 1500 MXN AND NOT promoción activa.

    Solo evalúa ELEGIBILIDAD. No aplica descuentos (RN-05): aplicar una promoción sigue siendo
    una acción explícita de Caja (CU-02).
    """
    return ActorPreferente() & TotalMinimo(minimo) & ~PromocionActiva()
