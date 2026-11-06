"""Ejecuta las 20 transiciones de prueba del paquete sobre la máquina de estados y deja evidencia.

Uso:  python scripts/ejecutar_transiciones.py
Genera evidencias/resultados_transiciones.csv (archivo NUEVO; transiciones_prueba.csv original no se toca).

Interpretación de las acciones sugeridas (supuesto E de docs/analisis/conciliacion-u2-paquete.md):
  aprobar            -> aprobar_operacion (puede_procesarse + CREADO -> ACEPTADO)
  repetir_aprobacion -> aprobar dos veces; la segunda debe rechazarse
  cancelar           -> CANCELAR desde CREADO (RN-02, sin autorización)
  saltar_estado      -> INICIAR_PREPARACION directo desde CREADO (se salta ACEPTADO)
  completar          -> ENTREGAR directo desde CREADO (se saltan todos los estados intermedios)
"""
import csv
import pathlib
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sazon_urbano.application.aprobacion import aprobar_operacion  # noqa: E402
from sazon_urbano.domain.errores import ErrorDeNegocio  # noqa: E402
from sazon_urbano.domain.pedido import AccionPedido, LineaPedido, MAQUINA_PEDIDO, Pedido  # noqa: E402
from sazon_urbano.domain.valores import Canal, Dinero, EstacionCocina, ProductoPedido, Responsable, Rol  # noqa: E402
from sazon_urbano.infrastructure.paquete_pia import PaquetePia  # noqa: E402

CAJA = Responsable("caja-1", Rol.CAJA)


def pedido_de(paquete: PaquetePia, operacion_id: str) -> Pedido:
    lineas = [
        LineaPedido(f"L{i}", ProductoPedido(d["recurso_id"], paquete.catalogo[d["recurso_id"]]["descripcion"],
                                            Dinero.mxn(paquete.catalogo[d["recurso_id"]]["precio_mxn"])),
                    int(d["cantidad"]), EstacionCocina.PARRILLA)
        for i, d in enumerate(paquete.detalle[operacion_id], start=1)
    ]
    return Pedido.crear(operacion_id, Canal.MESA, CAJA, lineas, mesa="1")


def ejecutar(paquete: PaquetePia, pedido: Pedido, op, accion: str) -> None:
    if accion == "aprobar":
        aprobar_operacion(pedido, op)
    elif accion == "repetir_aprobacion":
        aprobar_operacion(pedido, op)
        aprobar_operacion(pedido, op)  # la segunda debe fallar
    elif accion == "cancelar":
        pedido.cancelar(CAJA, "Cancelación de prueba")
    elif accion == "saltar_estado":
        pedido.iniciar_preparacion(EstacionCocina.PARRILLA)
    elif accion == "completar":
        pedido.marcar_entregado()
    else:
        raise ValueError(f"Acción desconocida: {accion}")


def main() -> None:
    paquete = PaquetePia()
    destino = RAIZ / "evidencias" / "resultados_transiciones.csv"
    resumen = Counter()
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["caso_id", "operacion_id", "accion", "estado_inicial", "estado_final", "resultado",
                    "eventos", "excepcion"])
        for t in paquete.transiciones:
            op = paquete.operaciones[t["operacion_id"]]
            pedido = pedido_de(paquete, op.operacion_id)
            excepcion = ""
            try:
                ejecutar(paquete, pedido, op, t["accion_sugerida"])
            except ErrorDeNegocio as e:
                excepcion = f"{type(e).__name__}: {e}"
            eventos = " | ".join(type(e).__name__ for e in pedido.recoger_eventos())
            resultado = "RECHAZADA" if excepcion else "EJECUTADA"
            w.writerow([t["caso_id"], op.operacion_id, t["accion_sugerida"], t["estado_inicial"],
                        pedido.estado.name, resultado, eventos, excepcion])
            resumen[(t["accion_sugerida"], resultado)] += 1
    for (accion, resultado), n in sorted(resumen.items()):
        print(f"{accion:20} {resultado:10} {n}")
    print(f"Evidencia: {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
