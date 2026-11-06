"""Prueba de humo: arranca la API real y recorre los 5 casos de uso por HTTP. Uso: python scripts/prueba_humo_api.py (desde la raíz del repo)."""
import json, os, subprocess, sys, time, urllib.request, urllib.error
env = dict(os.environ, PYTHONPATH="src")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "--factory", "sazon_urbano.api.main:crear_app", "--port", "8766"],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = "http://127.0.0.1:8766"
def call(m, path, body=None, rol=None, uid=None):
    h = {"Content-Type": "application/json"}
    if rol: h.update({"X-Usuario-Id": uid or rol + "-01", "X-Rol": rol})
    req = urllib.request.Request(B + path, method=m, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        r = urllib.request.urlopen(req); return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")
def paso(n, esperado, res):
    ok = "OK " if res[0] == esperado else "FALLA"
    print(f"{ok} {n:<58} esperado {esperado} -> {res[0]}")
    return res[0] == esperado
try:
    for _ in range(40):
        try: urllib.request.urlopen(B + "/salud"); break
        except Exception: time.sleep(0.25)
    res = []
    res.append(paso("GET /salud", 200, call("GET", "/salud")))
    res.append(paso("GET /docs (Swagger UI)", 200, (urllib.request.urlopen(B + "/docs").status, None)))
    res.append(paso("GET /openapi.json", 200, call("GET", "/openapi.json")))
    res.append(paso("GET /menu", 200, call("GET", "/menu")))
    cli = {"nombre": "Ana", "telefono": "8100000001", "direccion": "Calle 1"}
    res.append(paso("CU-01 domicilio de $30 -> RN-01 rechaza", 422, call("POST", "/pedidos", {"canal": "domicilio", "items": [{"platillo_id": "refresco", "cantidad": 1}], "cliente": cli}, "caja")))
    res.append(paso("CU-01 mesero no registra domicilio (H-01)", 403, call("POST", "/pedidos", {"canal": "domicilio", "items": [{"platillo_id": "taco-pastor", "cantidad": 2}], "cliente": cli}, "mesero")))
    s, p = call("POST", "/pedidos", {"canal": "domicilio", "items": [{"platillo_id": "taco-pastor", "cantidad": 2}], "cliente": cli}, "caja")
    res.append(paso("CU-01 domicilio de $180 se confirma", 201, (s, p))); pid = p.get("id") or p.get("pedido_id")
    res.append(paso("GET resumen del pedido", 200, call("GET", f"/pedidos/{pid}")))
    res.append(paso("CU-02 promo-martes dentro de vigencia", 200, call("POST", f"/pedidos/{pid}/promocion", {"promocion_id": "promo-martes", "fecha_hora": "2026-11-03T19:00:00"}, "caja")))
    res.append(paso("CU-02 segunda promoción -> RN-04 rechaza", 409, call("POST", f"/pedidos/{pid}/promocion", {"promocion_id": "promo-martes", "fecha_hora": "2026-11-03T19:00:00"}, "caja")))
    res.append(paso("Cocina inicia preparación (parrilla)", 200, call("POST", f"/pedidos/{pid}/preparacion", {"estacion": "parrilla"}, "cocina")))
    res.append(paso("CU-03 cancelar con preparación sin Encargado", 409, call("POST", f"/pedidos/{pid}/cancelacion", {"motivo": "Cliente cambió de opinión"}, "mesero")))
    res.append(paso("CU-03 cancelar con Encargado -> merma (RN-03)", 200, call("POST", f"/pedidos/{pid}/cancelacion", {"motivo": "Cliente cambió de opinión", "autorizador": {"usuario_id": "eva", "rol": "encargado"}}, "mesero")))
    s, p2 = call("POST", "/pedidos", {"canal": "domicilio", "items": [{"platillo_id": "taco-pastor", "cantidad": 2}], "cliente": cli}, "caja"); pid2 = p2.get("id") or p2.get("pedido_id")
    for est in ("parrilla",):
        call("POST", f"/pedidos/{pid2}/preparacion", {"estacion": est}, "cocina")
    res.append(paso("Cocina marca el pedido listo", 200, call("POST", f"/pedidos/{pid2}/listo", None, "cocina")))
    s, reps = call("GET", "/repartidores/disponibles"); rid = reps[0]["id"]
    s, ent = call("POST", "/entregas", {"pedido_id": pid2, "repartidor_id": rid}, "encargado"); eid = ent.get("id") or ent.get("entrega_id")
    res.append(paso("CU-05 asignar repartidor", 201, (s, ent)))
    res.append(paso("CU-05 confirmar sin salida -> RN-11 rechaza", 409, call("POST", f"/entregas/{eid}/confirmacion", None, "repartidor")))
    res.append(paso("CU-05 registrar salida", 200, call("POST", f"/entregas/{eid}/salida", None, "repartidor")))
    res.append(paso("CU-05 confirmar entrega", 200, call("POST", f"/entregas/{eid}/confirmacion", None, "repartidor")))
    res.append(paso("CU-04a cocina marca producto agotado", 200, call("POST", "/productos/ensalada-casa/agotado", None, "cocina")))
    res.append(paso("GET evaluación de operación del paquete PIA", 200, call("GET", "/operaciones/PED-O001/evaluacion")))
    print(f"\n{sum(res)}/{len(res)} pasos correctos")
finally:
    srv.terminate(); srv.wait()
