'use strict';
// ---- Configuración: API desplegada en Render (no GitHub) ----
const API = (localStorage.getItem('su.api') || 'https://pia-equipo3-sazon-urbano.onrender.com').replace(/\/$/, '');
const ROLES = ['mesero', 'caja', 'cocina', 'encargado', 'repartidor', 'gerente', 'cliente'];
const ESTACIONES = ['parrilla', 'fria', 'bebidas', 'empaque'];
const FINALES = ['entregado', 'cancelado', 'entrega_no_completada'];
// Permisos por rol (espejo de la API; el servidor es quien decide de verdad)
const PERMISO = { mesa: ['mesero'], remoto: ['caja'], promo: ['caja'], cancelar: ['mesero', 'caja'], agotado: ['cocina'],
  quitar: ['mesero'], asignar: ['encargado'], entrega: ['repartidor'], cocina: ['cocina'] };

const $ = (s, r = document) => r.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const mxn = n => Number(n).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
const leer = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const guardar = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const S = { menu: [], cart: [], canal: 'mesa', rol: leer('su.rol', 'mesero'), usuario: leer('su.usuario', 'ana'),
  pedidos: leer('su.pedidos', []), entregas: leer('su.entregas', []), actual: null };
const puede = a => PERMISO[a].includes(S.rol);
const bloqueo = a => puede(a) ? '' : `disabled title="Requiere rol: ${PERMISO[a].join(' o ')}"`;

class ApiError extends Error {
  constructor(status, error, mensaje, motivos = []) { super(mensaje); Object.assign(this, { status, error, motivos }); }
}

async function api(path, { method = 'GET', body, query } = {}) {
  const url = new URL(API + path);
  Object.entries(query || {}).forEach(([k, v]) => v && url.searchParams.set(k, v));
  const headers = { Accept: 'application/json' };
  if (method !== 'GET') { headers['X-Usuario-Id'] = S.usuario; headers['X-Rol'] = S.rol; }
  if (body) headers['Content-Type'] = 'application/json';
  const ctl = new AbortController();
  const corte = setTimeout(() => ctl.abort(), 75000);
  const aviso = setTimeout(() => { $('#aviso').hidden = false; }, 3500);
  try {
    let r;
    try { r = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: ctl.signal }); }
    catch { throw new ApiError(0, 'SinConexion', ctl.signal.aborted
      ? 'El servidor tardó demasiado en responder. Intenta de nuevo.'
      : 'No se pudo conectar con la API. Si estaba dormida, espera un minuto y reintenta; si persiste, el backend necesita habilitar CORS.'); }
    const d = await r.json().catch(() => null);
    if (!r.ok) throw new ApiError(r.status, d?.error || 'Error', d?.mensaje || `Error ${r.status}`,
      d?.motivos || (d?.detalles || []).map(x => `${x.campo}: ${x.problema}`));
    return d;
  } finally { clearTimeout(corte); clearTimeout(aviso); $('#aviso').hidden = true; }
}

function toast(msg, detalle = [], err = false) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.innerHTML = `${esc(msg)}${detalle.map(d => `<small>${esc(d)}</small>`).join('')}`;
  $('#toasts').append(t);
  setTimeout(() => t.remove(), err ? 7000 : 3500);
}
async function intentar(fn, ok) {
  try { const r = await fn(); if (ok) toast(ok); return r; }
catch (e) { toast(e instanceof ApiError ? `${e.status ? e.status + ' · ' : ''}${e.error}: ${e.message}` : 'Error inesperado', e.motivos || [], true); }
}

function dialogo(titulo, cuerpo, ok = 'Confirmar') {
  return new Promise(res => {
    const d = $('#dlg');
    d.innerHTML = `<form method="dialog"><h2>${esc(titulo)}</h2>${cuerpo}<div class="fila fin"><button value="x" class="sec" formnovalidate>Cancelar</button><button value="ok">${ok}</button></div></form>`;
    d.onclose = () => res(d.returnValue === 'ok' ? Object.fromEntries(new FormData(d.querySelector('form'))) : null);
    d.showModal();
  });
}
const campo = (n, label, extra = '') => `<label class="campo">${label}<input name="${n}" ${extra}></label>`;

// ---- Navegación ----
function ir() {
  const v = (location.hash || '#tomar').slice(1);
  document.querySelectorAll('main > section').forEach(s => { s.hidden = s.id !== 'v-' + v; });
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('on', a.hash === '#' + v));
  ({ tomar: cargarMenu, pedidos: cargarPedidos, entregas: pintarEntregas, consultas: pintarConsultas })[v]?.();
}

// ---- Tomar pedido ----
async function cargarMenu() {
  S.menu = await intentar(() => api('/menu')) || S.menu;
  pintarMenu(); pintarTicket();
}
function pintarMenu() {
  $('#menu').innerHTML = S.menu.map(p => `<article class="plato ${p.disponible ? '' : 'agotado'}">
    <div><h3>${esc(p.nombre)}</h3><p class="precio">${mxn(p.precio)}</p></div>
    <div class="acc"><button data-add="${esc(p.id)}" ${p.disponible ? '' : 'disabled'}>${p.disponible ? 'Agregar' : 'Agotado'}</button>
    ${p.disponible ? `<button class="sec" data-agotar="${esc(p.id)}" ${bloqueo('agotado')}>Marcar agotado</button>` : ''}</div></article>`).join('')
    || '<p class="vacio">El menú está vacío.</p>';
}
$('#menu').addEventListener('click', async e => {
  const add = e.target.dataset.add, ag = e.target.dataset.agotar;
  if (add) {
    const p = S.menu.find(x => x.id === add), l = S.cart.find(x => x.id === add);
    l ? l.cantidad++ : S.cart.push({ id: p.id, nombre: p.nombre, precio: Number(p.precio), cantidad: 1, mods: '' });
    pintarTicket();
  }
  if (ag && await intentar(() => api(`/productos/${encodeURIComponent(ag)}/agotado`, { method: 'POST' }), 'Producto marcado como agotado')) cargarMenu();
});

function pintarTicket() {
  const total = S.cart.reduce((t, l) => t + l.precio * l.cantidad, 0), mesa = S.canal === 'mesa';
  const form = S.form || {};
  $('#ticket').innerHTML = `<h2>Nuevo pedido</h2>
    <label class="campo">Canal<select id="canal">${[['mesa', 'Mesa'], ['telefono_whatsapp', 'Teléfono / WhatsApp'], ['domicilio', 'Domicilio']]
      .map(([v, t]) => `<option value="${v}" ${S.canal === v ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
    ${mesa ? campo('mesa', 'Mesa', `id="f-mesa" value="${esc(form.mesa || '')}"`)
      : campo('nombre', 'Nombre', `id="f-nombre" value="${esc(form.nombre || '')}"`) + campo('telefono', 'Teléfono', `id="f-telefono" value="${esc(form.telefono || '')}"`)
        + campo('direccion', 'Dirección', `id="f-direccion" value="${esc(form.direccion || '')}"`)}
    ${S.cart.length ? S.cart.map((l, i) => `<div class="item"><b>${esc(l.nombre)}</b>
      <span class="qty"><button class="sec" data-q="${i}" data-d="-1" aria-label="Quitar uno">−</button><span>${l.cantidad}</span><button class="sec" data-q="${i}" data-d="1" aria-label="Agregar uno">+</button></span>
      <input data-mod="${i}" placeholder="Modificaciones (separadas por coma)" value="${esc(l.mods)}"><span>${mxn(l.precio * l.cantidad)}</span></div>`).join('')
      : '<p class="vacio">Agrega platillos del menú.</p>'}
    <div class="total"><span>Total estimado</span><span>${mxn(total)}</span></div>
    ${S.canal === 'domicilio' ? '<p class="nota">Domicilio: mínimo $150 (RN-01). El total final lo calcula la API.</p>' : ''}
    <button id="enviar" ${S.cart.length ? '' : 'disabled'} ${bloqueo(mesa ? 'mesa' : 'remoto')}>Registrar pedido</button>
    ${puede(mesa ? 'mesa' : 'remoto') ? '' : `<p class="nota">Con el rol ${esc(S.rol)} no puedes registrar pedidos de este canal.</p>`}`;
}
const recogerForm = () => { S.form = Object.fromEntries([...$('#ticket').querySelectorAll('[id^=f-]')].map(i => [i.id.slice(2), i.value])); };
$('#ticket').addEventListener('change', e => { if (e.target.id === 'canal') { recogerForm(); S.canal = e.target.value; pintarTicket(); } });
$('#ticket').addEventListener('input', e => { if (e.target.dataset.mod) S.cart[e.target.dataset.mod].mods = e.target.value; });
$('#ticket').addEventListener('click', async e => {
  if (e.target.dataset.q) {
    recogerForm(); const l = S.cart[e.target.dataset.q]; l.cantidad += Number(e.target.dataset.d);
    if (l.cantidad < 1) S.cart.splice(e.target.dataset.q, 1);
    pintarTicket();
  }
  if (e.target.id !== 'enviar') return;
  recogerForm(); const f = S.form;
  const body = { canal: S.canal, items: S.cart.map(l => ({ platillo_id: l.id, cantidad: l.cantidad,
    modificaciones: l.mods.split(',').map(x => x.trim()).filter(Boolean) })) };
  if (S.canal === 'mesa') body.mesa = f.mesa || null; else body.cliente = { nombre: f.nombre || '', telefono: f.telefono || '', direccion: f.direccion || '' };
  const r = await intentar(() => api('/pedidos', { method: 'POST', body }), 'Pedido registrado');
  if (r) {
    S.pedidos.unshift({ id: r.pedido_id, canal: S.canal, ts: Date.now() }); guardar('su.pedidos', S.pedidos);
    S.cart = []; S.form = {}; location.hash = '#pedidos'; verPedido(r.pedido_id);
  }
});
async function cargarPedidos() {
  const lista = await intentar(() => api('/pedidos'));
  if (lista) { S.pedidos = lista.map(p => ({ id: p.id, canal: p.canal })); guardar('su.pedidos', S.pedidos); }
  pintarPedidos();
}
// ---- Pedidos ----
function pintarPedidos() {
  $('#historial').innerHTML = S.pedidos.length ? S.pedidos.map(p => `<li><span><b>${esc(p.id)}</b> <small class="nota">${esc(p.canal)}</small></span><button class="sec" data-ver="${esc(p.id)}">Abrir</button></li>`).join('')
    : '<li class="vacio">Los pedidos que registres aquí aparecerán en esta lista. También puedes buscar cualquier ID.</li>';
  pintarDetalle();
}
$('#buscar').addEventListener('submit', e => { e.preventDefault(); verPedido(new FormData(e.target).get('id').trim()); });
$('#historial').addEventListener('click', e => e.target.dataset.ver && verPedido(e.target.dataset.ver));

async function verPedido(id) {
  const r = await intentar(() => api(`/pedidos/${encodeURIComponent(id)}`));
  if (!r) return;
  S.actual = r;
  if (!S.pedidos.some(p => p.id === id)) { S.pedidos.unshift({ id, canal: r.canal, ts: Date.now() }); guardar('su.pedidos', S.pedidos); }
  pintarPedidos();
}
function pintarDetalle() {
  const p = S.actual, el = $('#detalle');
  if (!p) { el.innerHTML = '<h2>Detalle</h2><p class="vacio">Selecciona o busca un pedido para ver su comanda y las acciones disponibles.</p>'; return; }
  const vivo = !FINALES.includes(p.estado);
  el.innerHTML = `<h2>${esc(p.id)} <span class="sello ${esc(p.estado)}">${esc(p.estado.replace(/_/g, ' '))}</span></h2>
    <p class="nota">${esc(p.canal)} · ${esc(p.mesa_o_cliente)} · atiende ${esc(p.responsable)}</p>
    ${p.lineas.map(l => `<div class="item"><span><b>${l.cantidad}×</b> ${esc(l.producto)}${l.modificaciones.length ? `<small class="nota"> (${esc(l.modificaciones.join(', '))})</small>` : ''}</span><span>${mxn(l.subtotal)}</span>
      ${vivo ? `<button class="sec" data-quitar="${esc(l.linea_id)}" ${bloqueo('quitar')}>Quitar (agotado)</button>` : ''}</div>`).join('')}
    ${p.promocion ? `<div class="item"><span>${esc(p.promocion)}</span><span>−${mxn(p.descuento)}</span></div>` : ''}
    <div class="total"><span>Total</span><span>${mxn(p.total)}</span></div>
    <div class="fila">
      ${vivo && !p.promocion ? `<button class="sec" data-a="promo" ${bloqueo('promo')}>Aplicar promoción</button>` : ''}
      ${['aceptado', 'en_preparacion'].includes(p.estado) ? `<button data-a="prep" ${bloqueo('cocina')}>Iniciar preparación</button>` : ''}
      ${p.acciones_permitidas.includes('marcar_listo') ? `<button data-a="listo" ${bloqueo('cocina')}>Marcar listo</button>` : ''}
      ${p.canal === 'domicilio' && p.estado === 'listo' ? `<button data-a="entrega" ${bloqueo('asignar')}>Asignar repartidor</button>` : ''}
      ${vivo ? `<button class="peligro" data-a="cancelar" ${bloqueo('cancelar')}>Cancelar</button>` : ''}
      <button class="sec" data-a="refrescar">Actualizar</button></div>`;
}
$('#detalle').addEventListener('click', async e => {
  const p = S.actual, id = encodeURIComponent(p?.id || ''), a = e.target.dataset.a, post = (ruta, body) => api(`/pedidos/${id}${ruta}`, { method: 'POST', body });
  let ok;
  if (e.target.dataset.quitar) ok = await intentar(() => api(`/pedidos/${id}/lineas/${encodeURIComponent(e.target.dataset.quitar)}`, { method: 'DELETE' }), 'Línea quitada');
  else if (a === 'promo') {
    const d = await dialogo('Aplicar promoción', campo('promo', 'ID de la promoción', 'value="promo-martes" required')
      + campo('fecha', 'Simular fecha y hora (opcional)', 'type="datetime-local"') + '<p class="nota">Sin fecha se usa la hora del servidor (puede ser UTC).</p>');
    if (d) ok = await intentar(() => post('/promocion', { promocion_id: d.promo, fecha_hora: d.fecha || null }), 'Promoción aplicada');
  } else if (a === 'prep') {
    const d = await dialogo('Iniciar preparación', `<label class="campo">Estación<select name="estacion">${ESTACIONES.map(x => `<option>${x}</option>`).join('')}</select></label>`);
    if (d) ok = await intentar(() => post('/preparacion', { estacion: d.estacion }), 'Preparación iniciada');
  } else if (a === 'listo') ok = await intentar(() => post('/listo'), 'Pedido listo');
  else if (a === 'cancelar') {
    const dura = ['en_preparacion', 'listo'].includes(p.estado);
    const d = await dialogo('Cancelar pedido', campo('motivo', 'Motivo', 'minlength="3" required')
      + (dura ? '<p class="nota">La preparación ya inició: requiere autorización del Encargado (RN-03) y genera merma.</p>' : '')
      + campo('aut', 'Usuario que autoriza (Encargado)', dura ? 'value="eva" required' : 'placeholder="Solo si aplica"'));
    if (d) ok = await intentar(() => post('/cancelacion', { motivo: d.motivo, autorizador: d.aut ? { usuario_id: d.aut, rol: 'encargado' } : null }), 'Pedido cancelado');
  } else if (a === 'entrega') { sessionStorage.setItem('su.pedidoEntrega', p.id); location.hash = '#entregas'; return; }
  else if (a === 'refrescar') ok = true;
  if (ok) verPedido(p.id);
});

// ---- Entregas ----
async function pintarEntregas() {
  const reps = await intentar(() => api('/repartidores/disponibles')) || [];
  const pre = sessionStorage.getItem('su.pedidoEntrega') || ''; sessionStorage.removeItem('su.pedidoEntrega');
  $('#v-entregas').innerHTML = `<h2>Entregas</h2><div class="tarjetas">
    <form id="asignar" class="caja">${campo('pedido_id', 'ID del pedido', `required value="${esc(pre)}"`)}
      <label class="campo">Repartidor disponible<select name="repartidor_id">${reps.map(r => `<option value="${esc(r.id)}">${esc(r.nombre)} (${esc(r.id)})</option>`).join('') || '<option value="">Sin repartidores disponibles</option>'}</select></label>
      <button ${bloqueo('asignar')}>Asignar repartidor</button></form>
    <div class="caja"><h3>Entregas de esta sesión</h3><ul class="lista">${S.entregas.map((x, i) => `<li><span><b>${esc(x.id)}</b> · ${esc(x.pedido_id)} <span class="sello ${esc(x.estado)}">${esc(x.estado.replace(/_/g, ' '))}</span></span>
      <span class="fila"><button class="sec" data-e="salida" data-i="${i}" ${bloqueo('entrega')}>Salida</button><button class="sec" data-e="confirmacion" data-i="${i}" ${bloqueo('entrega')}>Entregada</button><button class="sec" data-e="fallida" data-i="${i}" ${bloqueo('entrega')}>Fallida</button></span></li>`).join('')
      || '<li class="vacio">Asigna un repartidor para ver la entrega aquí. La API no tiene un listado de entregas.</li>'}</ul></div></div>`;
}
$('#v-entregas').addEventListener('submit', async e => {
  e.preventDefault(); const d = Object.fromEntries(new FormData(e.target));
  const r = await intentar(() => api('/entregas', { method: 'POST', body: d }), 'Repartidor asignado');
  if (r) { S.entregas.unshift({ id: r.entrega_id, pedido_id: d.pedido_id, estado: r.estado }); guardar('su.entregas', S.entregas); pintarEntregas(); }
});
$('#v-entregas').addEventListener('click', async e => {
  const acc = e.target.dataset.e; if (!acc) return;
  const x = S.entregas[e.target.dataset.i]; let body;
  if (acc === 'fallida') { const d = await dialogo('Entrega fallida', campo('motivo', 'Motivo', 'minlength="3" required placeholder="Cliente ausente"')); if (!d) return; body = d; }
  const r = await intentar(() => api(`/entregas/${encodeURIComponent(x.id)}/${acc}`, { method: 'POST', body }), 'Entrega actualizada');
  if (r) { x.estado = r.estado; guardar('su.entregas', S.entregas); pintarEntregas(); }
});

// ---- Consultas ----
function pintarConsultas() {
  $('#v-consultas').innerHTML = `<h2>Consultas</h2><div class="tarjetas">
    <div class="caja"><h3>Promociones vigentes</h3><div class="fila"><input id="q-fecha" type="datetime-local"><button id="q-promos">Consultar</button></div><div id="o-promos"></div></div>
    <div class="caja"><h3>Evaluar operación del paquete PIA</h3><div class="fila"><input id="q-op" placeholder="ID de operación"><button id="q-eval">Evaluar</button></div><div id="o-eval"></div></div>
    <div class="caja"><h3>Servidor</h3><p class="nota">${esc(API)}</p><button id="q-salud">Probar /salud</button><div id="o-salud"></div></div></div>`;
}
$('#v-consultas').addEventListener('click', async e => {
  const out = (id, html) => { $('#' + id).innerHTML = html; };
  if (e.target.id === 'q-promos') {
    const r = await intentar(() => api('/promociones/vigentes', { query: { fecha_hora: $('#q-fecha').value } }));
    if (r) out('o-promos', r.length ? `<ul class="lista">${r.map(p => `<li><span><b>${esc(p.nombre)}</b><br><small class="nota">${esc(p.id)} · ${esc(p.horario)} · ${esc(p.productos.join(', '))}</small></span></li>`).join('')}</ul>` : '<p class="vacio">No hay promociones vigentes en esa fecha y hora.</p>');
  }
  if (e.target.id === 'q-eval') {
    const r = await intentar(() => api(`/operaciones/${encodeURIComponent($('#q-op').value.trim())}/evaluacion`));
    if (r) out('o-eval', `<pre>${esc(JSON.stringify(r, null, 2))}</pre>`);
  }
  if (e.target.id === 'q-salud') { const r = await intentar(() => api('/salud'), 'Servidor en línea'); if (r) out('o-salud', `<pre>${esc(JSON.stringify(r))}</pre>`); }
});

// ---- Sesión y arranque ----
$('#rol').innerHTML = ROLES.map(r => `<option ${r === S.rol ? 'selected' : ''}>${r}</option>`).join('');
$('#usuario').value = S.usuario;
$('#rol').onchange = e => { S.rol = e.target.value; guardar('su.rol', S.rol); ir(); };
$('#usuario').onchange = e => { S.usuario = e.target.value.trim() || 'ana'; guardar('su.usuario', S.usuario); };
async function salud() {
  try { await api('/salud'); $('#luz').className = 'luz ok'; } catch { $('#luz').className = 'luz mal'; }
}
window.addEventListener('hashchange', ir);
salud(); ir();
