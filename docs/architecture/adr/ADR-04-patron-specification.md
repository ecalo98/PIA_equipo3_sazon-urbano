# ADR-04: Patrón Specification para las reglas combinables

**Estado:** Aceptada · **Fecha:** 02/11/2026

## Contexto
El PIA exige al menos tres Specifications combinables con AND/OR/NOT. El paquete de datos define dos reglas
compuestas (`puede_procesarse` y `beneficio_referencia`) y el BRD tiene reglas que también son condiciones
combinables (RN-01 monto mínimo a domicilio, RN-04/RN-05 promociones). En la U3, RN-01 estaba escrita como un
`if` dentro de `Pedido.confirmar`.

## Alternativas
- **Condicionales dentro de cada método:** rápido, pero repite condiciones y no explica por qué falló una regla.
- **Servicio de validación con un método por regla:** centraliza, pero cada combinación nueva obliga a editar código.
- **Specification:** cada condición es una clase pequeña con nombre del negocio; las combinaciones se arman sin
  editar las existentes.

## Decisión
Se implementa el patrón Specification en `domain/specifications.py`, con combinadores `Y`, `O` y `NO`
(operadores `&`, `|`, `~`). Las Specifications evalúan una `OperacionEvaluable` (Value Object de solo lectura) o
cualquier objeto con los mismos atributos, como `Pedido`. RN-01 pasó de un `if` a `MontoMinimoDomicilio`.
`beneficio_referencia` solo evalúa **elegibilidad** y nunca aplica descuentos (decisión A, RN-05).

## Consecuencias
- **Beneficios:** una regla, una clase; nuevas combinaciones sin editar código existente (principio O de SOLID);
  `motivos_de_rechazo` explica qué condición falló (útil para respuestas 422 de la API).
- **Costos:** más clases pequeñas.
- **Riesgos:** abusar del patrón en condiciones triviales. Se limita a reglas del negocio con nombre propio.

## Trazabilidad
RN-01, RN-04, RN-05 · NEC-05, NEC-12 · US-03, US-08, US-09 · `docs/analisis/conciliacion-u2-paquete.md` (D-02, D-03, D-04)
· Pruebas: `tests/test_specifications.py`, `tests/test_paquete_pia.py`
