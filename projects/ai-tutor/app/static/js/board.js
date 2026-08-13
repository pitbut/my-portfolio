/* Рендер диаграмм и графиков на доске (тип "diagram"/"graph" из BOARD-блока
 * ответа ИИ-репетитора — раздел 4 ai-tutor-system-prompt.md, этап 9.2 ТЗ).
 * Оба рендерятся из JSON, который прислала модель в поле content, поэтому
 * входные данные валидируются перед использованием — модель иногда может
 * прислать невалидный JSON или мусор вместо выражения. */

const ALLOWED_MATH_WORDS = new Set([
  "sin", "cos", "tan", "sqrt", "abs", "log", "exp", "pow", "pi", "e", "x",
]);

function isSafeExpression(expr) {
  if (typeof expr !== "string" || !expr.trim()) return false;
  if (!/^[0-9x+\-*/^().,\s a-zA-Z]+$/.test(expr)) return false;
  const words = expr.match(/[a-zA-Z]+/g) || [];
  return words.every((w) => ALLOWED_MATH_WORDS.has(w));
}

function compileExpression(expr) {
  // ^ -> ** (возведение в степень в JS), функции берутся из Math через with().
  const jsExpr = expr.replace(/\^/g, "**");
  // eslint-disable-next-line no-new-func
  return new Function("x", `with (Math) { return ${jsExpr}; }`);
}

function renderBoardGraph(canvas, data) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  if (!data || !isSafeExpression(data.expression)) {
    ctx.fillStyle = "#9797b8";
    ctx.font = "16px sans-serif";
    ctx.fillText("Не удалось построить график.", 16, 30);
    return;
  }

  const xMin = Number.isFinite(data.x_min) ? data.x_min : -10;
  const xMax = Number.isFinite(data.x_max) ? data.x_max : 10;
  const fn = compileExpression(data.expression);

  const steps = 300;
  const points = [];
  for (let i = 0; i <= steps; i++) {
    const x = xMin + ((xMax - xMin) * i) / steps;
    let y;
    try {
      y = fn(x);
    } catch (e) {
      y = NaN;
    }
    if (Number.isFinite(y)) points.push({ x, y });
  }

  if (!points.length) {
    ctx.fillStyle = "#9797b8";
    ctx.font = "16px sans-serif";
    ctx.fillText("Функция не определена на этом диапазоне.", 16, 30);
    return;
  }

  let yMin = Math.min(...points.map((p) => p.y));
  let yMax = Math.max(...points.map((p) => p.y));
  if (yMin === yMax) { yMin -= 1; yMax += 1; }
  const yPad = (yMax - yMin) * 0.1;
  yMin -= yPad; yMax += yPad;

  const pad = 30;
  const toPx = (x, y) => [
    pad + ((x - xMin) / (xMax - xMin)) * (width - 2 * pad),
    height - pad - ((y - yMin) / (yMax - yMin)) * (height - 2 * pad),
  ];

  // Оси
  ctx.strokeStyle = "#d8d8ea";
  ctx.lineWidth = 1;
  if (yMin < 0 && yMax > 0) {
    const [x0, y0] = toPx(xMin, 0);
    const [x1, y1] = toPx(xMax, 0);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
  }
  if (xMin < 0 && xMax > 0) {
    const [x0, y0] = toPx(0, yMin);
    const [x1, y1] = toPx(0, yMax);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
  }

  // Кривая
  ctx.strokeStyle = "#5b7cff";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  points.forEach((p, i) => {
    const [px, py] = toPx(p.x, p.y);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  });
  ctx.stroke();

  // Отмеченные точки
  (data.points || []).slice(0, 5).forEach((point) => {
    if (!Number.isFinite(point.x)) return;
    let y;
    try { y = fn(point.x); } catch (e) { return; }
    if (!Number.isFinite(y)) return;
    const [px, py] = toPx(point.x, y);
    ctx.fillStyle = "#ffb454";
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, 2 * Math.PI);
    ctx.fill();
    if (point.label) {
      ctx.fillStyle = "#4a4a68";
      ctx.font = "12px sans-serif";
      ctx.fillText(point.label, px + 6, py - 6);
    }
  });

  if (data.title) {
    ctx.fillStyle = "#4a4a68";
    ctx.font = "13px sans-serif";
    ctx.fillText(data.title, 10, 16);
  }
}

function renderBoardDiagram(container, data) {
  container.innerHTML = "";
  const nodes = Array.isArray(data && data.nodes) ? data.nodes.slice(0, 8) : [];
  const edges = Array.isArray(data && data.edges) ? data.edges : [];

  if (!nodes.length) {
    container.textContent = "Не удалось построить схему.";
    return;
  }

  const row = document.createElement("div");
  row.className = "diagram-row";

  const byId = {};
  nodes.forEach((node, i) => {
    const box = document.createElement("div");
    box.className = "diagram-node";
    box.textContent = node.label || node.id || `Узел ${i + 1}`;
    byId[node.id] = box;
    row.appendChild(box);

    const nextEdge = edges.find((e) => e.from === node.id && byId[e.to] === undefined);
    const isLastInRow = i === nodes.length - 1;
    if (!isLastInRow) {
      const connector = document.createElement("div");
      connector.className = "diagram-arrow";
      connector.textContent = nextEdge && nextEdge.label ? `→ ${nextEdge.label} →` : "→";
      row.appendChild(connector);
    }
  });
  container.appendChild(row);

  // Связи, не отражённые соседними узлами в ряду (нелинейные схемы) —
  // отдельным списком под рядом, чтобы не терять информацию.
  const shownPairs = new Set(nodes.slice(0, -1).map((n, i) => `${n.id}->${nodes[i + 1].id}`));
  const extra = edges.filter((e) => !shownPairs.has(`${e.from}->${e.to}`));
  if (extra.length) {
    const list = document.createElement("ul");
    list.className = "diagram-extra-edges";
    extra.forEach((e) => {
      const li = document.createElement("li");
      const fromLabel = (byId[e.from] && byId[e.from].textContent) || e.from;
      const toLabel = (byId[e.to] && byId[e.to].textContent) || e.to;
      li.textContent = `${fromLabel} → ${toLabel}${e.label ? ": " + e.label : ""}`;
      list.appendChild(li);
    });
    container.appendChild(list);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const boardEl = document.querySelector("[data-board-type]");
  if (!boardEl || typeof window.__boardData === "undefined") return;

  const boardType = boardEl.dataset.boardType;
  let data = null;
  try {
    data = JSON.parse(window.__boardData);
  } catch (e) {
    boardEl.textContent = "Не удалось разобрать данные доски.";
    return;
  }

  if (boardType === "graph") {
    const canvas = document.createElement("canvas");
    canvas.width = boardEl.clientWidth || 560;
    canvas.height = 320;
    boardEl.innerHTML = "";
    boardEl.appendChild(canvas);
    renderBoardGraph(canvas, data);
  } else if (boardType === "diagram") {
    renderBoardDiagram(boardEl, data);
  }
});
