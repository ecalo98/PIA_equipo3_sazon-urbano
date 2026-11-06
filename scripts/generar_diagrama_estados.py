"""Genera el diagrama de estados del Pedido a partir de la MISMA tabla que usa el código.

Uso:  python scripts/generar_diagrama_estados.py
Escribe docs/architecture/diagramas/estados-pedido.puml (y .png si `dot` está instalado).
"""
import pathlib
import shutil
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sazon_urbano.domain.pedido import EstadoPedido, MAQUINA_PEDIDO  # noqa: E402

DESTINO = RAIZ / "docs" / "architecture" / "diagramas"


def contenido_puml() -> str:
    return MAQUINA_PEDIDO.a_plantuml(EstadoPedido.CREADO)


def contenido_dot() -> str:
    lineas = ['digraph pedido {', '  rankdir=LR; labelloc=t; label="Máquina de estados: Pedido";',
              '  node [shape=box, style="rounded,filled", fillcolor="#E1F5EE", fontname="Arial"];',
              '  edge [fontname="Arial", fontsize=10];', '  inicio [shape=circle, label="", width=0.2, style=filled, fillcolor=black];',
              f'  inicio -> {EstadoPedido.CREADO.name};']
    for o, a, d in MAQUINA_PEDIDO.transiciones():
        lineas.append(f'  {o.name} -> {d.name} [label="{a.value}"];')
    for e in EstadoPedido:
        if MAQUINA_PEDIDO.es_final(e):
            lineas.append(f'  {e.name} [fillcolor="#F1EFE8", peripheries=2];')
    lineas.append("}")
    return "\n".join(lineas) + "\n"


def main() -> None:
    (DESTINO / "estados-pedido.puml").write_text(contenido_puml(), encoding="utf-8")
    if shutil.which("dot"):
        subprocess.run(["dot", "-Tpng", "-o", str(DESTINO / "estados-pedido.png")], input=contenido_dot().encode("utf-8"), check=True)
    print("Diagrama de estados generado en", DESTINO.relative_to(RAIZ))


if __name__ == "__main__":
    main()
