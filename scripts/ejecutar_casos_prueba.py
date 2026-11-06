"""Ejecuta los 120 casos de prueba del paquete con las Specifications y deja evidencia.

Uso:  python scripts/ejecutar_casos_prueba.py
Genera evidencias/resultados_casos_prueba.csv (archivo NUEVO; casos_prueba.csv original no se toca).
"""
import csv
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sazon_urbano.domain.specifications import beneficio_referencia, puede_procesarse  # noqa: E402
from sazon_urbano.infrastructure.paquete_pia import PaquetePia  # noqa: E402

REGLAS = {"validar_operacion": puede_procesarse(), "evaluar_beneficio": beneficio_referencia()}


def main() -> None:
    paquete = PaquetePia()
    destino = RAIZ / "evidencias" / "resultados_casos_prueba.csv"
    resumen = {}
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["caso_id", "operacion_id", "tipo_prueba", "regla", "resultado", "motivos_de_rechazo"])
        for caso in paquete.casos_prueba:
            regla = REGLAS[caso["tipo_prueba"]]
            op = paquete.operaciones[caso["operacion_id"]]
            ok = regla.es_satisfecha_por(op)
            motivos = "; ".join(regla.motivos_de_rechazo(op))
            w.writerow([caso["caso_id"], op.operacion_id, caso["tipo_prueba"], regla.descripcion,
                        "CUMPLE" if ok else "NO_CUMPLE", motivos])
            clave = (caso["tipo_prueba"], ok)
            resumen[clave] = resumen.get(clave, 0) + 1
    for (tipo, ok), n in sorted(resumen.items()):
        print(f"{tipo:18} {'CUMPLE' if ok else 'NO_CUMPLE':10} {n}")
    print(f"Evidencia: {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
