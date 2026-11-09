/* Møbelsnekker I&W — light motion layer (no libraries).
   Loader, split-text headings, scroll reveals, parallax, scroll-reactive marquee,
   magnetic CTAs, hide-on-scroll nav. Respects prefers-reduced-motion. */
(function () {
  "use strict";
  const root = document.documentElement;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = window.matchMedia("(pointer: fine)").matches;
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  if (reduce) return; // content is fully visible without this file

  root.classList.add("anim");

  /* ---------- 1. Loader (once per session, < 1s) ---------- */
  let seen = false;
  try { seen = sessionStorage.getItem("iw-loaded") === "1"; sessionStorage.setItem("iw-loaded", "1"); } catch (_) {}
  const startIntro = () => root.classList.add("intro");
  if (!seen && document.querySelector(".hero, .calc-hero")) {
    const l = document.createElement("div");
    l.className = "loader";
    l.innerHTML = '<div class="loader-in"><span class="lw">I&amp;W</span><svg class="ls"><use href="#star"/></svg></div>';
    document.body.appendChild(l);
    requestAnimationFrame(() => l.classList.add("go"));
    setTimeout(() => { l.classList.add("out"); startIntro(); }, 750);
    setTimeout(() => l.remove(), 1500);
  } else {
    requestAnimationFrame(startIntro);
  }

  /* ---------- 2. Split headings into masked words ---------- */
  function split(el) {
    if (el.dataset.split) return;
    el.dataset.split = "1";
    let i = 0;
    const walk = (node) => {
      Array.from(node.childNodes).forEach((n) => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            const w = document.createElement("span");
            w.className = "w";
            const inner = document.createElement("span");
            inner.className = "wi";
            inner.style.setProperty("--i", i++);
            inner.textContent = part;
            w.appendChild(inner);
            frag.appendChild(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && !n.matches("svg, br, small")) {
          walk(n);
        }
      });
    };
    walk(el);
    el.classList.add("split");
  }
  $$(".hero h1, .sec-head h2, .steps h2, .about h2, .contact h2, .calc-hero h1, .coll-board .t").forEach(split);

  /* ---------- 3. Scroll reveals ---------- */
  const groups = [
    [".hero .eyebrow, .hero-copy > div > *, .facts > div, .hero-photo", "up"],
    [".sec-head p, .coll-foot > *, .calc-band, .about p, .about .eyebrow, .about .btn", "up"],
    [".svc .card, .plans .plan, .rv .r, .ben > div", "up"],
    [".bento .tile", "clip"],
    [".step", "line"],
    [".coll-board img, .coll-board .tag", "pop"],
    [".about .imgs img", "clip"],
    [".contact .form, .contact .side", "up"],
    ["footer .fgrid > div", "up"],
    [".calc-step, .sum-card", "up"],
  ];
  const targets = [];
  groups.forEach(([sel, kind]) => {
    // stagger siblings that share a parent
    const byParent = new Map();
    $$(sel).forEach((el) => {
      if (el.closest(".modal")) return;
      el.classList.add("rv-" + kind);
      const k = el.parentElement;
      const n = byParent.get(k) || 0;
      byParent.set(k, n + 1);
      el.style.setProperty("--d", Math.min(n, 6) * 80 + "ms");
      targets.push(el);
    });
  });
  $$("h1.split, h2.split, .coll-board .t.split").forEach((el) => targets.push(el));

  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
  targets.forEach((t) => io.observe(t));

  /* ---------- 4. Scroll-driven effects (one rAF loop) ---------- */
  const par = $$(".hero-photo img, .bento .tile img, .about .imgs img, .card .ph img").map((img) => ({ img, box: img.parentElement, k: 0.08 }));
  const floaters = $$(".coll-board img").map((img, i) => ({ img, k: [0.06, -0.05, 0.09, -0.07][i % 4] }));
  const stars = $$(".steps .star, .calc-hero .star, .marquee svg");
  const contactBg = document.querySelector(".contact .bg");
  const track = document.querySelector(".marquee .track");
  const nav = document.querySelector(".nav");
  const big = document.querySelector(".bigword");

  let lastY = window.scrollY, vel = 0, mx = 0, ticking = false;
  const vh = () => window.innerHeight;

  if (track) track.style.animation = "none";

  function frame() {
    const y = window.scrollY;
    const dy = y - lastY;
    lastY = y;
    vel += (dy - vel) * 0.12;

    // parallax inside image frames
    par.forEach(({ img, box, k }) => {
      const r = box.getBoundingClientRect();
      if (r.bottom < 0 || r.top > vh()) return;
      const p = (r.top + r.height / 2 - vh() / 2) / vh();
      img.style.transform = `translate3d(0, ${(-p * r.height * k).toFixed(1)}px, 0) scale(${1 + k * 1.6})`;
    });
    floaters.forEach(({ img, k }) => {
      const r = img.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh() + 200) return;
      const p = (r.top - vh() / 2);
      img.style.translate = `0 ${(p * k).toFixed(1)}px`;
    });
    if (contactBg) {
      const r = contactBg.parentElement.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh()) contactBg.style.transform = `translate3d(0, ${(r.top * -0.12).toFixed(1)}px, 0) scale(1.15)`;
    }
    // stars spin with scroll
    stars.forEach((s) => (s.style.rotate = (y * 0.25) % 360 + "deg"));

    // marquee: base speed + scroll velocity
    if (track) {
      mx -= 0.6 + Math.min(18, Math.abs(vel) * 0.35);
      const half = track.scrollWidth / 2;
      if (-mx >= half) mx += half;
      track.style.transform = `translate3d(${mx.toFixed(1)}px,0,0)`;
    }

    // big footer word slides in
    if (big) {
      const r = big.getBoundingClientRect();
      if (r.top < vh()) big.style.transform = `translate3d(${Math.max(0, (r.top - vh() * 0.55) * 0.35).toFixed(1)}px,0,0)`;
    }

    // nav: hide on scroll down, show on scroll up
    if (nav && !root.classList.contains("modal-open")) {
      if (y > 140 && dy > 4) nav.classList.add("nav-hide");
      else if (dy < -4 || y < 140) nav.classList.remove("nav-hide");
      nav.classList.toggle("nav-solid", y > 20);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  /* ---------- 5. Magnetic buttons + image tilt (desktop only) ---------- */
  if (fine) {
    $$(".btn.lime, .modal-x").forEach((b) => {
      b.addEventListener("mousemove", (e) => {
        const r = b.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * 0.18;
        const y = (e.clientY - r.top - r.height / 2) * 0.3;
        b.style.translate = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
      });
      b.addEventListener("mouseleave", () => (b.style.translate = "0 0"));
    });

    // custom cursor label over project tiles
    const cur = document.createElement("div");
    cur.className = "cursor-dot";
    cur.textContent = "View";
    document.body.appendChild(cur);
    let cx = 0, cy = 0, tx = 0, ty = 0;
    document.addEventListener("mousemove", (e) => { tx = e.clientX; ty = e.clientY; });
    (function loop() {
      cx += (tx - cx) * 0.2; cy += (ty - cy) * 0.2;
      cur.style.transform = `translate3d(${cx}px, ${cy}px, 0) translate(-50%, -50%)`;
      requestAnimationFrame(loop);
    })();
    $$(".bento .tile, .svc .card .ph").forEach((t) => {
      t.addEventListener("mouseenter", () => { cur.textContent = t.closest(".svc") ? "Quote" : "View"; cur.classList.add("on"); });
      t.addEventListener("mouseleave", () => cur.classList.remove("on"));
    });
  }

  /* ---------- 6. Price counters in the plans ---------- */
  $$(".plan .price").forEach((el) => {
    const node = el.firstChild;
    if (!node || node.nodeType !== 3) return;
    const text = node.textContent;
    const m = text.match(/\d[\d ]*\d/);
    if (!m) return;
    const target = parseInt(m[0].replace(/ /g, ""), 10);
    if (target < 1000) return;
    const pre = text.slice(0, m.index), post = text.slice(m.index + m[0].length);
    const fmt = (n) => n.toLocaleString("nb-NO").replace(/\u00a0/g, " ");
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      obs.disconnect();
      const t0 = performance.now();
      (function tick(t) {
        const p = Math.min(1, (t - t0) / 1100), v = target * (1 - Math.pow(1 - p, 3));
        node.textContent = pre + fmt(p < 1 ? Math.round(v / 100) * 100 : target) + post;
        if (p < 1) requestAnimationFrame(tick);
      })(t0);
    }, { threshold: 0.6 });
    obs.observe(el);
  });
})();
