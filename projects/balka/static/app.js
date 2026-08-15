// ---------- состояние ----------
const state = {
  supports: [],   // {x, kind}
  forces: [],     // {x, value}  (value со знаком: вниз = отрицательное)
  moments: [],    // {x, value}  (value со знаком: против ч.с. = положительное)
  dloads: [],     // {x1,x2,value1,value2}
};
let lastCalc = null;
let lastPayload = null;

// ---------- сечения: динамические поля размеров ----------
const SEC_FIELDS = {
  rectangle: [['b', 'Ширина b, мм', 120], ['h', 'Высота h, мм', 200]],
  circle: [['d', 'Диаметр d, мм', 100]],
  pipe: [['d_out', 'Внешний D, мм', 100], ['d_in', 'Внутренний d, мм', 80]],
  box: [['b_out', 'Ширина b, мм', 100], ['h_out', 'Высота h, мм', 100], ['t', 'Толщина стенки t, мм', 5]],
  i_beam: [['h', 'Высота h, мм', 200], ['b', 'Ширина полки b, мм', 100],
           ['s', 'Толщина стенки s, мм', 6], ['t', 'Толщина полки t, мм', 9]],
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
  document.querySelectorAll('#sec_dims [data-dim]').forEach(inp => {
    dims[inp.dataset.dim] = parseFloat(inp.value);
  });
  return { type, dims };
}

// ---------- добавление элементов ----------
function addSupport() {
  if (state.supports.length >= 4) { showError('Максимум 4 опоры.'); return; }
  const x = parseFloat(document.getElementById('new_sup_x').value);
  const kind = document.getElementById('new_sup_kind').value;
  if (isNaN(x)) { showError('Укажите координату опоры x.'); return; }
  state.supports.push({ x, kind });
  renderLists(); drawPreview();
}
function addForce() {
  const x = parseFloat(document.getElementById('new_f_x').value);
  let v = parseFloat(document.getElementById('new_f_val').value);
  const dir = document.getElementById('new_f_dir').value;
  if (isNaN(x) || isNaN(v)) { showError('Заполните x и значение силы.'); return; }
  v = Math.abs(v) * (dir === 'down' ? -1 : 1);
  state.forces.push({ x, value: v });
  renderLists(); drawPreview();
}
function addMoment() {
  const x = parseFloat(document.getElementById('new_m_x').value);
  let v = parseFloat(document.getElementById('new_m_val').value);
  const dir = document.getElementById('new_m_dir').value;
  if (isNaN(x) || isNaN(v)) { showError('Заполните x и значение момента.'); return; }
  v = Math.abs(v) * (dir === 'ccw' ? 1 : -1);
  state.moments.push({ x, value: v });
  renderLists(); drawPreview();
}
function addDload() {
  const x1 = parseFloat(document.getElementById('new_d_x1').value);
  const x2 = parseFloat(document.getElementById('new_d_x2').value);
  let q1 = parseFloat(document.getElementById('new_d_q1').value);
  let q2raw = document.getElementById('new_d_q2').value;
  let q2 = q2raw === '' ? q1 : parseFloat(q2raw);
  const dir = document.getElementById('new_d_dir').value;
  if (isNaN(x1) || isNaN(x2) || isNaN(q1)) { showError('Заполните x₁, x₂ и q₁.'); return; }
  const sign = dir === 'down' ? -1 : 1;
  state.dloads.push({ x1, x2, value1: Math.abs(q1) * sign, value2: Math.abs(q2) * sign });
  renderLists(); drawPreview();
}

function removeItem(arrName, idx) {
  state[arrName].splice(idx, 1);
  renderLists(); drawPreview();
}

function renderLists() {
  const supBox = document.getElementById('supports_list');
  supBox.innerHTML = '';
  const kindNames = { pin: 'шарнир неподв.', roller: 'шарнир подв.', fixed: 'заделка' };
  state.supports.forEach((s, i) => {
    supBox.innerHTML += `<div class="item-row"><span>x=${s.x} м · ${kindNames[s.kind]}</span>
      <button onclick="removeItem('supports',${i})">×</button></div>`;
  });

  const fBox = document.getElementById('forces_list');
  fBox.innerHTML = '';
  state.forces.forEach((f, i) => {
    fBox.innerHTML += `<div class="item-row"><span>x=${f.x} м · F=${Math.abs(f.value)} Н ${f.value < 0 ? '↓' : '↑'}</span>
      <button onclick="removeItem('forces',${i})">×</button></div>`;
  });

  const mBox = document.getElementById('moments_list');
  mBox.innerHTML = '';
  state.moments.forEach((m, i) => {
    mBox.innerHTML += `<div class="item-row"><span>x=${m.x} м · M=${Math.abs(m.value)} Н·м ${m.value > 0 ? '↺' : '↻'}</span>
      <button onclick="removeItem('moments',${i})">×</button></div>`;
  });

  const dBox = document.getElementById('dloads_list');
  dBox.innerHTML = '';
  state.dloads.forEach((d, i) => {
    dBox.innerHTML += `<div class="item-row"><span>[${d.x1};${d.x2}] м · q=${Math.abs(d.value1)}${d.value1 !== d.value2 ? '…' + Math.abs(d.value2) : ''} Н/м ${d.value1 < 0 || d.value2 < 0 ? '↓' : '↑'}</span>
      <button onclick="removeItem('dloads',${i})">×</button></div>`;
  });
}

function showError(msg) {
  const box = document.getElementById('error_box');
  box.textContent = msg;
  box.hidden = false;
  setTimeout(() => { box.hidden = true; }, 4000);
}

// ---------- canvas-предпросмотр схемы ----------
function drawPreview() {
  const cv = document.getElementById('preview');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const L = parseFloat(document.getElementById('length').value) || 1;
  const marginX = 60, y0 = H / 2;
  const scale = (W - 2 * marginX) / L;
  const X = x => marginX + x * scale;

  ctx.strokeStyle = '#5ec8ff';
  ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(X(0), y0); ctx.lineTo(X(L), y0); ctx.stroke();

  ctx.fillStyle = '#87a0b8';
  ctx.font = '11px IBM Plex Mono';
  ctx.textAlign = 'center';
  ctx.fillText('0 м', X(0), y0 + 45);
  ctx.fillText(L + ' м', X(L), y0 + 45);

  // опоры
  state.supports.forEach(s => {
    const x = X(s.x);
    ctx.strokeStyle = '#eaf1f8'; ctx.fillStyle = '#0a1520'; ctx.lineWidth = 1.5;
    if (s.kind === 'fixed') {
      ctx.beginPath(); ctx.moveTo(x, y0 - 22); ctx.lineTo(x, y0 + 22); ctx.stroke();
      for (let k = -2; k <= 2; k++) {
        ctx.beginPath(); ctx.moveTo(x, y0 + k * 9); ctx.lineTo(x - 10, y0 + k * 9 + 9); ctx.stroke();
      }
    } else {
      ctx.beginPath();
      ctx.moveTo(x, y0); ctx.lineTo(x - 12, y0 + 20); ctx.lineTo(x + 12, y0 + 20); ctx.closePath();
      ctx.stroke();
      if (s.kind === 'roller') {
        ctx.beginPath(); ctx.moveTo(x - 14, y0 + 24); ctx.lineTo(x + 14, y0 + 24); ctx.stroke();
      }
    }
  });

  // силы
  ctx.strokeStyle = '#ff8a3d'; ctx.fillStyle = '#ff8a3d';
  state.forces.forEach(f => {
    const x = X(f.x);
    const up = f.value > 0;
    const y1 = up ? y0 - 45 : y0 + 45;
    const y2 = up ? y0 - 4 : y0 + 4;
    arrow(ctx, x, y1, x, y2);
    ctx.textAlign = 'center';
    ctx.fillText(Math.abs(f.value) + ' Н', x, up ? y1 - 8 : y1 + 16);
  });

  // моменты
  ctx.strokeStyle = '#5ec8ff';
  state.moments.forEach(m => {
    const x = X(m.x);
    const ccw = m.value > 0;
    ctx.beginPath();
    ctx.arc(x, y0 - 30, 16, ccw ? 0.6 : 2.6, ccw ? 2.6 : 0.6, !ccw);
    ctx.stroke();
    ctx.fillStyle = '#5ec8ff';
    ctx.fillText(Math.abs(m.value) + ' Н·м', x, y0 - 54);
  });

  // распределённые нагрузки
  ctx.strokeStyle = '#c9a24b'; ctx.fillStyle = '#c9a24b';
  state.dloads.forEach(d => {
    const xa = X(d.x1), xb = X(d.x2);
    const up = (d.value1 + d.value2) >= 0;
    const top = up ? y0 - 34 : y0 + 34;
    ctx.beginPath(); ctx.moveTo(xa, top); ctx.lineTo(xb, top); ctx.stroke();
    const n = Math.max(3, Math.round((xb - xa) / 24));
    for (let k = 0; k <= n; k++) {
      const xx = xa + (xb - xa) * k / n;
      arrow(ctx, xx, top, xx, up ? y0 - 4 : y0 + 4);
    }
    ctx.textAlign = 'center';
    ctx.fillText('q, Н/м', (xa + xb) / 2, top - 8 * (up ? 1 : -1));
  });
}

function arrow(ctx, x1, y1, x2, y2) {
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  const ang = Math.atan2(y2 - y1, x2 - x1);
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - 6 * Math.cos(ang - 0.4), y2 - 6 * Math.sin(ang - 0.4));
  ctx.lineTo(x2 - 6 * Math.cos(ang + 0.4), y2 - 6 * Math.sin(ang + 0.4));
  ctx.closePath(); ctx.fill();
}

document.getElementById('length').addEventListener('input', drawPreview);
drawPreview();

// ---------- сборка payload и вызов API ----------
function buildPayload() {
  return {
    length: parseFloat(document.getElementById('length').value),
    E: parseFloat(document.getElementById('E_gpa').value) * 1e9,
    sigma_allow: parseFloat(document.getElementById('sigma_allow').value) * 1e6,
    section: getSectionPayload(),
    supports: state.supports,
    forces: state.forces,
    moments: state.moments,
    dloads: state.dloads,
  };
}

async function calculate() {
  const payload = buildPayload();
  if (payload.supports.length < 1) { showError('Добавьте хотя бы одну опору.'); return; }
  lastPayload = payload;
  try {
    const resp = await fetch('/api/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.ok) { showError(data.error || 'Ошибка расчёта'); return; }
    lastCalc = data;
    renderResults(data);
    document.getElementById('btn-report').disabled = false;
  } catch (e) {
    showError('Не удалось связаться с сервером расчёта.');
  }
}

function renderResults(data) {
  document.getElementById('results').hidden = false;
  const tbody = document.querySelector('#reactions_table tbody');
  tbody.innerHTML = '';
  const kindNames = { pin: 'Шарнирно-неподвижная', roller: 'Шарнирно-подвижная', fixed: 'Жёсткая заделка' };
  data.reactions.forEach(r => {
    tbody.innerHTML += `<tr><td>${r.x.toFixed(2)}</td><td>${kindNames[r.kind]}</td>
      <td>${r.R.toFixed(1)}</td><td>${r.kind === 'fixed' ? r.M.toFixed(1) : '—'}</td></tr>`;
  });
  document.getElementById('determinacy_note').textContent = data.determinate
    ? 'Система статически определима — реакции найдены из уравнений равновесия.'
    : 'Система статически неопределима — реакции найдены методом конечных элементов (метод перемещений).';

  document.getElementById('m_Qmax').textContent = data.Qmax.toFixed(1) + ' Н';
  document.getElementById('m_Mmax').textContent = data.Mmax.toFixed(1) + ' Н·м';
  document.getElementById('m_sigma').textContent = data.sigma_max_MPa.toFixed(2) + ' МПа';
  document.getElementById('m_n').textContent = data.safety_factor ? data.safety_factor.toFixed(2) : '—';
  document.getElementById('m_v').textContent = data.v_max_mm.toFixed(3) + ' мм';

  document.getElementById('img_Q').src = data.images.Q;
  document.getElementById('img_M').src = data.images.M;
  document.getElementById('img_D').src = data.images.defl;
}

async function downloadReport() {
  if (!lastPayload) return;
  try {
    const resp = await fetch('/api/report', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastPayload),
    });
    if (!resp.ok) {
      const data = await resp.json();
      showError(data.error || 'Ошибка формирования записки');
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'Расчёт_балки.docx';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    showError('Не удалось связаться с сервером.');
  }
}
