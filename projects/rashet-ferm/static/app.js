const state = {
  nodes: [],     // {x,y}
  members: [],   // {i,j}
  supports: [],  // {node, kind}
  loads: [],     // {node, fx, fy}
};
let lastPayload = null;

// ---------- сечения ----------
const SEC_FIELDS = {
  pipe: [['d_out', 'Внешний D, мм', 60], ['d_in', 'Внутренний d, мм', 50]],
  circle: [['d', 'Диаметр d, мм', 40]],
  rectangle: [['b', 'Ширина b, мм', 50], ['h', 'Высота h, мм', 80]],
  box: [['b_out', 'Ширина b, мм', 60], ['h_out', 'Высота h, мм', 60], ['t', 'Толщина стенки t, мм', 4]],
  i_beam: [['h', 'Высота h, мм', 100], ['b', 'Ширина полки b, мм', 68],
           ['s', 'Толщина стенки s, мм', 4.5], ['t', 'Толщина полки t, мм', 7.2]],
};
function renderSecDims() {
  const type = document.getElementById('sec_type').value;
  const box = document.getElementById('sec_dims');
  box.innerHTML = '';
  for (const [key, label, def] of SEC_FIELDS[type]) {
    const lab = document.createElement('label');
    lab.innerHTML = `${label}<input type="number" step="1" value="${def}" data-dim="${key}">`;
    box.appendChild(lab);
  }
}
document.getElementById('sec_type').addEventListener('change', renderSecDims);
renderSecDims();
function getSectionPayload() {
  const type = document.getElementById('sec_type').value;
  const dims = {};
  document.querySelectorAll('#sec_dims [data-dim]').forEach(inp => { dims[inp.dataset.dim] = parseFloat(inp.value); });
  return { type, dims };
}

// ---------- шаблон: ферма Пратта ----------
function buildPrattTemplate() {
  const span = parseFloat(document.getElementById('tpl_span').value);
  const h = parseFloat(document.getElementById('tpl_height').value);
  const N = parseInt(document.getElementById('tpl_panels').value);
  if (isNaN(span) || isNaN(h) || isNaN(N) || N < 2) { showError('Проверь пролёт/высоту/число панелей (панелей ≥ 2).'); return; }

  state.nodes = []; state.members = []; state.supports = []; state.loads = [];
  const bottom = []; // индексы нижних узлов b0..bN
  const top = {};    // i -> индекс верхнего узла (для i=1..N-1)

  for (let i = 0; i <= N; i++) {
    bottom.push(state.nodes.length);
    state.nodes.push({ x: i * span / N, y: 0 });
  }
  for (let i = 1; i <= N - 1; i++) {
    top[i] = state.nodes.length;
    state.nodes.push({ x: i * span / N, y: h });
  }

  for (let i = 0; i < N; i++) state.members.push({ i: bottom[i], j: bottom[i + 1] });
  for (let i = 1; i <= N - 2; i++) state.members.push({ i: top[i], j: top[i + 1] });
  if (N >= 2) {
    state.members.push({ i: bottom[0], j: top[1] });
    state.members.push({ i: bottom[N], j: top[N - 1] });
  }
  for (let i = 1; i <= N - 1; i++) state.members.push({ i: bottom[i], j: top[i] });
  for (let i = 1; i <= N - 2; i++) {
    if (i < N / 2) state.members.push({ i: bottom[i], j: top[i + 1] });
    else state.members.push({ i: bottom[i + 1], j: top[i] });
  }

  state.supports.push({ node: bottom[0], kind: 'pin' });
  state.supports.push({ node: bottom[N], kind: 'roller_y' });

  renderLists(); drawPreview();
}

// ---------- добавление вручную ----------
function addNode() {
  const x = parseFloat(document.getElementById('new_n_x').value);
  const y = parseFloat(document.getElementById('new_n_y').value);
  if (isNaN(x) || isNaN(y)) { showError('Укажите x и y узла.'); return; }
  state.nodes.push({ x, y });
  renderLists(); drawPreview();
}
function addMember() {
  const i = parseInt(document.getElementById('new_m_i').value);
  const j = parseInt(document.getElementById('new_m_j').value);
  if (isNaN(i) || isNaN(j) || i === j || i < 0 || j < 0 || i >= state.nodes.length || j >= state.nodes.length) {
    showError('Укажите два разных существующих узла.'); return;
  }
  state.members.push({ i, j });
  renderLists(); drawPreview();
}
function addSupport() {
  const node = parseInt(document.getElementById('new_s_node').value);
  const kind = document.getElementById('new_s_kind').value;
  if (isNaN(node) || node < 0 || node >= state.nodes.length) { showError('Укажите существующий узел.'); return; }
  state.supports.push({ node, kind });
  renderLists(); drawPreview();
}
function addLoad() {
  const node = parseInt(document.getElementById('new_l_node').value);
  const fx = parseFloat(document.getElementById('new_l_fx').value) || 0;
  const fy = parseFloat(document.getElementById('new_l_fy').value) || 0;
  if (isNaN(node) || node < 0 || node >= state.nodes.length) { showError('Укажите существующий узел.'); return; }
  state.loads.push({ node, fx, fy });
  renderLists(); drawPreview();
}
function removeItem(arrName, idx) { state[arrName].splice(idx, 1); renderLists(); drawPreview(); }

function renderLists() {
  const kindNames = { pin: 'шарнир неподв.', roller_y: 'каток (гориз.)', roller_x: 'каток (верт.)' };

  const nb = document.getElementById('nodes_list'); nb.innerHTML = '';
  state.nodes.forEach((n, i) => {
    nb.innerHTML += `<div class="item-row"><span>№${i}: (${n.x}, ${n.y})</span>
      <button onclick="removeItem('nodes',${i})">×</button></div>`;
  });

  const mb = document.getElementById('members_list'); mb.innerHTML = '';
  state.members.forEach((m, i) => {
    mb.innerHTML += `<div class="item-row"><span>№${i}: ${m.i} — ${m.j}</span>
      <button onclick="removeItem('members',${i})">×</button></div>`;
  });

  const sb = document.getElementById('supports_list'); sb.innerHTML = '';
  state.supports.forEach((s, i) => {
    sb.innerHTML += `<div class="item-row"><span>узел ${s.node}: ${kindNames[s.kind]}</span>
      <button onclick="removeItem('supports',${i})">×</button></div>`;
  });

  const lb = document.getElementById('loads_list'); lb.innerHTML = '';
  state.loads.forEach((l, i) => {
    lb.innerHTML += `<div class="item-row"><span>узел ${l.node}: Fx=${l.fx} Н, Fy=${l.fy} Н</span>
      <button onclick="removeItem('loads',${i})">×</button></div>`;
  });
}

function showError(msg) {
  const box = document.getElementById('error_box');
  box.textContent = msg; box.hidden = false;
  setTimeout(() => { box.hidden = true; }, 4500);
}

// ---------- canvas-предпросмотр ----------
function drawPreview() {
  const cv = document.getElementById('preview');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  if (state.nodes.length === 0) return;

  const xs = state.nodes.map(n => n.x), ys = state.nodes.map(n => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = Math.max(maxX - minX, 1), spanY = Math.max(maxY - minY, 1);
  const margin = 60;
  const scale = Math.min((W - 2 * margin) / spanX, (H - 2 * margin) / spanY);
  const X = x => margin + (x - minX) * scale;
  const Y = y => H - margin - (y - minY) * scale;

  ctx.strokeStyle = '#5ec8ff'; ctx.lineWidth = 2.5;
  state.members.forEach(m => {
    const a = state.nodes[m.i], b = state.nodes[m.j];
    if (!a || !b) return;
    ctx.beginPath(); ctx.moveTo(X(a.x), Y(a.y)); ctx.lineTo(X(b.x), Y(b.y)); ctx.stroke();
  });

  ctx.fillStyle = '#eaf1f8'; ctx.font = '11px IBM Plex Mono'; ctx.textAlign = 'center';
  state.nodes.forEach((n, i) => {
    ctx.beginPath(); ctx.arc(X(n.x), Y(n.y), 4, 0, 7); ctx.fill();
    ctx.fillText(i, X(n.x) + 10, Y(n.y) - 8);
  });

  ctx.strokeStyle = '#eaf1f8';
  state.supports.forEach(s => {
    const n = state.nodes[s.node]; if (!n) return;
    const x = X(n.x), y = Y(n.y), sz = 14;
    ctx.beginPath();
    ctx.moveTo(x, y); ctx.lineTo(x - sz, y + sz * 1.6); ctx.lineTo(x + sz, y + sz * 1.6); ctx.closePath();
    ctx.stroke();
    if (s.kind !== 'pin') { ctx.beginPath(); ctx.moveTo(x - sz - 2, y + sz * 1.6 + 5); ctx.lineTo(x + sz + 2, y + sz * 1.6 + 5); ctx.stroke(); }
  });

  ctx.strokeStyle = '#ff8a3d'; ctx.fillStyle = '#ff8a3d';
  state.loads.forEach(l => {
    const n = state.nodes[l.node]; if (!n) return;
    const mag = Math.hypot(l.fx, l.fy);
    if (mag < 1e-9) return;
    const scaleArrow = 40 / mag;
    const x1 = X(n.x) - l.fx * scaleArrow, y1 = Y(n.y) + l.fy * scaleArrow;
    const x2 = X(n.x), y2 = Y(n.y);
    arrow(ctx, x1, y1, x2, y2);
    ctx.fillText(mag.toFixed(0) + ' Н', x1, y1 - 6);
  });
}
function arrow(ctx, x1, y1, x2, y2) {
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  const ang = Math.atan2(y2 - y1, x2 - x1);
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - 7 * Math.cos(ang - 0.4), y2 - 7 * Math.sin(ang - 0.4));
  ctx.lineTo(x2 - 7 * Math.cos(ang + 0.4), y2 - 7 * Math.sin(ang + 0.4));
  ctx.closePath(); ctx.fill();
}
drawPreview();

// ---------- API ----------
function buildPayload() {
  return {
    E: parseFloat(document.getElementById('E_gpa').value) * 1e9,
    sigma_allow: parseFloat(document.getElementById('sigma_allow').value) * 1e6,
    section: getSectionPayload(),
    nodes: state.nodes,
    members: state.members,
    supports: state.supports,
    loads: state.loads,
  };
}

async function calculate() {
  const payload = buildPayload();
  if (payload.nodes.length < 2) { showError('Добавьте узлы (минимум 2).'); return; }
  lastPayload = payload;
  try {
    const resp = await fetch('/api/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.ok) { showError(data.error || 'Ошибка расчёта'); return; }
    renderResults(data);
    document.getElementById('btn-report').disabled = false;
  } catch (e) { showError('Не удалось связаться с сервером расчёта.'); }
}

function renderResults(data) {
  document.getElementById('results').hidden = false;
  const kindNames = { pin: 'Шарнирно-неподвижная', roller_y: 'Каток (гориз.)', roller_x: 'Каток (верт.)' };

  const det = data.determinacy;
  let note;
  if (det.deg === 0) note = `Статически определима (m+r−2n=0): ${det.m} стержней, ${det.r} связей, ${det.n} узлов.`;
  else note = `Статически неопределима на ${det.deg} (m+r−2n=${det.deg}) — решено методом конечных элементов.`;
  document.getElementById('determinacy_note').textContent = note;

  const rtb = document.querySelector('#reactions_table tbody'); rtb.innerHTML = '';
  data.reactions.forEach(r => {
    rtb.innerHTML += `<tr><td>${r.node}</td><td>${kindNames[r.kind]}</td><td>${r.Rx.toFixed(1)}</td><td>${r.Ry.toFixed(1)}</td></tr>`;
  });

  const ftb = document.querySelector('#forces_table tbody'); ftb.innerHTML = '';
  data.member_checks.forEach(c => {
    const status = c.ratio <= 1.0 ? '✓' : '⚠ превышение';
    ftb.innerHTML += `<tr><td>${c.i}</td><td>${c.nodes[0]}—${c.nodes[1]}</td><td>${c.N.toFixed(1)}</td>
      <td>${c.sigma_MPa.toFixed(2)}</td><td>${status}</td></tr>`;
  });

  document.getElementById('img_forces').src = data.images.forces;
}

async function downloadReport() {
  if (!lastPayload) return;
  try {
    const resp = await fetch('/api/report', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(lastPayload),
    });
    if (!resp.ok) { const data = await resp.json(); showError(data.error || 'Ошибка формирования записки'); return; }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'Расчёт_фермы.docx';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  } catch (e) { showError('Не удалось связаться с сервером.'); }
}
