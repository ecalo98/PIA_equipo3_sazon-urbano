"""Operación evaluable: foto de solo lectura de lo que las Specifications necesitan saber.

Las Specifications no deciden sobre el aggregate Pedido completo, sino sobre este Value Object.
Así las mismas reglas sirven para los datos del paquete del PIA y para un Pedido real
(ambos exponen `canal` y `total`).
"""
from __future__ import annotations

from dataclasses import dataclass

from .valores import Canal, Dinero


@dataclass(frozen=True)
class OperacionEvaluable:
    operacion_id: str
    actor_activo: bool
    actor_preferente: bool
    num_lineas: int
    total: Dinero
    autorizado: bool
    promocion_activa: bool
    canal: Canal | None = None  # los CSV del paquete no traen canal (ver docs/analisis, D-06)
