(() => {
  let DATA = null;

  // ---------- утилиты ----------
  function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "text") e.textContent = v;
      else e.setAttribute(k, v);
    }
    children.forEach((c) => e.appendChild(c));
    return e;
  }
  function fmt(n, nd = 1) {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    return Number(n).toLocaleString("ru-RU", { maximumFractionDigits: nd, minimumFractionDigits: 0 });
  }
  function table(headers, rows) {
    const t = el("table");
    const thead = el("tr");
    headers.forEach((h) => thead.appendChild(el("th", { text: h })));
    t.appendChild(el("thead", {}, [thead]));
    const tbody = el("tbody");
    rows.forEach((r) => {
      const tr = el("tr");
      r.forEach((c) => tr.appendChild(el("td", { text: c })));
      tbody.appendChild(tr);
    });
    t.appendChild(tbody);
    return t;
  }

  // ---------- вкладки ----------
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("is-active", b === btn));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("is-active"));
      document.getElementById("tab-" + btn.dataset.tab).classList.add("is-active");
    });
  });

  // ---------- загрузка справочников ----------
  async function loadData() {
    const res = await fetch("/api/data");
    DATA = await res.json();
    populateFeedUI();
    populateCropUI();
  }

  // ===================== переключатели режима (кнопки, не select) =====================
  function setupModeSwitch(containerId, blockPrefix, onChange) {
    const container = document.getElementById(containerId);
    let current = container.querySelector(".mode-btn.is-active").dataset.mode;
    function apply() {
      container.querySelectorAll(".mode-btn").forEach((b) => {
        const active = b.dataset.mode === current;
        b.classList.toggle("is-active", active);
        const block = document.getElementById(blockPrefix + b.dataset.mode);
        if (block) block.style.display = active ? "" : "none";
      });
      if (onChange) onChange(current);
    }
    container.querySelectorAll(".mode-btn").forEach((b) => {
      b.addEventListener("click", () => { current = b.dataset.mode; apply(); });
    });
    apply();
    return { get: () => current };
  }

  // ===================== КОРМ =====================
  const feedAnimalSel = document.getElementById("feed-animal");
  const feedWeight = document.getElementById("feed-weight");
  const feedOutput = document.getElementById("feed-output");
  const feedOutputLabel = document.getElementById("feed-output-label");
  const feedOutputPriceLabel = document.getElementById("feed-output-price-label");
  const feedBudgetInputs = document.getElementById("feed-budget-inputs");
  const feedPriceInputs = document.getElementById("feed-price-inputs");
  const feedMode = setupModeSwitch("feed-mode-switch", "feed-mode-");

  function populateFeedUI() {
    feedAnimalSel.innerHTML = "";
    Object.entries(DATA.animals).forEach(([id, a]) => {
      feedAnimalSel.appendChild(el("option", { value: id, text: a.label }));
    });
    feedBudgetInputs.innerHTML = "";
    feedPriceInputs.innerHTML = "";
    Object.entries(DATA.feed_types).forEach(([id, f]) => {
      const wrap = el("div");
      wrap.appendChild(el("label", { text: f.label }));
      const input = el("input", { type: "number", step: "1", "data-feed": id, value: "0", min: "0" });
      wrap.appendChild(input);
      feedBudgetInputs.appendChild(wrap);

      const pwrap = el("div");
      pwrap.appendChild(el("label", { text: f.label + ", ₽/кг" }));
      const pinput = el("input", { type: "number", step: "0.1", "data-feed-price": id, min: "0" });
      pwrap.appendChild(pinput);
      feedPriceInputs.appendChild(pwrap);
    });
    onFeedAnimalChange();
  }

  function onFeedAnimalChange() {
    const a = DATA.animals[feedAnimalSel.value];
    feedWeight.value = a.weight_default;
    feedWeight.min = a.weight_min;
    feedWeight.max = a.weight_max;
    feedOutput.value = a.production.default;
    feedOutputLabel.textContent = "Продуктивность на голову: " + a.production.unit_label;
    feedOutputPriceLabel.textContent = "Цена за единицу продукции (" + a.production.unit_label + "), ₽";
  }
  feedAnimalSel.addEventListener("change", onFeedAnimalChange);

  function collectFeedPayload() {
    const mode = feedMode.get();
    const payload = {
      mode,
      animal_id: feedAnimalSel.value,
      weight: feedWeight.value,
      regime: document.getElementById("feed-regime").value,
      days: document.getElementById("feed-days").value,
      output_per_head: feedOutput.value,
      author: document.getElementById("feed-author").value,
      date: document.getElementById("feed-date").value,
    };
    if (mode === "forward") {
      payload.count = document.getElementById("feed-count").value;
    } else if (mode === "reverse_budget") {
      const budget = {};
      feedBudgetInputs.querySelectorAll("input").forEach((inp) => {
        budget[inp.dataset.feed] = inp.value;
      });
      payload.budget_kg_by_feed = budget;
    } else if (mode === "reverse_target") {
      payload.target_total_output = document.getElementById("feed-target").value;
    }
    const feed_prices = {};
    feedPriceInputs.querySelectorAll("input").forEach((inp) => { feed_prices[inp.dataset.feedPrice] = inp.value || 0; });
    payload.feed_prices = feed_prices;
    payload.output_price = document.getElementById("feed-output-price").value || 0;
    return payload;
  }

  function renderFeedResult(data, econ) {
    const box = document.getElementById("feed-result");
    box.innerHTML = "";
    const animal = DATA.animals[data.animal_id || feedAnimalSel.value];

    if (data.max_count !== undefined) {
      box.appendChild(el("div", { class: "headline", html: "" }));
      box.lastChild.innerHTML = `Хватит на <span class="num">${fmt(data.max_count, 0)}</span> голов на ${data.days} суток`;
      if (data.forward_check) data = data.forward_check;
    }
    if (data.required_count !== undefined) {
      box.appendChild(el("div", { class: "headline" }));
      box.lastChild.innerHTML = `Нужно <span class="num">${fmt(data.required_count, 0)}</span> голов, чтобы получить ${fmt(data.target_total_output)}`;
    }

    box.appendChild(el("h4", { text: "Суточная потребность на 1 голову" }));
    box.appendChild(table(["Показатель", "Значение"], [
      ["ЭКЕ на поддержание", fmt(data.per_head.maintenance_efu) + " ЭКЕ/сут"],
      ["ЭКЕ на продукцию", fmt(data.per_head.production_efu) + " ЭКЕ/сут"],
      ["Итого ЭКЕ/сутки", fmt(data.per_head.total_efu_per_head) + " ЭКЕ/сут"],
    ]));

    box.appendChild(el("h4", { text: "Рацион на 1 голову в сутки" }));
    const rationRows = Object.entries(data.per_head.feed_kg_per_head)
      .filter(([, kg]) => kg > 0.001)
      .map(([f, kg]) => [DATA.feed_types[f].label, fmt(kg, 2) + " кг"]);
    box.appendChild(table(["Вид корма", "кг/сутки"], rationRows));

    if (data.count) {
      box.appendChild(el("h4", { text: `Итого на всё поголовье (${data.count} гол.) за ${data.days} сут.` }));
      const totalRows = Object.entries(data.feed_kg_period_all)
        .filter(([, kg]) => kg > 0.01)
        .map(([f, kg]) => [DATA.feed_types[f].label, fmt(kg, 1) + " кг"]);
      box.appendChild(table(["Вид корма", "кг за период"], totalRows));
    }

    if (econ) {
      box.appendChild(el("h4", { text: "Экономика" }));
      const costRows = Object.entries(econ.feed_cost_breakdown)
        .filter(([, cost]) => cost > 0)
        .map(([f, cost]) => [DATA.feed_types[f].label, fmt(cost, 0) + " ₽"]);
      if (costRows.length) box.appendChild(table(["Вид корма", "Затраты"], costRows));
      box.appendChild(table(["Показатель", "Значение"], [
        ["Затраты на корм всего", fmt(econ.feed_cost, 0) + " ₽"],
        ["Выручка от продукции", fmt(econ.revenue, 0) + " ₽"],
        ["Прибыль", fmt(econ.profit, 0) + " ₽"],
      ]));
    }
  }

  document.getElementById("feed-calc-btn").addEventListener("click", async () => {
    const errEl = document.getElementById("feed-error");
    errEl.textContent = "";
    try {
      const res = await fetch("/api/feed/calculate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectFeedPayload()),
      });
      const data = await res.json();
      if (!data.ok) { errEl.textContent = data.error || "Ошибка расчёта"; return; }
      renderFeedResult(data.result, data.econ);
    } catch (e) {
      errEl.textContent = "Ошибка соединения.";
    }
  });

  document.getElementById("feed-report-btn").addEventListener("click", async () => {
    const errEl = document.getElementById("feed-error");
    errEl.textContent = "";
    try {
      const res = await fetch("/api/feed/report", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectFeedPayload()),
      });
      if (!res.ok) { const d = await res.json(); errEl.textContent = d.error || "Ошибка отчёта"; return; }
      const blob = await res.blob();
      const a = el("a", { href: URL.createObjectURL(blob), download: "Расчёт_кормления.docx" });
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) {
      errEl.textContent = "Ошибка соединения.";
    }
  });

  // ===================== ПОСЕВ =====================
  const cropCropSel = document.getElementById("crop-crop");
  const cropYield = document.getElementById("crop-yield");
  const cropFertInputs = document.getElementById("crop-fertilizer-inputs");
  const priceFertInputs = document.getElementById("price-fert-inputs");
  const cropMode = setupModeSwitch("crop-mode-switch", "crop-mode-");

  const NUTRIENT_LABELS = { N: "Азот (N)", P2O5: "Фосфор (P₂O₅)", K2O: "Калий (K₂О)" };

  function populateCropUI() {
    cropCropSel.innerHTML = "";
    Object.entries(DATA.crops).forEach(([id, c]) => {
      cropCropSel.appendChild(el("option", { value: id, text: c.label }));
    });
    cropFertInputs.innerHTML = "";
    priceFertInputs.innerHTML = "";
    Object.entries(DATA.fertilizers).forEach(([nutrient, options]) => {
      const wrap = el("div");
      wrap.appendChild(el("label", { text: NUTRIENT_LABELS[nutrient] || nutrient }));
      const sel = el("select", { "data-nutrient": nutrient, id: "fert-" + nutrient });
      options.forEach((o) => sel.appendChild(el("option", { value: o.id, text: o.label })));
      wrap.appendChild(sel);
      cropFertInputs.appendChild(wrap);

      const pwrap = el("div");
      pwrap.appendChild(el("label", { text: "Цена " + (NUTRIENT_LABELS[nutrient] || nutrient) + ", ₽/кг продукта" }));
      const pinput = el("input", { type: "number", step: "0.1", "data-nutrient-price": nutrient });
      pwrap.appendChild(pinput);
      priceFertInputs.appendChild(pwrap);
    });
    onCropChange();
  }

  function onCropChange() {
    const c = DATA.crops[cropCropSel.value];
    cropYield.value = c.yield_t_ha;
    cropYield.placeholder = "по умолчанию " + c.yield_t_ha;
  }
  cropCropSel.addEventListener("change", onCropChange);

  function collectCropPayload() {
    const mode = cropMode.get();
    const fertilizer_choice = {};
    cropFertInputs.querySelectorAll("select").forEach((s) => { fertilizer_choice[s.dataset.nutrient] = s.value; });
    const fert_price_per_kg = {};
    priceFertInputs.querySelectorAll("input").forEach((i) => { fert_price_per_kg[i.dataset.nutrientPrice] = i.value || 0; });

    const payload = {
      mode,
      crop_id: cropCropSel.value,
      yield_t_ha: cropYield.value,
      sowing_date: document.getElementById("crop-sowing-date").value,
      fertilizer_choice,
      author: document.getElementById("crop-author").value,
      date: document.getElementById("crop-date").value,
      prices: {
        price_per_t: document.getElementById("price-per-t").value || 0,
        seed_price_per_kg: document.getElementById("price-seed").value || 0,
        water_price_per_m3: document.getElementById("price-water").value || 0,
        daily_wage: document.getElementById("price-wage").value || 0,
        fert_price_per_kg,
      },
    };
    if (mode === "forward") payload.area_ha = document.getElementById("crop-area").value;
    else payload.target_total_yield_t = document.getElementById("crop-target").value;
    return payload;
  }

  function renderCropResult(data, econ) {
    const box = document.getElementById("crop-result");
    box.innerHTML = "";
    const crop = DATA.crops[data.crop_id] || DATA.crops[cropCropSel.value];

    if (data.required_area_ha !== undefined) {
      box.appendChild(el("div", { class: "headline" }));
      box.lastChild.innerHTML = `Нужно <span class="num">${fmt(data.required_area_ha, 3)} га</span>, чтобы собрать ${fmt(data.target_total_yield_t)} т`;
    } else {
      box.appendChild(el("div", { class: "headline" }));
      box.lastChild.innerHTML = `Ожидаемый сбор: <span class="num">${fmt(data.total_yield_t, 2)} т</span>`;
    }

    box.appendChild(el("h4", { text: "Семена" }));
    box.appendChild(table(["Показатель", "Значение"], [
      ["Площадь, га", fmt(data.area_ha, 3)],
      ["Норма высева, кг/га", crop.seeding_rate_kg_ha],
      ["Нужно семян всего", fmt(data.seed_kg, 1) + " кг"],
    ]));

    box.appendChild(el("h4", { text: "Удобрения (по выносу с урожаем)" }));
    const nutrientRows = Object.entries(data.nutrient_kg).map(([n, kg]) => [NUTRIENT_LABELS[n] || n, fmt(kg, 1) + " кг д.в."]);
    box.appendChild(table(["Элемент", "кг действующего вещества"], nutrientRows));
    const fertRows = Object.values(data.fertilizer_products).map((p) => [p.fertilizer_label, fmt(p.product_kg, 1) + " кг"]);
    if (fertRows.length) box.appendChild(table(["Удобрение", "кг товарного продукта"], fertRows));

    box.appendChild(el("h4", { text: "Вода и трудозатраты" }));
    box.appendChild(table(["Показатель", "Значение"], [
      ["Вода за сезон (осадки + полив)", fmt(data.water_m3, 0) + " м³"],
      ["Трудозатраты", fmt(data.labor_days, 1) + " чел.-дней"],
    ]));

    if (data.harvest_range) {
      box.appendChild(el("h4", { text: "Календарь созревания" }));
      box.appendChild(table(["Посев", "Ожидаемая уборка"], [[data.sowing_date, `${data.harvest_range[0]} — ${data.harvest_range[1]}`]]));
    }

    if (econ) {
      box.appendChild(el("h4", { text: "Экономика" }));
      box.appendChild(table(["Статья", "Сумма, ₽"], [
        ["Выручка", fmt(econ.revenue, 0)],
        ["Затраты на семена", fmt(econ.seed_cost, 0)],
        ["Затраты на удобрения", fmt(econ.fert_cost, 0)],
        ["Затраты на воду", fmt(econ.water_cost, 0)],
        ["Оплата труда", fmt(econ.labor_cost, 0)],
        ["Итого затрат", fmt(econ.total_cost, 0)],
        ["Прибыль", fmt(econ.profit, 0)],
      ]));
    }
  }

  document.getElementById("crop-calc-btn").addEventListener("click", async () => {
    const errEl = document.getElementById("crop-error");
    errEl.textContent = "";
    try {
      const res = await fetch("/api/crop/calculate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectCropPayload()),
      });
      const data = await res.json();
      if (!data.ok) { errEl.textContent = data.error || "Ошибка расчёта"; return; }
      renderCropResult(data.result, data.econ);
    } catch (e) {
      errEl.textContent = "Ошибка соединения.";
    }
  });

  document.getElementById("crop-report-btn").addEventListener("click", async () => {
    const errEl = document.getElementById("crop-error");
    errEl.textContent = "";
    try {
      const res = await fetch("/api/crop/report", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectCropPayload()),
      });
      if (!res.ok) { const d = await res.json(); errEl.textContent = d.error || "Ошибка отчёта"; return; }
      const blob = await res.blob();
      const a = el("a", { href: URL.createObjectURL(blob), download: "Расчёт_посева.docx" });
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) {
      errEl.textContent = "Ошибка соединения.";
    }
  });

  loadData();
})();
