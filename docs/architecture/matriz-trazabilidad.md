# Matriz de trazabilidad: BRD → regla → historia → caso de uso → componente → prueba

**Proyecto:** Sazón Urbano · **Equipo:** 3 · **Curso:** Componentes de Lógica de Negocios (UANL, FIME)
**Ubicación:** `docs/architecture/matriz-trazabilidad.md` · **Fecha:** 05/11/2026

## 1. Cómo leer este documento

Cada fila une un requerimiento del BRD con el código que lo cumple y la prueba que lo demuestra. Las rutas son relativas a `src/sazon_urbano/` (componentes) y `tests/` (pruebas); las pruebas se escriben como `archivo › prueba`.

| Estado | Significado |
|---|---|
| ✅ Implementado | Existe código y al menos una prueba que lo verifica |
| 🟡 Parcial | Se cubre una parte; la sección 7 explica qué falta |
| ⚪ No implementado | Fuera de los 5 casos de uso aprobados en la U3; se documenta y justifica en la sección 7 |

**Resumen de cobertura:**

| Elemento del BRD | Total | ✅ Implementado | 🟡 Parcial | ⚪ No implementado |
|---|---|---|---|---|
| Reglas de negocio (RN) | 15 | 8 | 3 | 4 |
| Necesidades (NEC) | 12 | 6 | 2 | 4 |
| User Stories (US) | 20 | 12 | 2 | 6 |
| Casos de uso (CU) | 5 | 5 | 0 | 0 |

Las 155 pruebas automáticas pasan (10 se omiten sin PostgreSQL y corren en CI) con una cobertura del 99.69 % sobre `src/`.

## 2. Reglas de negocio (RN)

| RN | Regla (resumen) | CU | Componente | Prueba | Estado |
|---|---|---|---|---|---|
| RN-01 | Domicilio con mínimo de $150 MXN | CU-01 | `domain/pedido.py › Pedido.confirmar` con `domain/specifications.py › MontoMinimoDomicilio`; error `MontoMinimoDomicilioNoAlcanzado` | `test_registrar_pedido › test_domicilio_menor_a_150_se_rechaza_y_no_se_guarda_ni_publica_nada` · `test_specifications › test_monto_minimo_domicilio_solo_aplica_a_domicilio_rn01` · `test_api › test_domicilio_menor_a_150_se_rechaza_rn01` y `test_domicilio_con_150_exactos_se_acepta` · `test_persistencia › test_registro_rechazado_no_deja_nada_guardado_rn01` | ✅ |
| RN-02 | Cancelar sin autorización solo si ninguna estación inició | CU-03 | `Pedido.cancelar` / `Pedido.preparacion_iniciada`; `domain/maquina_estados.py` (CREADO → CANCELADO) | `test_cancelar_pedido › test_sin_preparacion_se_cancela_directo_y_sin_merma` · `test_maquina_estados › test_creado_se_cancela_sin_autorizacion_rn02` · `test_api › test_sin_preparacion_se_cancela_directo_rn02` | ✅ |
| RN-03 | Cancelar con preparación iniciada exige Encargado y genera merma | CU-03 | `Pedido.cancelar`; `domain/merma.py › Merma.desde_cancelacion`; `application/handlers.py › CancelarPedidoHandler`; `UnitOfWork` | `test_cancelar_pedido › test_con_preparacion_sin_autorizacion_se_rechaza_y_no_se_guarda_nada`, `test_con_preparacion_y_encargado_se_cancela_y_se_registra_la_merma` · `test_persistencia › test_cancelacion_tardia_autorizada_guarda_pedido_y_merma_juntos`, `test_si_falla_guardar_la_merma_no_queda_un_pedido_cancelado_rn03` · `test_api › test_con_autorizacion_del_encargado_genera_merma_rn03` | ✅ |
| RN-04 | Una sola promoción por pedido | CU-02 | `Pedido.aplicar_promocion` (error `PedidoYaTienePromocion`); `domain/servicios.py › AplicadorDePromocion` | `test_aplicar_promocion › test_segunda_promocion_se_rechaza` · `test_api › test_segunda_promocion_409_rn04` | ✅ |
| RN-05 | La promoción la elige Caja; el sistema nunca la aplica sola | CU-02 | `application/comandos.py › AplicarPromocion` (se pide explícitamente); `Accion.APLICAR_PROMOCION` solo para Caja; `ConsultarPromocionesVigentesHandler` | `test_api › test_el_sistema_nunca_la_aplica_sola_rn05`, `test_aplica_el_descuento_dentro_de_vigencia_rn05`, `test_solo_caja_aplica_promociones_h01` · `test_aplicar_promocion › test_el_mesero_no_aplica_promociones` | ✅ |
| RN-06 | Quitar un producto agotado sin cancelar el pedido | CU-04b | `Pedido.quitar_linea`; `QuitarLineaAgotadaHandler`; `ConsultasDeDisponibilidad` | `test_producto_agotado › test_mesero_quita_la_linea_agotada_sin_cancelar_el_pedido`, `test_no_se_quita_una_linea_cuyo_producto_no_esta_agotado` · `test_api › test_quitar_solo_la_linea_agotada_sin_cancelar_el_pedido_rn06` | ✅ |
| RN-07 | Tiempo meta de 18 / 25 minutos | — | — | — | ⚪ |
| RN-08 | Máximo 25 pedidos activos en horario pico | — | — | — | ⚪ |
| RN-09 | Solo el Gerente configura precios y promociones | — | Las promociones se cargan por semilla (`infrastructure/persistence/semilla.py`); no hay endpoint de configuración | — | ⚪ |
| RN-10 | Solo el Encargado ajusta inventario y autoriza cancelaciones tardías | CU-03 | `Accion.AUTORIZAR_CANCELACION` solo para Encargado (`infrastructure/memoria.py › ControlDeAccesoPorRol`); `Autorizado` | `test_cancelar_pedido › test_un_autorizador_que_no_es_encargado_no_sirve` · `test_api › test_autorizador_que_no_es_encargado_403` | 🟡 (falta el ajuste manual de inventario) |
| RN-11 | El repartidor registra salida y entrega, o el motivo de falla | CU-05 | `domain/entrega.py › Entrega`; errores `EntregaSinSalidaRegistrada`, `MotivoDeFallaObligatorio` | `test_entrega › test_flujo_completo_asignar_salir_y_entregar`, `test_no_se_entrega_sin_registrar_la_salida`, `test_entrega_fallida_exige_motivo_y_cierra_el_pedido_como_no_completado` · `test_api › test_flujo_completo_asignar_salida_confirmacion_rn11` | ✅ |
| RN-12 | Modificar un pedido enviado exige estación sin iniciar, salvo autorización | CU-04b | `Pedido.quitar_linea` (H-08: RN-06 prevalece sobre RN-12 para productos agotados) | Mismas pruebas de RN-06 | 🟡 (solo el caso de producto agotado) |
| RN-13 | Inventario en tiempo real | CU-04a | `DisponibilidadRepository.marcar_agotado`; `application/catalogo.py` valida stock y disponibilidad | `test_api › test_marcar_agotado_actualiza_el_menu_y_bloquea_nuevos_pedidos`, `test_cantidad_mayor_al_stock_422` | 🟡 (no descuenta existencias por venta) |
| RN-14 | Todo pedido registra responsable y canal | CU-01 | `Pedido.crear` (`responsable`, `canal`) | `test_registrar_pedido › test_pedido_en_mesa_se_confirma_con_responsable_y_canal` · `test_api › test_el_resumen_expone_estado_responsable_y_acciones_permitidas` | ✅ |
| RN-15 | Alertas automáticas de existencia mínima | — | — | — | ⚪ |

## 3. Necesidades (NEC)

| NEC | Necesidad (resumen) | Reglas | Componente | Prueba | Estado |
|---|---|---|---|---|---|
| NEC-01 | Inventario en tiempo real | RN-13 | Ver RN-13 | Ver RN-13 | 🟡 |
| NEC-02 | Alertas de existencia mínima | RN-15 | — | — | ⚪ |
| NEC-03 | Marcar agotado y notificar a mesero/caja | RN-06 | `MarcarProductoAgotadoHandler` (Transaction Script, ADR-01); `Notificador` → `NotificadorInterno` | `test_producto_agotado › test_cocina_marca_agotado_y_se_avisa_a_mesero_y_caja` | ✅ |
| NEC-04 | Trazabilidad de modificaciones y cancelaciones con motivo y responsable | RN-03 | `domain/valores.py › Cancelacion` (motivo, responsable, autorizador, fecha); `Merma` | `test_persistencia › test_quitar_linea_actualiza_las_lineas_y_registra_cancelacion_parcial` · `test_cancelar_pedido › test_con_preparacion_y_encargado_se_cancela_y_se_registra_la_merma` | ✅ |
| NEC-05 | Promociones con vigencia, productos y no acumulación | RN-04, RN-05 | `domain/promocion.py › Promocion`, `Vigencia` | `test_aplicar_promocion › test_promocion_fuera_de_vigencia_se_rechaza` · `test_persistencia › test_la_promocion_conserva_vigencia_y_productos` | ✅ |
| NEC-06 | Asignar repartidores y registrar tiempos | RN-11 | `AsignadorDeRepartidor`; `EntregaApplicationService` (la cercanía la decide el Encargado, ADR-01) | `test_entrega › test_no_se_asigna_un_repartidor_no_disponible` | ✅ |
| NEC-07 | Alerta de pedido fuera del tiempo meta | RN-07 | — | — | ⚪ |
| NEC-08 | Reporte de discrepancias | RN-13 | — | — | ⚪ |
| NEC-09 | Reportes de ventas, mermas y repartidores | — | — | — | ⚪ |
| NEC-10 | Permisos por rol | RN-09, RN-10 | `application/puertos.py › ControlDeAcceso`; `ControlDeAccesoPorRol` (tabla de la sección 6) | `test_api › test_rol_sin_permiso_403_us19`, `test_sin_identificar_401` | ✅ |
| NEC-11 | Capturar completos los datos del pedido | RN-14 | `Pedido`, `LineaPedido`, `DatosCliente`, `ProductoPedido` | `test_registrar_pedido › test_pedido_en_mesa_se_confirma_con_responsable_y_canal` · `test_persistencia › test_el_pedido_sobrevive_a_una_sesion_nueva_con_todos_sus_datos` | 🟡 (el pedido no guarda su hora de registro) |
| NEC-12 | Validar el monto mínimo a domicilio | RN-01 | Ver RN-01 | Ver RN-01 | ✅ |

## 4. User Stories (US)

| US | Historia (resumen) | CU | Endpoint | Componente | Prueba | Estado |
|---|---|---|---|---|---|---|
| US-01 | Mesero registra pedido en mesa | CU-01 | `POST /pedidos` | `PedidoApplicationService.registrar_pedido` | `test_registrar_pedido › test_pedido_en_mesa_se_confirma_con_responsable_y_canal` | ✅ |
| US-02 | Caja registra pedido por teléfono/WhatsApp con datos del cliente | CU-01 | `POST /pedidos` | `DatosCliente`; error `DatosDeDomicilioIncompletos` | `test_registrar_pedido › test_domicilio_sin_direccion_ni_telefono_se_rechaza` · `test_api › test_domicilio_sin_cliente_se_rechaza` | ✅ |
| US-03 | Validar monto mínimo de $150 | CU-01 | `POST /pedidos` | `MontoMinimoDomicilio` | Ver RN-01 | ✅ |
| US-04 | Cocina marca agotado en tiempo real | CU-04a | `POST /productos/{id}/agotado` · `GET /menu` | `MarcarProductoAgotadoHandler`; `ConsultarMenuDisponibleHandler` | `test_api › test_marcar_agotado_actualiza_el_menu_y_bloquea_nuevos_pedidos` | ✅ |
| US-05 | Eliminar solo la línea agotada | CU-04b | `DELETE /pedidos/{id}/lineas/{linea}` | `Pedido.quitar_linea` | Ver RN-06 | ✅ |
| US-06 | Cancelar pedido sin preparación | CU-03 | `POST /pedidos/{id}/cancelacion` | `Pedido.cancelar` | Ver RN-02 | ✅ |
| US-07 | Encargado autoriza cancelación tardía y se genera merma | CU-03 | `POST /pedidos/{id}/cancelacion` | `CancelarPedidoHandler`; `Merma` | Ver RN-03 | ✅ |
| US-08 | Aplicar promoción vigente explícitamente | CU-02 | `POST /pedidos/{id}/promocion` | `Promocion.esta_vigente_en` | `test_api › test_fuera_de_vigencia_422` | ✅ |
| US-09 | Impedir más de una promoción | CU-02 | `POST /pedidos/{id}/promocion` | `Pedido.aplicar_promocion` | Ver RN-04 | ✅ |
| US-10 | Encargado ajusta existencias manualmente | — | — | — | — | ⚪ |
| US-11 | Alerta de existencia mínima | — | — | — | — | ⚪ |
| US-12 | Inventario se actualiza con cada venta, merma o recepción | — | — | Solo se marca agotado y se valida stock | Ver RN-13 | 🟡 |
| US-13 | Reporte diario de discrepancias | — | — | Table Module, trabajo posterior (ADR-01) | — | ⚪ |
| US-14 | Asignar repartidor disponible | CU-05 | `GET /repartidores/disponibles` · `POST /entregas` | `AsignarRepartidorHandler`; `ConsultarRepartidoresDisponiblesHandler` | `test_entrega › test_no_se_asigna_un_repartidor_no_disponible` | ✅ |
| US-15 | Repartidor registra salida, entrega o motivo de falla | CU-05 | `POST /entregas/{id}/salida`, `/confirmacion`, `/fallida` | `Entrega.registrar_salida`, `confirmar`, `fallar` | Ver RN-11 | ✅ |
| US-16 | Marcar pedido como retrasado | — | — | — | — | ⚪ |
| US-17 | Reporte de ventas por canal y producto | — | — | Table Module, trabajo posterior (ADR-01) | — | ⚪ |
| US-18 | Gerente configura promociones | — | — | Ver RN-09 | — | ⚪ |
| US-19 | Permisos definidos por rol | todos | todos | `ControlDeAccesoPorRol` | `test_api › test_rol_sin_permiso_403_us19` | ✅ |
| US-20 | Responsable y canal consultables en el historial | CU-01 | `GET /pedidos/{id}` | `ResumenDePedidoDto` | `test_api › test_el_resumen_expone_estado_responsable_y_acciones_permitidas` | 🟡 (se consulta en el resumen, no hay historial de cambios) |

## 5. Casos de uso (CU) y requisitos del PIA

### 5.1 Casos de uso

| CU | Caso de uso | Service → Handler | Aggregates | Patrón (ADR-01) | ADR |
|---|---|---|---|---|---|
| CU-01 | Registrar pedido | `PedidoApplicationService` → `RegistrarPedidoHandler` | Pedido | Domain Model | 01, 02, 03 |
| CU-02 | Aplicar promoción | `PedidoApplicationService` → `AplicarPromocionHandler` + `AplicadorDePromocion` | Pedido, Promoción | Domain Model | 01, 03 |
| CU-03 | Cancelar pedido | `PedidoApplicationService` → `CancelarPedidoHandler` | Pedido, Merma | Domain Model | 01, 02 |
| CU-04a | Marcar producto agotado | `DisponibilidadApplicationService` → `MarcarProductoAgotadoHandler` | — | Transaction Script | 01 |
| CU-04b | Quitar línea agotada | `DisponibilidadApplicationService` → `QuitarLineaAgotadaHandler` | Pedido | Domain Model | 01, 03 |
| CU-05 | Asignar repartidor y registrar entrega | `EntregaApplicationService` → `AsignarRepartidorHandler`, `RegistrarSalidaHandler`, `ConfirmarEntregaHandler`, `RegistrarEntregaFallidaHandler` | Entrega, Repartidor, Pedido | Domain Model | 01, 02 |
| (apoyo) | Iniciar preparación y marcar listo | `PreparacionApplicationService` → `IniciarPreparacionHandler`, `MarcarPedidoListoHandler` | Pedido | Domain Model | 01 |

### 5.2 Requisitos técnicos del PIA

| Requisito del PIA | Evidencia en el repositorio |
|---|---|
| Modelo DDD (aggregates, VO, Domain Services, eventos) | `domain/` · `docs/architecture/diagramas/clases-dominio.puml` · ADR-01 |
| Specification (≥ 3) con AND/OR/NOT | `domain/specifications.py` (7 condiciones + `Y`, `O`, `NO`; `puede_procesarse`, `beneficio_referencia`) · `test_specifications` · ADR-04 |
| State Machine | `domain/maquina_estados.py` + `MAQUINA_PEDIDO` en `domain/pedido.py` · `test_maquina_estados` · `diagramas/estados-pedido.puml` · ADR-05 |
| Persistencia en base de datos | `infrastructure/persistence/` (SQLAlchemy, PostgreSQL) · `test_persistencia` · ADR-06 |
| API REST con OpenAPI | `api/` (17 endpoints, Swagger en `/docs`) · `docs/api/openapi.json` · `test_api › test_openapi_y_swagger_ui_activos` · ADR-07 |
| 120 casos de prueba del paquete | `scripts/ejecutar_casos_prueba.py` → `evidencias/resultados_casos_prueba.csv` · `test_paquete_pia › test_los_120_casos_coinciden_con_el_oraculo_independiente` |
| 20 transiciones de prueba | `scripts/ejecutar_transiciones.py` → `evidencias/resultados_transiciones.csv` · `test_maquina_estados` |
| Pruebas con cobertura ≥ 80 % | 155 pruebas, 99.69 % de cobertura |
| Arquitectura por capas verificable | `test_arquitectura` (5 pruebas de dependencias entre capas) · `diagramas/clases*.puml` |
| CI/CD | `.github/workflows/ci.yml` (PostgreSQL 16, cobertura ≥ 80 %, falla si se omite alguna prueba) |
| Docker Compose | `Dockerfile` (destinos `app` y `tests`) y `docker-compose.yml` (db + app + tests) · `docker/crear-bd-pruebas.sh` |
| Despliegue | Plataforma y URL públicas: ver la tabla de despliegue del `README.md` |

## 6. Permisos por rol (US-19, NEC-10)

Tabla real de `ControlDeAccesoPorRol.PERMISOS`. El Cliente y el Gerente no tienen acciones habilitadas en los 5 casos de uso: el Cliente no usa el sistema (H-02) y el Gerente solo configura promociones y consulta reportes, que quedaron fuera (RN-09, US-13, US-17, US-18).

| Acción | Mesero | Caja | Cocina | Encargado | Repartidor | Gerente | Cliente |
|---|---|---|---|---|---|---|---|
| Registrar pedido en mesa | ✅ | | | | | | |
| Registrar pedido por teléfono/WhatsApp/domicilio | | ✅ | | | | | |
| Aplicar promoción | | ✅ | | | | | |
| Solicitar cancelación | ✅ | ✅ | | | | | |
| Autorizar cancelación tardía | | | | ✅ | | | |
| Marcar producto agotado | | | ✅ | | | | |
| Quitar línea agotada | ✅ | | | | | | |
| Iniciar preparación / marcar listo | | | ✅ | | | | |
| Asignar repartidor | | | | ✅ | | | |
| Registrar salida, entrega o entrega fallida | | | | | ✅ | | |

Ajustes a la U2 derivados de separar Mesero y Caja (H-01, H-07): el Mesero no cobra ni aplica descuentos y Caja no atiende en mesa. Prueba: `test_api › test_mesero_no_registra_pedidos_a_domicilio_h01`, `test_solo_caja_aplica_promociones_h01`.

## 7. Lo que no está implementado y por qué

Los 5 casos de uso (registrar pedido, aplicar promoción, cancelar, producto agotado y entrega) se aprobaron en la U3 como alcance del diseño. Lo siguiente queda fuera y se declara de forma explícita:

| Elemento | Qué falta | Motivo |
|---|---|---|
| RN-07, RN-08, NEC-07, US-16 | Tiempo meta y límite de pedidos activos; alerta de pedido retrasado | Sin user story propia para RN-08 y NEC-07 (H-06); fuera de los 5 casos |
| RN-15, NEC-02, US-11 | Alertas de existencia mínima | Requieren inventario por insumo, fuera de los 5 casos |
| RN-13 (parcial), NEC-01, US-10, US-12 | Descontar existencias por venta, merma o recepción; ajuste manual | El catálogo del paquete trae un stock fijo y no hay aggregate de Inventario (decisión de la U3) |
| RN-09, US-18 | Que el Gerente configure promociones | Las promociones se cargan con la semilla de datos; `Promocion` y `Vigencia` ya modelan la configuración |
| NEC-08, NEC-09, US-13, US-17 | Reportes de discrepancias y ventas | Candidatos a Table Module (ADR-01); no forman parte de los 5 casos |
| RN-12 (parcial) | Modificar líneas de un pedido enviado a cocina con autorización del Encargado | Solo se cubre quitar una línea agotada (H-08: RN-06 prevalece) |
| NEC-11 (parcial) | Hora de registro del pedido | `Pedido` guarda responsable, canal, cliente, líneas y precio; las horas se guardan en `Entrega` y `Cancelacion` |
| US-20 (parcial) | Historial completo de cambios de un pedido | Se consulta el estado, el responsable y las acciones permitidas en `GET /pedidos/{id}` |

## 8. Supuestos que siguen vigentes

| Supuesto | Hallazgo | Dónde se refleja |
|---|---|---|
| Mesero y Caja son roles distintos | H-01, H-07 | Sección 6 y `ControlDeAccesoPorRol` |
| RN-06 prevalece sobre RN-12 al quitar una línea agotada | H-08 | `Pedido.quitar_linea` |
| El precio se conserva al capturar el pedido (snapshot) | H-09 | `ProductoPedido.precio_unitario` |
| El Encargado se identifica como usuario autorizante | H-10 | `Cancelacion.autorizado_por` |
| Los estados del pedido salen del BPMN, no del BRD | H-12 | `EstadoPedido`, ADR-05 |
| El repartidor queda disponible al cerrar la entrega | Etapa 5 | `ConfirmarEntregaHandler`, `Repartidor.liberar` |
| El comensal del paquete es un dato del pedido, no un usuario | D-01 | `docs/analisis/conciliacion-u2-paquete.md` |
