"""Aprobar una operación = comprobar la Specification `puede_procesarse` y luego aceptar el pedido.

Une dos piezas del dominio: la regla combinable (Specification) y la transición CREADO -> ACEPTADO
(máquina de estados). La capa API (Paso 6) usará esta misma función.
"""
from sazon_urbano.domain.errores import OperacionNoProcesable
from sazon_urbano.domain.evaluacion import OperacionEvaluable
from sazon_urbano.domain.pedido import Pedido
from sazon_urbano.domain.specifications import Specification, puede_procesarse


def aprobar_operacion(pedido: Pedido, operacion: OperacionEvaluable, regla: Specification | None = None) -> None:
    regla = regla or puede_procesarse()
    motivos = regla.motivos_de_rechazo(operacion)
    if motivos:
        raise OperacionNoProcesable(motivos)
    pedido.confirmar()
