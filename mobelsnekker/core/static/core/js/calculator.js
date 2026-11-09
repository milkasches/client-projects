/* Price calculator — renders options from the server and asks /api/estimate for prices */
(function () {
  "use strict";
  const form = document.getElementById("calc");
  if (!form) return;
  const O = JSON.parse(document.getElementById("calc-options").textContent);
  const IMG = window.IW_STATIC || "";
  const $ = (s, r = document) => r.querySelector(s);
  const fmt = (n) => Math.round(n).toLocaleString("nb-NO").replace(/ /g, " ");

  const state = {
    type: O.types[form.dataset.initialType] ? form.dataset.initialType : "wardrobe",
    material: "oak_veneer", finish: "oil", complexity: "standard", hardware: "standard", delivery: "oslo",
    drawers: 0, doors: 0, glass_doors: 0, led: 0,
  };

  /* ---------- rendering helpers ---------- */
  function radios(name, table, extra) {
    const host = form.querySelector(`[data-render="${name}"]`);
    host.innerHTML = "";
    Object.entries(table).forEach(([key, o]) => {
      const lab = document.createElement("label");
      lab.className = "chip";
      lab.innerHTML = `<input type="radio" name="${name}" value="${key}"><span></span>`;
      const span = lab.querySelector("span");
      if (extra) extra(span, key, o); else span.textContent = o.label;
      host.appendChild(lab);
    });
  }

  // types
  (function () {
    const host = form.querySelector('[data-render="types"]');
    Object.entries(O.types).forEach(([key, t]) => {
      const lab = document.createElement("label");
      lab.className = "type-card";
      lab.innerHTML = `<input type="radio" name="type" value="${key}"><span class="tc-img"><img alt="" loading="lazy"></span><span class="tc-txt"><b></b><small></small></span>`;
      lab.querySelector("img").src = IMG + t.img;
      lab.querySelector("b").textContent = t.label;
      lab.querySelector("small").textContent = "from " + fmt(t.from) + " kr";
      host.appendChild(lab);
    });
  })();
  radios("materials", O.materials, (span, k, o) => { span.innerHTML = `<i class="swatch-dot" style="background:${o.swatch}"></i>`; span.append(o.label); });
  form.querySelector('[data-render="materials"]').querySelectorAll("input").forEach((i) => (i.name = "material"));
  radios("finishes", O.finishes); form.querySelectorAll('[data-render="finishes"] input').forEach((i) => (i.name = "finish"));
  radios("hardware", O.hardware);
  radios("delivery", O.delivery);
  (function () {
    const host = form.querySelector('[data-render="complexity"]');
    Object.entries(O.complexity).forEach(([key, c]) => {
      const lab = document.createElement("label");
      lab.className = "cx";
      lab.innerHTML = `<input type="radio" name="complexity" value="${key}"><span><b></b><small></small></span>`;
      lab.querySelector("b").textContent = c.label;
      lab.querySelector("small").textContent = c.hint;
      host.appendChild(lab);
    });
  })();
  (function () {
    const host = form.querySelector('[data-render="extras"]');
    Object.entries(O.extras).forEach(([key, x]) => {
      const row = document.createElement("div");
      row.className = "stepper";
      row.innerHTML = `<span></span><div><button type="button" data-d="-1" aria-label="Less">−</button><input type="number" name="${key}" min="0" max="${x.max}" value="0" inputmode="numeric"><button type="button" data-d="1" aria-label="More">+</button></div>`;
      row.querySelector("span").textContent = x.label;
      row.addEventListener("click", (e) => {
        const b = e.target.closest("button"); if (!b) return;
        const inp = row.querySelector("input");
        inp.value = Math.max(0, Math.min(x.max, (+inp.value || 0) + +b.dataset.d));
        inp.dispatchEvent(new Event("input", { bubbles: true }));
      });
      host.appendChild(row);
    });
  })();

  /* ---------- dimension sliders ---------- */
  const SL = { width: [30, 600, 5], height: [2, 300, 1], depth: [2, 120, 1] };
  Object.entries(SL).forEach(([k, [min, max, step]]) => {
    const r = form[k + "_r"], n = form[k];
    Object.assign(r, { min, max, step }); Object.assign(n, { min, max });
    r.addEventListener("input", () => { n.value = r.value; update(); });
    n.addEventListener("change", () => { n.value = Math.max(min, Math.min(max, +n.value || min)); r.value = n.value; update(); });
  });

  function applyType(key, keepDims) {
    const t = O.types[key];
    state.type = key;
    if (!keepDims) {
      ["width", "height", "depth"].forEach((k, i) => { form[k].value = t.dims[i]; form[k + "_r"].value = t.dims[i]; });
    }
    form.installation.checked = t.install;
    $('[data-dim="depth"] label', form).textContent = key === "wall_panel" ? "Thickness" : "Depth";
  }

  /* ---------- sync form -> state ---------- */
  function setChecked(name, val) {
    const el = form.querySelector(`input[name="${name}"][value="${val}"]`);
    if (el) el.checked = true;
  }
  ["type", "material", "finish", "complexity", "hardware", "delivery"].forEach((n) => setChecked(n, state[n]));
  applyType(state.type);

  form.addEventListener("change", (e) => {
    if (e.target.name === "type") applyType(e.target.value);
    update();
  });
  form.addEventListener("input", (e) => { if (e.target.type === "number" && !SL[e.target.name]) update(); });

  function collect() {
    const fd = new FormData(form);
    const d = {};
    ["type", "material", "finish", "complexity", "hardware", "delivery"].forEach((k) => (d[k] = fd.get(k)));
    ["width", "height", "depth", "floor", ...Object.keys(O.extras)].forEach((k) => (d[k] = +fd.get(k) || 0));
    ["installation", "drawings", "rush", "elevator"].forEach((k) => (d[k] = form[k].checked));
    return d;
  }

  /* ---------- visual box ---------- */
  function drawBox(d) {
    const box = $(".dims-viz .box", form);
    const t = O.types[d.type];
    const w = d.width, h = t.area === "top" ? d.depth : d.height;
    const s = Math.min(260 / w, 150 / h);
    box.style.width = Math.max(24, w * s) + "px";
    box.style.height = Math.max(8, h * s) + "px";
    $(".bw", box).textContent = w + " cm";
    $(".bh", box).textContent = h + " cm";
    box.classList.toggle("top", t.area === "top");
  }

  /* ---------- fetch estimate (debounced, latest wins) ---------- */
  let timer, seq = 0;
  function update() {
    const d = collect();
    drawBox(d);
    $("#sum-lines").classList.add("busy");
    clearTimeout(timer);
    timer = setTimeout(() => request(d), 180);
  }
  async function request(d) {
    const my = ++seq;
    try {
      const res = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": IW.csrf() },
        credentials: "same-origin",
        body: JSON.stringify(d),
      });
      const data = await res.json();
      if (my !== seq) return;
      if (!data.ok) throw new Error(data.error);
      render(data.estimate);
    } catch (err) {
      if (my === seq) IW.toast("Could not calculate the price right now.");
    }
  }

  function render(e) {
    IW.currentEstimate = e;
    $("#sum-title").textContent = e.title;
    animate($("#sum-low"), e.low);
    animate($("#sum-high"), e.high);
    $("#sum-lead").textContent = `ready in ${e.lead_time_weeks[0]}–${e.lead_time_weeks[1]} weeks`;
    $("#sum-total").textContent = fmt(e.total) + " kr";
    $("#sum-vat").textContent = fmt(e.vat) + " kr";
    const ul = $("#sum-lines");
    ul.innerHTML = "";
    e.lines.forEach((l) => {
      const li = document.createElement("li");
      li.innerHTML = "<span></span><b></b>";
      li.firstChild.textContent = l.label;
      li.lastChild.textContent = l.amount ? fmt(Math.round(l.amount * 1.25 / 100) * 100) + " kr" : "free";
      ul.appendChild(li);
    });
    ul.classList.remove("busy");
    $(".area-note", form).textContent = `${O.types[e.input.type].area === "top" ? "Top" : "Front"} area: ${e.area_m2.toLocaleString("nb-NO")} m²`;
    const r = document.getElementById("om-range");
    if (r) { r.textContent = `${fmt(e.low)} – ${fmt(e.high)} kr`; document.getElementById("om-what").textContent = e.lines[0].label; }
  }

  const shown = new WeakMap();
  function animate(el, to) {
    const from = shown.get(el) || 0;
    shown.set(el, to);
    const t0 = performance.now(), dur = 380;
    const step = (t) => {
      const p = Math.min(1, (t - t0) / dur), v = from + (to - from) * (1 - Math.pow(1 - p, 3));
      el.textContent = fmt(Math.round(v / 100) * 100);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  update();
})();
