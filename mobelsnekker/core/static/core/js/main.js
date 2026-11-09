/* Møbelsnekker I&W — shared front-end: modals, forms, uploads */
(function () {
  "use strict";
  window.IW = window.IW || {};

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function csrf(form) {
    const el = form && form.querySelector("[name=csrfmiddlewaretoken]");
    if (el) return el.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }
  IW.csrf = csrf;

  /* ---------------- toast ---------------- */
  let toastTimer;
  IW.toast = function (msg) {
    const t = $("#toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 3500);
  };

  /* ---------------- modals ---------------- */
  let lastFocus = null;
  function openModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    lastFocus = document.activeElement;
    resetState(m);
    m.hidden = false;
    requestAnimationFrame(() => m.classList.add("open"));
    document.documentElement.classList.add("modal-open");
    m.dispatchEvent(new CustomEvent("iw:open"));
    const first = m.querySelector("input:not([type=hidden]):not(.hp), select, textarea");
    setTimeout(() => first && first.focus({ preventScroll: true }), 60);
  }
  function closeModal(m) {
    m.classList.remove("open");
    document.documentElement.classList.remove("modal-open");
    setTimeout(() => { m.hidden = true; }, 220);
    if (lastFocus) lastFocus.focus({ preventScroll: true });
  }
  function resetState(m) {
    const f = $("[data-state=form]", m), s = $("[data-state=success]", m);
    if (f && s && !s.hidden) { f.hidden = false; s.hidden = true; }
  }
  IW.openModal = openModal;

  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open]");
    if (opener) { e.preventDefault(); openModal(opener.dataset.open); return; }
    const closer = e.target.closest("[data-close]");
    if (closer) { const m = closer.closest(".modal"); if (m) closeModal(m); }
  });
  document.addEventListener("keydown", (e) => {
    const m = $(".modal.open");
    if (!m) return;
    if (e.key === "Escape") closeModal(m);
    if (e.key === "Tab") { // focus trap
      const f = $$("a[href], button:not([disabled]), input:not([type=hidden]):not(.hp), select, textarea", m)
        .filter((el) => el.offsetParent !== null);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  /* ---------------- date min = today ---------------- */
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  $$(".js-min-today").forEach((i) => (i.min = today));

  /* ---------------- switches ---------------- */
  $$("[data-switch]").forEach((sw) => {
    const form = sw.closest("form");
    const hidden = form.querySelector(`input[name="${sw.dataset.switch}"]`);
    const addr = form.querySelector(".address");
    sw.addEventListener("click", () => {
      const on = sw.getAttribute("aria-checked") !== "true";
      sw.setAttribute("aria-checked", on);
      sw.classList.toggle("on", on);
      hidden.value = on ? "true" : "false";
      if (addr) addr.hidden = !on;
    });
  });

  /* ---------------- file inputs ---------------- */
  const MAX_FILES = 5, MAX_MB = 10;
  $$("[data-drop]").forEach((drop) => {
    const input = drop.querySelector("input[type=file]");
    const list = drop.parentElement.querySelector(".file-list");
    let files = [];
    const render = () => {
      const dt = new DataTransfer();
      files.forEach((f) => dt.items.add(f));
      input.files = dt.files;
      list.innerHTML = "";
      files.forEach((f, i) => {
        const li = document.createElement("li");
        const big = f.size > MAX_MB * 1048576;
        li.className = big ? "bad" : "";
        li.innerHTML = `<span></span><small>${(f.size / 1048576).toFixed(1)} MB${big ? " · too large" : ""}</small><button type="button" aria-label="Remove">×</button>`;
        li.firstChild.textContent = f.name;
        li.querySelector("button").onclick = () => { files.splice(i, 1); render(); };
        list.appendChild(li);
      });
    };
    const add = (fl) => {
      files = files.concat(Array.from(fl)).slice(0, MAX_FILES);
      render();
    };
    input.addEventListener("change", () => { add(input.files); });
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => add(e.dataTransfer.files));
    drop._reset = () => { files = []; render(); };
  });

  /* ---------------- generic ajax forms ---------------- */
  function showErrors(form, errors, message) {
    $$(".field.err, .consent.err", form).forEach((el) => el.classList.remove("err"));
    $$(".field-msg", form).forEach((el) => el.remove());
    const box = $(".form-error", form);
    const general = [];
    Object.entries(errors || {}).forEach(([name, msgs]) => {
      const input = form.querySelector(`[name="${name}"]`);
      const wrap = input && input.closest(".field, .consent");
      if (wrap && name !== "attachments") {
        wrap.classList.add("err");
        const m = document.createElement("em");
        m.className = "field-msg";
        m.textContent = msgs[0];
        wrap.appendChild(m);
      } else general.push(...msgs);
    });
    if (message) general.unshift(message);
    box.textContent = general.join(" ");
    const firstErr = $(".err input, .err textarea, .err select", form);
    if (firstErr) firstErr.focus();
  }

  function clientValidate(form) {
    const errs = {};
    $$("[required]", form).forEach((el) => {
      const empty = el.type === "checkbox" ? !el.checked : !el.value.trim();
      if (empty) errs[el.name] = [el.type === "checkbox" ? "Please accept to continue." : "Required."];
      else if (el.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value)) errs[el.name] = ["Enter a valid email."];
    });
    const tel = form.querySelector("input[type=tel]");
    if (tel && tel.value && tel.value.replace(/\D/g, "").length < 8) errs[tel.name] = ["Enter a valid phone number."];
    return errs;
  }

  $$(".js-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errs = clientValidate(form);
      if (Object.keys(errs).length) { showErrors(form, errs); return; }
      showErrors(form, {});
      if (form.hasAttribute("data-with-estimate") && IW.currentEstimate) {
        form.querySelector("[name=estimate]").value = JSON.stringify({ input: IW.currentEstimate.input });
      }
      const btn = form.querySelector("[type=submit]");
      btn.disabled = true; btn.classList.add("loading");
      try {
        const res = await fetch(form.dataset.endpoint, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-CSRFToken": csrf(form), "X-Requested-With": "fetch" },
          credentials: "same-origin",
        });
        let data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok || !data.ok) {
          let msg = data.error || "";
          if (!msg && !data.errors) {
            msg = res.status === 403
              ? "Your session has expired. Please reload the page (Cmd/Ctrl+R) and send again."
              : `Something went wrong (error ${res.status}). Please try again or call +47 411 92 689.`;
          }
          console.error("Form error", res.status, form.dataset.endpoint);
          showErrors(form, data.errors, msg);
          return;
        }
        onSuccess(form);
      } catch (err) {
        showErrors(form, {}, "No connection. Please check your internet and try again.");
      } finally {
        btn.disabled = false; btn.classList.remove("loading");
      }
    });
  });

  function onSuccess(form) {
    const modal = form.closest(".modal");
    form.reset();
    $$("[data-drop]", form).forEach((d) => d._reset && d._reset());
    $$("[data-switch]", form).forEach((sw) => { if (sw.classList.contains("on")) sw.click(); });
    if (modal) {
      $("[data-state=form]", modal).hidden = true;
      $("[data-state=success]", modal).hidden = false;
      $("[data-state=success] button", modal).focus();
    } else {
      const ok = form.parentElement.querySelector(".form-success");
      form.hidden = true;
      ok.hidden = false;
      ok.scrollIntoView({ behavior: "smooth", block: "center" });
      ok.querySelector(".js-reset").onclick = () => { ok.hidden = true; form.hidden = false; };
    }
  }
})();
