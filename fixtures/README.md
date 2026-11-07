# Fixtures propios del equipo

Archivos **nuevos** que complementan el paquete de datos del PIA sin modificarlo (decisión C, `docs/analisis/conciliacion-u2-paquete.md`).

- `menu_sazon_urbano.csv`: menú propio de Sazón Urbano. Incluye platillos de menos de $150 MXN (el paquete no tiene ninguno,
  así que sin ellos RN-01 nunca se ejercitaría) y la estación de cocina que prepara cada uno.
- `operaciones_extra.csv`: completa las 60 operaciones del paquete con canal, mesa, responsable (Mesero solo en mesa y Caja en los demás canales, H-01), teléfono y dirección, porque los CSV originales no los traen (RN-14, US-02). Además trae 9 casos propios (`tipo` = `rn01` o `us02`) con `lineas` (formato `platillo_id:cantidad;...`, usando `menu_sazon_urbano.csv`) y `resultado_esperado` (`aceptado`, `rechazado_monto_minimo` o `rechazado_datos_domicilio`). Los datos son ficticios. Lo verifica `tests/integration/test_fixtures_extra.py`.
