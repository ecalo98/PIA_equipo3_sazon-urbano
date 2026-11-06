# BPMN complementario de Sazón Urbano

**Equipo:** 3 · **Curso:** Componentes de Lógica de Negocios (UANL, FIME) · **Fecha:** 05/11/2026

`BPMN_E3.pdf` se conserva **sin modificaciones** (regla de inmutabilidad de `conciliacion-u2-paquete.md`). Este documento y sus dos diagramas completan el proceso según el BRD y cierran los hallazgos **H-04** (conexiones sin unir) y **H-05** (sin promociones ni alertas) de la U3. Cuando el BPMN original y el BRD difieren, prevalece el BRD.

| Archivo | Contenido |
|---|---|
| `bpmn-complemento-proceso.puml` / `.png` | Proceso principal: captura por canal, producto agotado, monto mínimo, promoción, pago, preparación por estación, entrega y cierre |
| `bpmn-complemento-excepciones.puml` / `.png` | Cancelación (RN-02, RN-03), producto agotado en preparación (RN-06) y alertas automáticas (RN-07, RN-08, RN-15) |

Los diagramas están en PlantUML (diagrama de actividades con carriles), la misma herramienta de los diagramas de arquitectura. Para regenerarlos:

```bash
java -DPLANTUML_LIMIT_SIZE=20000 -jar plantuml.jar -tpng -charset UTF-8 docs/analisis/bpmn-complemento-*.puml
```

## Qué se corrigió respecto a `BPMN_E3.pdf`

| # | En el BPMN original | En el complemento | Base |
|---|---|---|---|
| 1 | Hay tareas sin conexión (por ejemplo, "Autorizar cancelación y registrar" no tiene entrada y "Preparar por estación" queda suelta) | Todas las tareas y decisiones quedan conectadas desde el inicio hasta un evento de fin | H-04 |
| 2 | Mesero y Caja aparecen como un solo carril ("Cajero / Caja") y no hay Mesero | Carriles separados: el Mesero captura en mesa; Caja captura los demás canales, cobra y aplica promociones | H-01, H-07 |
| 3 | El Cliente decide si "Confirma compra" y "Recibe producto" como tareas del sistema | El Cliente solo origina el pedido y decide si continúa; no interactúa con el sistema | H-02, BRD (stakeholders) |
| 4 | No hay promociones | Caja selecciona la promoción explícitamente; el sistema valida vigencia, productos y no acumulación, y la rechaza con motivo si no procede | RN-04, RN-05, NEC-05 · H-05 |
| 5 | No hay validación del monto mínimo | Domicilio menor a $150: se informa el faltante y se ofrece cambiar a "para llevar" | RN-01, NEC-12 |
| 6 | "Pedido cancelado con reembolso" | No existe en el BRD. La cancelación se registra con motivo y responsable; con preparación iniciada exige autorización del Encargado y genera merma | RN-02, RN-03, NEC-04 |
| 7 | "Asignar repartidor" está en el carril de Cocina | Lo hace el Encargado, según cercanía y disponibilidad; solo para pedidos a domicilio | BRD (stakeholders), NEC-06 |
| 8 | Todo pedido pasa por entrega a domicilio | Mesa y para llevar se entregan en el momento y cierran sin repartidor | BRD (canales) |
| 9 | Producto agotado solo notifica por inventario | Cocina lo marca, el sistema avisa de inmediato a mesero y caja, y se quita solo esa línea sin cancelar el pedido | RN-06, NEC-03 |
| 10 | No hay alertas | Tiempo meta de 18 / 25 min (RN-07), límite de 25 pedidos activos en hora pico (RN-08) y existencia mínima por insumo (RN-15) | NEC-02, NEC-07 · H-05 |
| 11 | El inventario se revisa solo al cierre | El inventario se actualiza con cada venta, merma o recepción | RN-13, NEC-01 |

## Relación con el sistema construido

El diagrama de proceso muestra el proceso del negocio completo. El sistema implementado cubre los 5 casos de uso aprobados en la U3: registrar pedido (RN-01, RN-14), aplicar promoción (RN-04, RN-05), cancelar (RN-02, RN-03), producto agotado (RN-06) y entrega (RN-11). Las alertas del diagrama 2/2 (RN-07, RN-08, RN-15) y el ajuste de inventario no están implementados; se documentan como alcance futuro en `docs/architecture/matriz-trazabilidad.md`, sección 7.
