"""Verifica fixtures/operaciones_extra.csv (decisión C de docs/analisis/conciliacion-u2-paquete.md).

El archivo completa las 60 operaciones del paquete con canal y responsable (RN-14, H-01) y agrega casos propios
que ejercitan RN-01 y US-02, que los datos originales nunca ejercitan (todos los pedidos del paquete superan $150).
Los resultados esperados del CSV se comprueban contra el dominio real.
"""
import csv
import unittest
from decimal import Decimal
from pathlib import Path

from sazon_urbano.domain.errores import DatosDeDomicilioIncompletos, MontoMinimoDomicilioNoAlcanzado
from sazon_urbano.domain.pedido import LineaPedido, Pedido
from sazon_urbano.domain.valores import Canal, DatosCliente, Dinero, EstacionCocina, ProductoPedido, Responsable, Rol
from sazon_urbano.infrastructure.paquete_pia import PaquetePia

RAIZ = Path(__file__).resolve().parents[2] / "fixtures"


def _leer(nombre):
    with open(RAIZ / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


FILAS = _leer("operaciones_extra.csv")
MENU = {m["platillo_id"]: m for m in _leer("menu_sazon_urbano.csv")}


def _pedido(fila):
    lineas = []
    for i, par in enumerate(fila["lineas"].split(";")):
        platillo_id, cantidad = par.split(":")
        m = MENU[platillo_id]
        producto = ProductoPedido(platillo_id, m["nombre"], Dinero(Decimal(m["precio_mxn"])))
        lineas.append(LineaPedido(f"l{i}", producto, int(cantidad), EstacionCocina(m["estacion"])))
    canal = Canal(fila["canal"])
    cliente = DatosCliente(fila["cliente_nombre"], fila["telefono"], fila["direccion"])
    responsable = Responsable(fila["responsable_usuario"], Rol(fila["responsable_rol"]))
    return Pedido.crear(fila["operacion_id"], canal, responsable, lineas, cliente, fila["mesa"] or None)


class TestOperacionesExtra(unittest.TestCase):
    def test_cubre_las_60_operaciones_del_paquete_una_sola_vez(self):
        ids = [f["operacion_id"] for f in FILAS if f["tipo"] == "paquete"]
        self.assertEqual(len(ids), 60)
        self.assertEqual(set(ids), set(PaquetePia().operaciones))

    def test_mesero_solo_captura_en_mesa_y_caja_en_los_demas_canales_h01(self):
        for f in FILAS:
            esperado = "mesero" if f["canal"] == "mesa" else "caja"
            self.assertEqual(f["responsable_rol"], esperado, f["operacion_id"])

    def test_todo_pedido_trae_responsable_y_canal_rn14(self):
        for f in FILAS:
            self.assertTrue(f["responsable_usuario"], f["operacion_id"])
            self.assertIn(f["canal"], {c.value for c in Canal}, f["operacion_id"])

    def test_los_pedidos_a_domicilio_del_paquete_traen_telefono_y_direccion_us02(self):
        for f in FILAS:
            if f["tipo"] == "paquete" and f["canal"] == "domicilio":
                self.assertTrue(f["telefono"] and f["direccion"], f["operacion_id"])

    def test_los_casos_propios_se_comportan_como_dice_el_csv(self):
        extras = [f for f in FILAS if f["tipo"] != "paquete"]
        self.assertEqual(len(extras), 9)
        for f in extras:
            esperado = f["resultado_esperado"]
            with self.subTest(f["operacion_id"], descripcion=f["descripcion"]):
                if esperado == "rechazado_datos_domicilio":
                    with self.assertRaises(DatosDeDomicilioIncompletos):
                        _pedido(f)
                    continue
                pedido = _pedido(f)
                if esperado == "rechazado_monto_minimo":
                    with self.assertRaises(MontoMinimoDomicilioNoAlcanzado):
                        pedido.confirmar()
                else:
                    pedido.confirmar()
                    self.assertEqual(pedido.estado.value, "aceptado")

    def test_los_casos_propios_cubren_el_limite_exacto_de_150(self):
        limite = next(f for f in FILAS if f["operacion_id"] == "EXTRA-RN01-04")
        self.assertEqual(_pedido(limite).total, Dinero.mxn(150))


if __name__ == "__main__":
    unittest.main()
