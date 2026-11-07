# Conciliación entre los artefactos de U2/U3 y el paquete de datos del PIA

**Proyecto:** Sazón Urbano · **Equipo:** 3 · **Curso:** Componentes de Lógica de Negocios (UANL, FIME)
**Ubicación en el repositorio:** `docs/analisis/conciliacion-u2-paquete.md`
**Fecha:** 02/11/2026

## 1. Propósito y regla de trabajo

El paquete de datos del PIA (`datos.zip`, `LEEME.txt`, `INSTRUCCIONES_ALUMNO.txt`) declara que sus reglas, estados e importes son un **modelo de pruebas propuesto** y que no deben reemplazar los requerimientos propios del equipo. Pide documentar las diferencias y adaptar fixtures y oráculos.

Este documento cumple ese requisito. Compara el paquete con el BRD, las user stories, el glosario, el BPMN y el reporte de la U3, y fija cómo se tratará cada diferencia.

**Regla de inmutabilidad.** Los siguientes archivos **no se modifican**; se usan tal como fueron entregados:

- U1/U2: `BRD_E3.pdf`, `User_stories_y_criterios_de_aceptación_E3.pdf`, `Glosario_de_Dominio_E3.pdf`, `BPMN_E3.pdf`.
- U3: `Reporte.pdf` y el repositorio base.
- Paquete: los 6 CSV (`actores`, `catalogo`, `operaciones`, `detalle_operaciones`, `casos_prueba`, `transiciones_prueba`).

Todo ajuste vive en archivos **nuevos**: este documento, `fixtures/` propios y el código. Los CSV se leen, nunca se editan.

**Fuente de verdad.** Si el paquete y el BRD difieren, prevalece el BRD. El paquete se usa como conjunto de datos y casos de prueba.

## 2. Perfil de los datos del paquete

Cifras obtenidas al leer los CSV originales (sin modificarlos):

| Elemento | Cantidad / observación |
|---|---|
| Actores | 40 (20 en Monterrey, 20 en Apodaca); 8 preferentes; 5 inactivos |
| Platillos (catálogo) | 20; precios de 290.00 a 1,639.00 MXN; stock mínimo 10; 1 deshabilitado (`PED-P011`) |
| Operaciones | 60, todas en estado `CREADO` |
| Líneas de detalle | 117; cantidades de 1 a 4; ninguna excede el stock |
| Operaciones sin líneas | 2 (`PED-O013`, `PED-O039`) |
| Operaciones con actor inactivo | 5 (`PED-O029` a `PED-O033`) |
| Operaciones no autorizadas | 7 (`PED-O008`, `016`, `024`, `032`, `040`, `048`, `056`) |
| Operaciones con promoción activa | 6 (`PED-O009`, `018`, `027`, `036`, `045`, `054`) |
| Operaciones con total ≥ 1,500 MXN | 52 |
| Operaciones que cumplen `beneficio_referencia` | 9 |
| Líneas con platillo deshabilitado | 6 (en `PED-O005`, `015`, `020`, `035`, `040`, `055`) |
| Casos de prueba | 120: 60 `validar_operacion` y 60 `evaluar_beneficio` |
| Transiciones de prueba | 20: 4 de cada acción (aprobar, completar, cancelar, repetir_aprobacion, saltar_estado) |

Los datos incluyen casos límite útiles: pedidos vacíos, actores inactivos, un actor preferente e inactivo (`PED-C035`), un platillo deshabilitado y pedidos sin autorización. Se aprovechan en las pruebas.

## 3. Diferencias encontradas y tratamiento

### D-01. El actor del paquete es el comensal; en el BRD el Cliente no usa el sistema

| | |
|---|---|
| **Paquete** | Actor = comensal, con `es_preferente` y `activo`. |
| **U2/U3** | El Cliente origina el pedido pero no interactúa con el sistema (BRD, stakeholders). Capturan Mesero (solo mesa) y Caja (demás canales); son roles distintos (H-01, H-07). El Cliente aparece en US-19 con permisos vacíos (H-02). |
| **Tratamiento** | El comensal se modela como **dato del pedido**, no como usuario de la API. Los usuarios de la API son Mesero, Caja, Cocina, Encargado, Repartidor y Gerente. |
| **Estado** | Supuesto a validar (hereda H-01). |

### D-02. `beneficio_referencia` roza un tema fuera de alcance

| | |
|---|---|
| **Paquete** | Regla: actor preferente AND total ≥ 1,500 MXN AND NOT promoción activa. |
| **U2/U3** | Los programas de lealtad o puntos están **fuera de alcance** (BRD). RN-05: el sistema nunca aplica promociones automáticamente. RN-04: una sola promoción por pedido. |
| **Tratamiento (decisión A)** | `beneficio_referencia` se implementa **solo como evaluación de elegibilidad**: una Specification que devuelve verdadero o falso. **No aplica descuentos ni modifica el total.** Aplicar una promoción sigue siendo una acción explícita de Caja (CU-02). |
| **Estado** | Decidido por el equipo. Es una desviación documentada. |

### D-03. La "autorización" del paquete es genérica; en el BRD es del Encargado y es específica

| | |
|---|---|
| **Paquete** | `puede_procesarse`: actor activo AND al menos una línea AND autorización (campo `autorizado`). |
| **U2/U3** | La autorización del Encargado solo se exige para cancelar con preparación iniciada (RN-03, RN-10, US-07) y para modificar una línea ya iniciada (RN-12). El mecanismo es un supuesto abierto (H-10). |
| **Tratamiento** | `autorizado` se interpreta como la **autorización previa requerida para procesar** el pedido dentro del modelo de pruebas. Se documenta como regla adicional del paquete y no sustituye RN-03 ni RN-10. |
| **Estado** | Supuesto a validar. |

### D-04. La precondición "cliente activo" no existe en el BRD

| | |
|---|---|
| **Paquete** | Un actor inactivo no puede procesarse (5 operaciones afectadas). |
| **U2/U3** | El BRD no define clientes activos o inactivos; el cliente no usa el sistema. |
| **Tratamiento** | Se conserva como **regla adicional del paquete** (Specification `ActorActivo`) para poder ejecutar los 120 casos. Se registra como regla sin respaldo en el BRD. |
| **Estado** | Regla adicional, documentada. |

### D-05. Modelo de estados distinto

| Paquete | Reporte U3 (derivado del BPMN, H-12) | Estado en el diseño final |
|---|---|---|
| `CREADO` | Capturado | `CREADO` |
| `ACEPTADO` | Confirmado | `ACEPTADO` |
| `EN_PREPARACION` | En preparación | `EN_PREPARACION` |
| (no existe) | Listo | **`LISTO`** (se agrega) |
| `ENTREGADO` | Entregado | `ENTREGADO` |
| `CANCELADO` | Cancelado | `CANCELADO` |
| (no existe) | Entrega no completada | **`ENTREGA_NO_COMPLETADA`** (se agrega) |

**Tratamiento (decisión B).** El diseño final usa el **superconjunto** de ambos modelos. Los nombres del paquete se conservan para que las pruebas de transición sean comparables. `LISTO` y `ENTREGA_NO_COMPLETADA` existen porque el BRD y el BPMN los exigen (RN-11, CU-05).

**Transiciones válidas (implementadas en `MAQUINA_PEDIDO`, ver ADR-05):**

- `CREADO → ACEPTADO → EN_PREPARACION → LISTO → ENTREGADO`
- `LISTO → ENTREGA_NO_COMPLETADA` (solo domicilio)
- `CREADO → CANCELADO` sin autorización (RN-02)
- `ACEPTADO → CANCELADO` sin autorización mientras ninguna estación haya iniciado (RN-02)
- `EN_PREPARACION` o `LISTO → CANCELADO` con autorización del Encargado y generación de merma (RN-03)

**Interpretación de las 20 transiciones de prueba** (todas parten de `CREADO`):

| Acción sugerida | Resultado esperado según este modelo |
|---|---|
| `aprobar` | `CREADO → ACEPTADO`, evento de dominio |
| `cancelar` | `CREADO → CANCELADO` sin autorización |
| `repetir_aprobacion` | Primera aprobación válida; la segunda se rechaza por transición inválida |
| `saltar_estado` | Rechazo por transición inválida |
| `completar` | Rechazo si se intenta desde `CREADO` sin pasar por los estados intermedios |

El paquete no incluye el resultado esperado (es del docente), así que `completar` y `repetir_aprobacion` son **interpretaciones del equipo** y quedan como supuesto a validar.

### D-06. Las operaciones no traen canal ni responsable

| | |
|---|---|
| **Paquete** | `operaciones.csv` tiene actor, estado, fecha, promoción y autorización. No tiene canal, mesa, dirección ni responsable. |
| **U2/U3** | RN-14: todo pedido registra responsable y canal. RN-01: el domicilio exige mínimo de $150 MXN. US-02: el domicilio exige teléfono y dirección. |
| **Hallazgo adicional** | Con precios desde 290.00 MXN, cualquier pedido con al menos una línea supera los 150 MXN, así que **los datos del paquete nunca ejercitan RN-01**. |
| **Tratamiento (decisión C)** | Se crea `fixtures/operaciones_extra.csv` (archivo nuevo) con canal, responsable y datos de domicilio por operación, más casos propios para RN-01. Se combina con los CSV originales al cargar los datos. |
| **Estado** | Decidido por el equipo. **Hecho:** el archivo existe (60 operaciones del paquete + 9 casos propios: 7 de RN-01 y 2 de US-02) y `tests/integration/test_fixtures_extra.py` verifica sus resultados contra el dominio. |

### D-07. Catálogo con `habilitado` y `capacidad_o_stock`

| | |
|---|---|
| **Paquete** | 1 platillo deshabilitado y stock por platillo. |
| **U2/U3** | RN-06 (producto agotado se elimina sin cancelar el pedido), RN-13 (inventario en tiempo real) y US-04 (agotado deja de mostrarse). La U3 decidió que Catálogo e Inventario **no son aggregates** y quedan fuera de los 5 casos de uso. |
| **Tratamiento** | Se carga como catálogo de **solo lectura** para validar cantidades y disponibilidad. Un platillo deshabilitado se trata como no disponible (cobertura de RN-06). No se modela inventario completo. |
| **Estado** | Alineado con la decisión de la U3. |

### D-08. El BPMN está incompleto

Los hallazgos H-04 (conexiones sin unir) y H-05 (sin promociones ni alertas) siguen pendientes. Además, el diagrama muestra "Pedido cancelado con reembolso", un concepto que el BRD no define.

**Tratamiento.** `BPMN_E3.pdf` **no se edita**. Se crea un BPMN complementario (`docs/analisis/bpmn-complemento`) que cubre promociones, alertas y la cancelación. El código sigue al BRD, no al BPMN, cuando hay conflicto.

**Estado:** hecho. Ver `docs/analisis/bpmn-complemento.md` (diagramas `bpmn-complemento-proceso` y `bpmn-complemento-excepciones`), que cierra H-04 y H-05 y elimina el "reembolso", que el BRD no define.

### D-09. La promoción de la demo es un porcentaje; el BRD describe un 2x1

| | |
|---|---|
| **U2/U3** | La entrevista y el diagrama describen un **2x1 de tacos los martes de 18:00 a 21:00**, que el mesero aplica "de memoria". |
| **Código** | `Promocion` calcula un descuento porcentual; la semilla de demo (`promo-martes`) usa 20 % con la misma vigencia y los mismos productos. |
| **Tratamiento** | La vigencia, los productos y la regla de una sola promoción coinciden con el BRD; solo cambia la forma del descuento. Un 2x1 se agrega como **variante de `Promocion`** sin tocar `Pedido` ni los servicios (hallazgo H3 de SOLID, principio O). |
| **Estado** | Diferencia documentada; la variante 2x1 queda como trabajo posterior. |

## 4. Resumen de decisiones

| ID | Decisión | Estado |
|---|---|---|
| A | `beneficio_referencia` es solo elegibilidad; nunca aplica descuento (RN-05) | Confirmada por el equipo |
| B | Estados = superconjunto: paquete + `LISTO` + `ENTREGA_NO_COMPLETADA` | Confirmada por el equipo |
| C | Canal y responsable se agregan en `fixtures/operaciones_extra.csv`; los CSV originales no se modifican | Confirmada por el equipo |
| D | `ActorActivo` y la autorización genérica se conservan como reglas adicionales del paquete | Documentada |
| E | `completar` y `repetir_aprobacion` se interpretan según la sección D-05 | Supuesto a validar |
| F | La promoción de la demo es un 20 % con la vigencia del 2x1 del BRD (D-09) | Documentada |

## 5. Trazabilidad preliminar

| Regla del paquete | Specification prevista | Respaldo en U2 | Notas |
|---|---|---|---|
| `puede_procesarse` | `ActorActivo ∧ TieneLineas ∧ Autorizado` | Parcial: RN-03, RN-10, RN-14, US-07 | `ActorActivo` no está en el BRD (D-04) |
| `beneficio_referencia` | `ActorPreferente ∧ TotalMinimo(1500) ∧ ¬PromocionActiva` | RN-04, RN-05, NEC-05 (límite); lealtad fuera de alcance | Solo elegibilidad (D-02) |
| Monto mínimo a domicilio | `MontoMinimoDomicilio(150)` | RN-01, NEC-12, US-03 | No cubierta por los datos del paquete (D-06) |
| Transiciones de estado | Máquina de estados + eventos | RN-02, RN-03, RN-11, H-12 | Ver D-05 |

La matriz completa BRD → regla → componente → prueba exigida por el PIA está en `docs/architecture/matriz-trazabilidad.md`.

## 6. Pendientes que se conservan

- H-01, H-08, H-09, H-10 y H-12 de la U3 siguen como supuestos a validar.
- Los resultados esperados de los 120 casos y las 20 transiciones son del docente. El equipo calculará sus propios oráculos con las reglas de este documento.
