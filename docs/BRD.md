# BRD – Business Requirements Document

> **Conversión a Markdown de [`docs/BRD/BRD_E3.pdf`](BRD/BRD_E3.pdf).** El contenido es el de la Unidad 2, sin cambios;
> el PDF original se conserva intacto. Los ajustes y diferencias posteriores se documentan aparte en
> [`docs/analisis/conciliacion-u2-paquete.md`](analisis/conciliacion-u2-paquete.md).

**Universidad Autónoma de Nuevo León · Facultad de Ingeniería Mecánica Eléctrica**

**Componentes de lógica de negocio · BRD-Business Requirements Document**

- **Docente:** Miguel Ángel Gómez Marroquín
- **Hora:** M4
- **Grupo:** 004
- **Semestre:** Agosto-Diciembre 2026
- **Equipo:** 3

| Nombre | Matrícula | Carrera |
|---|---|---|
| Edgar Daniel del Ángel Hernández | 2094613 | ITS |
| Emmanuel Carrillo Loera | 2067988 | ITS |
| Fatima Alejandra Cavazos Serrato | 2099488 | ITS |

---

## BRD-Business Requirements Document

### Caso: Sazon Urbano

Sazón Urbano es un restaurante que ofrece servicio en mesa, para llevar y entrega a domicilio. Sus ingresos provienen de la venta de alimentos, bebidas, paquetes y complementos. La operación diaria depende de la coordinación entre cocina, caja, meseros y repartidores, quienes en conjunto procesan pedidos capturados por distintos canales (mesa, teléfono, WhatsApp y servicio a domicilio).

Actualmente, el pedido del cliente pasa por estaciones de parrilla, preparación fría, bebidas y empaque. Se entrega al cliente o al repartidor una vez que todas las partes están terminadas.

Los ingredientes tienen existencias limitadas y algunos son críticos para determinados platillos. El inventario solo se revisa al final del día.

### Problema / oportunidad

- Los productos agotados no se reflejan oportunamente, generando pedidos que no se pueden cumplir.
- Cocina recibe órdenes incompletas, lo que provoca retrabajo y demoras.
- Existen diferencias entre lo vendido y el inventario real, sin un mecanismo que las detecte a tiempo.
- No hay forma sistemática de rastrear modificaciones y cancelaciones de pedidos.

La oportunidad y objetivo consiste en dotar a Sazón Urbano de un proceso documentado y, eventualmente, de un sistema que capture datos en tiempo real, aplique las reglas de negocio de forma consistente y genere los reportes que la gerencia necesita para tomar decisiones.

### Stakeholders

| Actor | Participación en el proceso |
|---|---|
| Cliente | Origina el pedido por cualquier canal (mesa, teléfono/WhatsApp o servicio a domicilio) y es el destinatario final del producto; no interactúa directamente con el sistema interno. |
| Mesero | Captura los pedidos del cliente, informa sobre productos disponibles o agotados, aplica promociones vigentes y puede modificar o cancelar pedidos antes de que inicie su preparación. |
| Caja | Recibe el pedido para realizar el cobro, verifica el total y las promociones aplicadas, procesa el pago y confirma la compra. |
| Cocina | Recibe el pedido por estación (parrilla, fría, bebidas, empaque), lo prepara, y marca productos o insumos como agotados en tiempo real. |
| Encargado | Autoriza cancelaciones posteriores al inicio de preparación, ajusta el inventario manualmente, asigna repartidores y revisa el reporte de discrepancias. |
| Repartidor | Recibe la asignación de pedidos a domicilio, realiza la entrega y registra hora de salida, hora de entrega o motivo de entrega fallida. |
| Gerente | Define precios y condiciones de promociones, y da seguimiento a los reportes e indicadores del negocio para la toma de decisiones. |

### Alcance del proyecto

#### Dentro del alcance

- Captura de pedidos por los tres canales: mesa, teléfono/WhatsApp y domicilio.
- Gestión del pedido por estaciones de cocina (parrilla, preparación fría, bebidas, empaque).
- Gestión de inventario en tiempo real, con alertas de existencia mínima.
- Gestión de modificaciones y cancelaciones de pedidos, con trazabilidad de motivo y responsable.
- Gestión de promociones con vigencia, condiciones y no acumulación.
- Asignación y seguimiento de repartidores para pedidos a domicilio.
- Generación de reportes e indicadores: ventas, mermas, discrepancias, cancelaciones y desempeño de repartidores.
- Control de permisos diferenciado por rol.

#### Fuera del alcance

- Integración con plataformas externas de delivery (por ejemplo, apps de terceros para pedidos).
- Gestión de nómina o pagos al personal.
- Programas de lealtad o puntos para clientes.
- Facturación electrónica fiscal detallada; solo se contempla el ticket o comprobante de venta.
- Gestión avanzada de proveedores (licitaciones, contratos, compras programadas).
- Aplicación propia para que el cliente ordene directamente (los pedidos se siguen capturando vía mesero, teléfono o WhatsApp).

### Necesidades

| ID | Descripción de la necesidad |
|---|---|
| NEC-01 | Actualizar el inventario en tiempo real con cada movimiento (venta, merma, recepción de insumos), no solo al cierre del día. |
| NEC-02 | Generar alertas automáticas cuando la existencia de un insumo llegue a su nivel mínimo configurado. |
| NEC-03 | Permitir marcar un producto o ingrediente como agotado en el momento y notificarlo a mesero/caja. |
| NEC-04 | Registrar y dar trazabilidad a toda modificación o cancelación de pedido, con motivo y responsable. |
| NEC-05 | Controlar la aplicación de promociones según vigencia (día/horario), productos y no acumulación. |
| NEC-06 | Asignar repartidores a pedidos a domicilio según cercanía y disponibilidad, con registro de tiempos. |
| NEC-07 | Alertar automáticamente cuando un pedido exceda el tiempo meta de preparación/entrega. |
| NEC-08 | Generar un reporte de discrepancias entre ventas registradas e inventario consumido. |
| NEC-09 | Generar reportes de ventas por canal y producto, mermas, cancelaciones y desempeño de repartidores. |
| NEC-10 | Definir permisos diferenciados por rol (Mesero/Caja, Cocina, Encargado, Gerente, Repartidor). |
| NEC-11 | Capturar de forma completa los datos de cada pedido (cliente, canal, productos, modificaciones, precio, responsable, horarios). |
| NEC-12 | Validar el monto mínimo de compra para pedidos a domicilio antes de confirmarlos. |

### Reglas de negocio

| ID | Descripción de la regla de negocio |
|---|---|
| RN-01 | Todo pedido a domicilio debe tener un monto mínimo de $150 MXN; si no se alcanza, solo procede como para llevar. |
| RN-02 | Un pedido puede cancelarse sin autorización especial únicamente si ninguna de sus estaciones ha iniciado la preparación. |
| RN-03 | La cancelación de un pedido con preparación ya iniciada requiere autorización del Encargado y genera un registro de merma. |
| RN-04 | Las promociones no son acumulables entre sí; solo puede aplicarse una por pedido. |
| RN-05 | Las promociones deben ser seleccionadas explícitamente por mesero/caja; el sistema nunca las aplica de forma automática. |
| RN-06 | Un producto agotado puede eliminarse de un pedido ya registrado sin necesidad de cancelar el pedido completo. |
| RN-07 | El tiempo meta de preparación es de 18 minutos para pedidos en mesa/para llevar y 25 minutos para domicilio (incluye entrega). |
| RN-08 | En horario pico (13:00–15:00 y 19:00–21:00) cocina admite un máximo de 25 pedidos activos simultáneos. |
| RN-09 | Únicamente el Gerente puede configurar precios y condiciones de promociones. |
| RN-10 | Únicamente el Encargado puede ajustar inventario manualmente y autorizar cancelaciones posteriores al inicio de preparación. |
| RN-11 | El repartidor debe registrar la hora de salida y la hora de entrega, o el motivo de una entrega fallida. |
| RN-12 | Toda modificación a un pedido ya enviado a cocina requiere que la estación correspondiente no haya iniciado esa preparación, salvo autorización del Encargado. |
| RN-13 | El inventario debe reflejar cada movimiento (venta, merma, recepción) en tiempo real, no únicamente al cierre del día. |
| RN-14 | Todo pedido debe registrar el responsable (mesero/caja) que lo capturó y el canal de origen. |
| RN-15 | Las alertas de existencia mínima se generan automáticamente por insumo al alcanzar el umbral configurado por el Encargado. |

### Restricciones

- La solución debe operar con la infraestructura de red e internet actual del restaurante, que puede presentar intermitencias.
- La implementación no debe interrumpir la operación diaria del restaurante.
- El presupuesto y los tiempos del proyecto son definidos por la gerencia y no se detallan cifras específicas en este caso.

### Supuestos

- El personal (meseros, cocina, encargado) cuenta con capacitación básica para el uso de sistemas de captura.
- Los repartidores utilizan su propio teléfono para registrar salidas y entregas.
- La conexión a internet del restaurante es estable la mayor parte del tiempo de operación.

### Criterios de éxito

- Reducir a cero, o casi cero, las discrepancias diarias entre ventas registradas e inventario consumido.
- Incrementar el porcentaje de pedidos que llegan completos a cocina desde el primer envío.
- Cumplir las metas de tiempo de preparación y entrega (18 minutos en mesa/para llevar, 25 minutos en domicilio).
- Lograr que el 100% de cancelaciones y modificaciones queden registradas con motivo y responsable.
