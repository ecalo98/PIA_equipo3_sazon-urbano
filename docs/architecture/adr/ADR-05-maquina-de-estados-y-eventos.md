# ADR-05: Máquina de estados explícita y Domain Events por transición

**Estado:** Aceptada · **Fecha:** 03/11/2026

## Contexto
El Pedido tenía su estado repartido en varios `if` (`if self.estado is not ...`). El paquete del PIA pide transiciones
válidas e inválidas (aprobar, repetir aprobación, saltar estado, completar, cancelar) y el PIA exige State Machine y
Domain Events. El BRD tiene reglas que dependen del estado (RN-02, RN-03, RN-11).

## Alternativas
- **`if` por método (estado anterior):** funciona, pero las transiciones válidas no se ven en un solo lugar.
- **Patrón State (una clase por estado):** flexible, pero para 7 estados y 6 acciones agrega más clases de las necesarias.
- **Tabla de transiciones (estado, acción) → estado:** todo el flujo en un lugar, fácil de probar y de dibujar.

## Decisión
`domain/maquina_estados.py` define una máquina genérica basada en tabla. `MAQUINA_PEDIDO` (en `domain/pedido.py`)
declara las transiciones válidas; cualquier otra lanza `TransicionDeEstadoInvalida` (error de negocio, 409 en la API).
`Pedido` cambia de estado solo mediante `_transicionar`. Estados = superconjunto del paquete y de la U3 (decisión B):
CREADO, ACEPTADO, EN_PREPARACION, LISTO, ENTREGADO, CANCELADO, ENTREGA_NO_COMPLETADA.

Cada transición emite un Domain Event: `PedidoConfirmado`, `PreparacionIniciada`, `PedidoListo`, `PedidoEntregado`,
`PedidoEntregaNoCompletada`, `PedidoCancelado`. Los eventos se publican después de confirmar la Unit of Work (ADR-02).
La aprobación (`application/aprobacion.py`) combina la Specification `puede_procesarse` con la transición ACEPTAR.
El diagrama de estados se **genera de la misma tabla** (`scripts/generar_diagrama_estados.py`) y una prueba verifica
que el `.puml` versionado coincide con el código.

## Consecuencias
- **Beneficios:** el flujo completo se lee en una tabla; las transiciones inválidas se rechazan sin tocar el estado ni
  emitir eventos; el diagrama no puede quedar desactualizado.
- **Costos:** se endurece el flujo: ya no se puede pasar de ACEPTADO a LISTO sin EN_PREPARACION (antes sí). Las pruebas
  de la U3 se ajustaron para pasar por EN_PREPARACION.
- **Riesgos:** la segunda estación que inicia preparación no cambia el estado del pedido (se maneja en `Pedido`, no en la tabla).
- **Pendiente:** las transiciones de `Entrega` (ASIGNADA → EN_RUTA → ENTREGADA/FALLIDA) siguen con sus errores específicos de RN-11.

## Trazabilidad
RN-02, RN-03, RN-11 · NEC-04 · US-06, US-07, US-15 · H-12 · `docs/analisis/conciliacion-u2-paquete.md` (D-05)
· Pruebas: `tests/test_maquina_estados.py` · Evidencia: `evidencias/resultados_transiciones.csv`
