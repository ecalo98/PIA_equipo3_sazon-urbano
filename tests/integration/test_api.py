"""Pruebas de la API REST con TestClient: éxito, 400, 401, 403, 404, 409 y 422, más el flujo completo de estados."""
import unittest

from fastapi.testclient import TestClient

from sazon_urbano.api.main import crear_app

MESERO = {"X-Usuario-Id": "ana", "X-Rol": "mesero"}
CAJA = {"X-Usuario-Id": "luis", "X-Rol": "caja"}
COCINA = {"X-Usuario-Id": "coc1", "X-Rol": "cocina"}
ENCARGADO = {"X-Usuario-Id": "eva", "X-Rol": "encargado"}
REPARTIDOR = {"X-Usuario-Id": "rep1", "X-Rol": "repartidor"}
CLIENTE_DOM = {"nombre": "Marta", "telefono": "8112345678", "direccion": "Calle 1 #100"}
MARTES_19H = "2026-10-13T19:00:00"
MIERCOLES_19H = "2026-10-14T19:00:00"


class ApiBase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(crear_app("sqlite://", sembrar=True))

    def pedido_mesa(self, items=None):
        r = self.client.post("/pedidos", headers=MESERO, json={
            "canal": "mesa", "mesa": "5", "items": items or [{"platillo_id": "taco-pastor", "cantidad": 2}, {"platillo_id": "refresco", "cantidad": 1}]})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["pedido_id"]

    def pedido_domicilio(self, items=None):
        r = self.client.post("/pedidos", headers=CAJA, json={
            "canal": "domicilio", "cliente": CLIENTE_DOM, "items": items or [{"platillo_id": "taco-pastor", "cantidad": 2}]})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["pedido_id"]

    def cocina_deja_listo(self, pedido_id, estacion="parrilla"):
        self.assertEqual(self.client.post(f"/pedidos/{pedido_id}/preparacion", headers=COCINA, json={"estacion": estacion}).status_code, 200)
        self.assertEqual(self.client.post(f"/pedidos/{pedido_id}/listo", headers=COCINA).status_code, 200)


class TestRegistrarPedido(ApiBase):
    def test_registra_y_calcula_el_total_con_el_precio_del_catalogo(self):  # 201
        r = self.client.post("/pedidos", headers=MESERO, json={
            "canal": "mesa", "mesa": "5", "items": [{"platillo_id": "taco-pastor", "cantidad": 2}, {"platillo_id": "refresco", "cantidad": 1}]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.json()["total"], r.json()["estado"]), ("210.00", "aceptado"))

    def test_el_resumen_expone_estado_responsable_y_acciones_permitidas(self):  # 200
        resumen = self.client.get(f"/pedidos/{self.pedido_mesa()}").json()
        self.assertEqual(resumen["estado"], "aceptado")
        self.assertEqual(resumen["responsable"], "ana (mesero)")                    # RN-14
        self.assertEqual(set(resumen["acciones_permitidas"]), {"iniciar_preparacion", "cancelar"})
        self.assertEqual(resumen["lineas"][0]["subtotal"], "180.00")

    def test_domicilio_menor_a_150_se_rechaza_rn01(self):  # 422
        r = self.client.post("/pedidos", headers=CAJA, json={"canal": "domicilio", "cliente": CLIENTE_DOM,
                                                              "items": [{"platillo_id": "agua", "cantidad": 1}]})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"], "MontoMinimoDomicilioNoAlcanzado")

    def test_domicilio_con_150_exactos_se_acepta(self):
        r = self.client.post("/pedidos", headers=CAJA, json={"canal": "domicilio", "cliente": CLIENTE_DOM,
                                                              "items": [{"platillo_id": "refresco", "cantidad": 5}]})  # 5 x 30 = 150
        self.assertEqual(r.status_code, 201)

    def test_domicilio_sin_cliente_se_rechaza(self):  # 422
        r = self.client.post("/pedidos", headers=CAJA, json={"canal": "domicilio", "items": [{"platillo_id": "taco-pastor", "cantidad": 2}]})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"], "DatosDeDomicilioIncompletos")

    def test_platillo_inexistente_404(self):
        r = self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "mesa": "1", "items": [{"platillo_id": "no-existe", "cantidad": 1}]})
        self.assertEqual((r.status_code, r.json()["error"]), (404, "PlatilloNoEncontrado"))

    def test_platillo_deshabilitado_422(self):  # PED-P011 viene deshabilitado en el paquete
        r = self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "mesa": "1", "items": [{"platillo_id": "PED-P011", "cantidad": 1}]})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "PlatilloNoDisponible"))

    def test_cantidad_mayor_al_stock_422(self):
        r = self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "mesa": "1", "items": [{"platillo_id": "postre-flan", "cantidad": 1}]})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "CantidadExcedeStock"))

    def test_cantidad_invalida_400(self):
        for cantidad in (0, -1, 100):
            r = self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "mesa": "1", "items": [{"platillo_id": "agua", "cantidad": cantidad}]})
            self.assertEqual((r.status_code, r.json()["error"]), (400, "SolicitudMalFormada"), cantidad)

    def test_pedido_sin_items_o_canal_invalido_400(self):
        self.assertEqual(self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "items": []}).status_code, 400)
        self.assertEqual(self.client.post("/pedidos", headers=MESERO, json={"canal": "volando", "items": [{"platillo_id": "agua", "cantidad": 1}]}).status_code, 400)

    def test_pedido_inexistente_404(self):
        self.assertEqual(self.client.get("/pedidos/no-existe").status_code, 404)


class TestIdentidadYPermisos(ApiBase):
    cuerpo = {"canal": "mesa", "mesa": "5", "items": [{"platillo_id": "agua", "cantidad": 1}]}

    def test_sin_identificar_401(self):
        self.assertEqual(self.client.post("/pedidos", json=self.cuerpo).status_code, 401)

    def test_rol_desconocido_400(self):
        r = self.client.post("/pedidos", json=self.cuerpo, headers={"X-Usuario-Id": "x", "X-Rol": "mago"})
        self.assertEqual((r.status_code, r.json()["error"]), (400, "RolInvalido"))

    def test_rol_sin_permiso_403_us19(self):
        r = self.client.post("/pedidos", json=self.cuerpo, headers=COCINA)        # cocina no captura pedidos
        self.assertEqual((r.status_code, r.json()["error"]), (403, "AccesoDenegado"))

    def test_mesero_no_registra_pedidos_a_domicilio_h01(self):
        r = self.client.post("/pedidos", headers=MESERO, json={"canal": "domicilio", "cliente": CLIENTE_DOM, "items": [{"platillo_id": "taco-pastor", "cantidad": 2}]})
        self.assertEqual(r.status_code, 403)

    def test_solo_caja_aplica_promociones_h01(self):
        pid = self.pedido_mesa()
        r = self.client.post(f"/pedidos/{pid}/promocion", headers=MESERO, json={"promocion_id": "promo-martes", "fecha_hora": MARTES_19H})
        self.assertEqual(r.status_code, 403)


class TestPromociones(ApiBase):
    def test_aplica_el_descuento_dentro_de_vigencia_rn05(self):  # 200
        pid = self.pedido_mesa()
        r = self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json={"promocion_id": "promo-martes", "fecha_hora": MARTES_19H})
        self.assertEqual((r.status_code, r.json()["total"]), (200, "174.00"))

    def test_fuera_de_vigencia_422(self):
        pid = self.pedido_mesa()
        r = self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json={"promocion_id": "promo-martes", "fecha_hora": MIERCOLES_19H})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "PromocionFueraDeVigencia"))

    def test_segunda_promocion_409_rn04(self):
        pid = self.pedido_mesa()
        cuerpo = {"promocion_id": "promo-martes", "fecha_hora": MARTES_19H}
        self.assertEqual(self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json=cuerpo).status_code, 200)
        r = self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json=cuerpo)
        self.assertEqual((r.status_code, r.json()["error"]), (409, "PedidoYaTienePromocion"))

    def test_promocion_que_no_aplica_a_los_productos_422(self):
        pid = self.pedido_mesa([{"platillo_id": "agua", "cantidad": 2}])
        r = self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json={"promocion_id": "promo-martes", "fecha_hora": MARTES_19H})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "PromocionNoAplicable"))

    def test_promocion_inexistente_404(self):
        pid = self.pedido_mesa()
        self.assertEqual(self.client.post(f"/pedidos/{pid}/promocion", headers=CAJA, json={"promocion_id": "x"}).status_code, 404)

    def test_el_sistema_nunca_la_aplica_sola_rn05(self):
        self.assertIsNone(self.client.get(f"/pedidos/{self.pedido_mesa()}").json()["promocion"])

    def test_promociones_vigentes_segun_la_fecha(self):
        self.assertEqual([p["id"] for p in self.client.get("/promociones/vigentes", params={"fecha_hora": MARTES_19H}).json()], ["promo-martes"])
        self.assertEqual(self.client.get("/promociones/vigentes", params={"fecha_hora": MIERCOLES_19H}).json(), [])


class TestCancelacion(ApiBase):
    def test_sin_preparacion_se_cancela_directo_rn02(self):  # 200
        pid = self.pedido_mesa()
        r = self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO, json={"motivo": "Error de captura"})
        self.assertEqual((r.status_code, r.json()["estado"], r.json()["genero_merma"]), (200, "cancelado", False))

    def test_con_preparacion_sin_autorizacion_409_rn03(self):
        pid = self.pedido_mesa()
        self.client.post(f"/pedidos/{pid}/preparacion", headers=COCINA, json={"estacion": "parrilla"})
        r = self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO, json={"motivo": "Se fue el cliente"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "CancelacionRequiereAutorizacion"))
        self.assertEqual(self.client.get(f"/pedidos/{pid}").json()["estado"], "en_preparacion")  # nada cambió

    def test_con_autorizacion_del_encargado_genera_merma_rn03(self):
        pid = self.pedido_mesa()
        self.client.post(f"/pedidos/{pid}/preparacion", headers=COCINA, json={"estacion": "parrilla"})
        r = self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO,
                             json={"motivo": "Se fue el cliente", "autorizador": {"usuario_id": "eva", "rol": "encargado"}})
        self.assertEqual((r.status_code, r.json()["estado"], r.json()["genero_merma"]), (200, "cancelado", True))

    def test_autorizador_que_no_es_encargado_403(self):
        pid = self.pedido_mesa()
        self.client.post(f"/pedidos/{pid}/preparacion", headers=COCINA, json={"estacion": "parrilla"})
        r = self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO,
                             json={"motivo": "Se fue el cliente", "autorizador": {"usuario_id": "ana", "rol": "mesero"}})
        self.assertEqual(r.status_code, 403)

    def test_un_pedido_cancelado_no_se_cancela_de_nuevo_409(self):
        pid = self.pedido_mesa()
        self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO, json={"motivo": "Error de captura"})
        r = self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO, json={"motivo": "Otra vez"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "TransicionDeEstadoInvalida"))

    def test_motivo_demasiado_corto_400(self):
        pid = self.pedido_mesa()
        self.assertEqual(self.client.post(f"/pedidos/{pid}/cancelacion", headers=MESERO, json={"motivo": "x"}).status_code, 400)


class TestMaquinaDeEstadosPorApi(ApiBase):
    def test_no_se_puede_saltar_un_estado_409(self):
        pid = self.pedido_mesa()
        r = self.client.post(f"/pedidos/{pid}/listo", headers=COCINA)             # ACEPTADO -> LISTO
        self.assertEqual((r.status_code, r.json()["error"]), (409, "TransicionDeEstadoInvalida"))
        self.assertIn("iniciar_preparacion", r.json()["mensaje"])
        self.assertEqual(self.client.get(f"/pedidos/{pid}").json()["estado"], "aceptado")

    def test_estacion_que_no_participa_422(self):
        pid = self.pedido_mesa([{"platillo_id": "taco-pastor", "cantidad": 1}])
        r = self.client.post(f"/pedidos/{pid}/preparacion", headers=COCINA, json={"estacion": "bebidas"})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "EstacionSinLineasEnElPedido"))

    def test_solo_cocina_mueve_la_preparacion_403(self):
        pid = self.pedido_mesa()
        self.assertEqual(self.client.post(f"/pedidos/{pid}/preparacion", headers=MESERO, json={"estacion": "parrilla"}).status_code, 403)

    def test_recorre_los_estados_y_el_resumen_los_refleja(self):
        pid = self.pedido_mesa([{"platillo_id": "taco-pastor", "cantidad": 1}])
        estados = [self.client.get(f"/pedidos/{pid}").json()["estado"]]
        self.client.post(f"/pedidos/{pid}/preparacion", headers=COCINA, json={"estacion": "parrilla"})
        estados.append(self.client.get(f"/pedidos/{pid}").json()["estado"])
        self.client.post(f"/pedidos/{pid}/listo", headers=COCINA)
        estados.append(self.client.get(f"/pedidos/{pid}").json()["estado"])
        self.assertEqual(estados, ["aceptado", "en_preparacion", "listo"])


class TestProductoAgotado(ApiBase):
    def test_marcar_agotado_actualiza_el_menu_y_bloquea_nuevos_pedidos(self):
        self.assertEqual(self.client.post("/productos/taco-pastor/agotado", headers=COCINA).status_code, 200)
        menu = {p["id"]: p["disponible"] for p in self.client.get("/menu").json()}
        self.assertFalse(menu["taco-pastor"])
        self.assertTrue(menu["refresco"])
        r = self.client.post("/pedidos", headers=MESERO, json={"canal": "mesa", "mesa": "1", "items": [{"platillo_id": "taco-pastor", "cantidad": 1}]})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "PlatilloNoDisponible"))

    def test_marcar_agotado_inexistente_404_y_solo_cocina_403(self):
        self.assertEqual(self.client.post("/productos/no-existe/agotado", headers=COCINA).status_code, 404)
        self.assertEqual(self.client.post("/productos/taco-pastor/agotado", headers=MESERO).status_code, 403)

    def test_quitar_solo_la_linea_agotada_sin_cancelar_el_pedido_rn06(self):
        pid = self.pedido_mesa()
        lineas = self.client.get(f"/pedidos/{pid}").json()["lineas"]
        taco = next(l for l in lineas if l["producto_id"] == "taco-pastor")
        self.client.post("/productos/taco-pastor/agotado", headers=COCINA)
        r = self.client.delete(f"/pedidos/{pid}/lineas/{taco['linea_id']}", headers=MESERO)
        self.assertEqual((r.status_code, r.json()["total"], r.json()["estado"]), (200, "30.00", "aceptado"))

    def test_no_se_quita_una_linea_de_un_producto_que_no_esta_agotado_409(self):
        pid = self.pedido_mesa()
        linea = self.client.get(f"/pedidos/{pid}").json()["lineas"][0]["linea_id"]
        r = self.client.delete(f"/pedidos/{pid}/lineas/{linea}", headers=MESERO)
        self.assertEqual((r.status_code, r.json()["error"]), (409, "ProductoNoEstaAgotado"))

    def test_linea_inexistente_404(self):
        pid = self.pedido_mesa()
        self.client.post("/productos/taco-pastor/agotado", headers=COCINA)
        self.assertEqual(self.client.delete(f"/pedidos/{pid}/lineas/zzz", headers=MESERO).status_code, 404)


class TestEntregas(ApiBase):
    def test_flujo_completo_asignar_salida_confirmacion_rn11(self):
        pid = self.pedido_domicilio()
        self.cocina_deja_listo(pid)
        r = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "rep-1"})
        self.assertEqual((r.status_code, r.json()["estado"]), (201, "asignada"))
        eid = r.json()["entrega_id"]
        self.assertEqual([x["id"] for x in self.client.get("/repartidores/disponibles").json()], ["rep-2"])
        self.assertEqual(self.client.post(f"/entregas/{eid}/salida", headers=REPARTIDOR).json()["estado"], "en_ruta")
        self.assertEqual(self.client.post(f"/entregas/{eid}/confirmacion", headers=REPARTIDOR).json()["estado"], "entregada")
        self.assertEqual(self.client.get(f"/pedidos/{pid}").json()["estado"], "entregado")
        self.assertEqual(len(self.client.get("/repartidores/disponibles").json()), 2)   # el repartidor se libera

    def test_no_se_entrega_sin_registrar_la_salida_409_rn11(self):
        pid = self.pedido_domicilio(); self.cocina_deja_listo(pid)
        eid = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "rep-1"}).json()["entrega_id"]
        r = self.client.post(f"/entregas/{eid}/confirmacion", headers=REPARTIDOR)
        self.assertEqual((r.status_code, r.json()["error"]), (409, "EntregaSinSalidaRegistrada"))

    def test_entrega_fallida_exige_motivo_y_deja_el_pedido_sin_completar(self):
        pid = self.pedido_domicilio(); self.cocina_deja_listo(pid)
        eid = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "rep-1"}).json()["entrega_id"]
        self.client.post(f"/entregas/{eid}/salida", headers=REPARTIDOR)
        self.assertEqual(self.client.post(f"/entregas/{eid}/fallida", headers=REPARTIDOR, json={}).status_code, 400)
        r = self.client.post(f"/entregas/{eid}/fallida", headers=REPARTIDOR, json={"motivo": "Cliente ausente"})
        self.assertEqual((r.status_code, r.json()["estado"]), (200, "fallida"))
        self.assertEqual(self.client.get(f"/pedidos/{pid}").json()["estado"], "entrega_no_completada")

    def test_pedido_que_no_esta_listo_409(self):
        pid = self.pedido_domicilio()
        r = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "rep-1"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "PedidoNoEstaListo"))

    def test_pedido_que_no_es_a_domicilio_422(self):
        pid = self.pedido_mesa([{"platillo_id": "taco-pastor", "cantidad": 1}]); self.cocina_deja_listo(pid)
        r = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "rep-1"})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "PedidoNoEsADomicilio"))

    def test_repartidor_no_disponible_409(self):
        p1 = self.pedido_domicilio(); self.cocina_deja_listo(p1)
        p2 = self.pedido_domicilio(); self.cocina_deja_listo(p2)
        self.assertEqual(self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": p1, "repartidor_id": "rep-1"}).status_code, 201)
        r = self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": p2, "repartidor_id": "rep-1"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "RepartidorNoDisponible"))

    def test_repartidor_o_entrega_inexistente_404_y_rol_sin_permiso_403(self):
        pid = self.pedido_domicilio(); self.cocina_deja_listo(pid)
        self.assertEqual(self.client.post("/entregas", headers=ENCARGADO, json={"pedido_id": pid, "repartidor_id": "zzz"}).status_code, 404)
        self.assertEqual(self.client.post("/entregas/zzz/salida", headers=REPARTIDOR).status_code, 404)
        self.assertEqual(self.client.post("/entregas", headers=CAJA, json={"pedido_id": pid, "repartidor_id": "rep-1"}).status_code, 403)


class TestPaquetePia(ApiBase):
    def test_operacion_valida(self):
        r = self.client.get("/operaciones/PED-O001/evaluacion").json()
        self.assertTrue(r["puede_procesarse"]); self.assertEqual(r["motivos_de_rechazo"], [])

    def test_operacion_vacia_inactiva_y_sin_autorizacion_con_motivos(self):
        vacia = self.client.get("/operaciones/PED-O013/evaluacion").json()
        self.assertEqual((vacia["puede_procesarse"], vacia["total"]), (False, "0"))
        self.assertIn("No cumple: al menos una línea de detalle", vacia["motivos_de_rechazo"])
        self.assertIn("No cumple: actor activo", self.client.get("/operaciones/PED-O029/evaluacion").json()["motivos_de_rechazo"])
        self.assertIn("No cumple: autorización registrada", self.client.get("/operaciones/PED-O008/evaluacion").json()["motivos_de_rechazo"])

    def test_operacion_inexistente_404(self):
        self.assertEqual(self.client.get("/operaciones/PED-O999/evaluacion").status_code, 404)

    def test_los_60_resultados_coinciden_con_las_specifications(self):
        validas = sum(self.client.get(f"/operaciones/PED-O{i:03d}/evaluacion").json()["puede_procesarse"] for i in range(1, 61))
        con_beneficio = sum(self.client.get(f"/operaciones/PED-O{i:03d}/evaluacion").json()["beneficio_referencia"] for i in range(1, 61))
        self.assertEqual((validas, con_beneficio), (47, 9))


class TestOpenApi(ApiBase):
    def test_openapi_y_swagger_ui_activos(self):
        esquema = self.client.get("/openapi.json").json()
        self.assertEqual(esquema["info"]["title"], "Sazón Urbano API")
        self.assertIn("/pedidos", esquema["paths"])
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/salud").json(), {"estado": "ok"})


if __name__ == "__main__":
    unittest.main()
