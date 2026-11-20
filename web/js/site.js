/* Stolařství Kubiš — sdílený skript všech stránek: menu, lightbox, poptávkové formuláře */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // Directory URLs on the host correspond to index.html files in a local preview.
  if (location.protocol === "file:") {
    const webRoot = new URL("../", document.currentScript.src);
    const localizeLink = (link) => {
      const href = link?.getAttribute("href");
      if (
        !href ||
        href.startsWith("#") ||
        href.startsWith("//") ||
        /^[a-z][a-z0-9+.-]*:/i.test(href)
      )
        return;
      const url = href.startsWith("/")
        ? new URL(href.slice(1), webRoot)
        : new URL(href, location.href);
      if (url.pathname.endsWith("/")) url.pathname += "index.html";
      link.href = url.href;
    };
    $$("a[href]").forEach(localizeLink);
    for (const event of ["click", "auxclick", "contextmenu"]) {
      document.addEventListener(event, (e) => localizeLink(e.target.closest("a")), true);
    }
  }

  /* ---------- hlavní menu s podnabídkami ---------- */
  $$("nav.main li.has-sub > button").forEach((b) => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const li = b.parentElement,
        open = !li.classList.contains("open");
      $$("nav.main li.open").forEach((x) => {
        x.classList.remove("open");
        x.querySelector("button").setAttribute("aria-expanded", "false");
      });
      li.classList.toggle("open", open);
      b.setAttribute("aria-expanded", String(open));
    });
  });
  document.addEventListener("click", () =>
    $$("nav.main li.open").forEach((x) => {
      x.classList.remove("open");
      x.querySelector("button").setAttribute("aria-expanded", "false");
    }),
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape")
      $$("nav.main li.open").forEach((x) => {
        x.classList.remove("open");
        x.querySelector("button").setAttribute("aria-expanded", "false");
        x.querySelector("button").focus();
      });
  });

  /* ---------- mobilní menu ---------- */
  const burger = $(".burger"),
    drawer = $("#drawer");
  if (burger && drawer) {
    const closeDrawer = () => drawer.close();
    burger.addEventListener("click", () => {
      drawer.showModal();
      burger.setAttribute("aria-expanded", "true");
      document.body.classList.add("no-scroll");
      drawer.querySelector(".close").focus();
    });
    drawer.querySelector(".close").addEventListener("click", closeDrawer);
    drawer.addEventListener("click", (event) => {
      if (event.target.closest("a")) closeDrawer();
      else if (event.target === drawer && event.clientX < drawer.getBoundingClientRect().left)
        closeDrawer();
    });
    drawer.addEventListener("close", () => {
      burger.setAttribute("aria-expanded", "false");
      document.body.classList.remove("no-scroll");
    });
    matchMedia("(min-width:721px)").addEventListener("change", (event) => {
      if (event.matches && drawer.open) closeDrawer();
    });
  }

  /* ---------- lightbox ---------- */
  const lb = document.createElement("div");
  lb.className = "lb";
  lb.hidden = true;
  lb.setAttribute("role", "dialog");
  lb.setAttribute("aria-modal", "true");
  lb.setAttribute("aria-label", "Fotografie");
  lb.innerHTML =
    '<div class="lb-top"><span class="lb-count"></span><button type="button" class="close" aria-label="Zavřít">✕</button></div><div class="lb-stage"><img alt=""></div><div class="lb-cap"></div><button type="button" class="prev" aria-label="Předchozí fotka">‹</button><button type="button" class="next" aria-label="Další fotka">›</button>';
  document.body.appendChild(lb);
  let group = [],
    idx = 0,
    opener = null;
  const show = (i) => {
    idx = (i + group.length) % group.length;
    const a = group[idx];
    const img = lb.querySelector("img");
    img.src = a.getAttribute("href");
    img.alt = a.querySelector("img")?.alt || "";
    lb.querySelector(".lb-cap").textContent = a.dataset.cap || a.querySelector("img")?.alt || "";
    lb.querySelector(".lb-count").textContent = `${idx + 1} / ${group.length}`;
    const multi = group.length > 1;
    lb.querySelector(".prev").hidden = !multi;
    lb.querySelector(".next").hidden = !multi;
  };
  const close = () => {
    lb.hidden = true;
    document.body.classList.remove("no-scroll");
    opener?.focus();
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-lb]");
    if (!a) return;
    e.preventDefault();
    opener = a;
    group = $$(`a[data-lb="${a.dataset.lb}"]`);
    lb.hidden = false;
    document.body.classList.add("no-scroll");
    show(group.indexOf(a));
    lb.querySelector(".close").focus();
  });
  lb.querySelector(".close").addEventListener("click", close);
  lb.querySelector(".prev").addEventListener("click", () => show(idx - 1));
  lb.querySelector(".next").addEventListener("click", () => show(idx + 1));
  lb.addEventListener("click", (e) => {
    if (e.target === lb || e.target.classList.contains("lb-stage")) close();
  });
  document.addEventListener("keydown", (e) => {
    if (lb.hidden) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(idx - 1);
    if (e.key === "ArrowRight") show(idx + 1);
  });
  let tx = null;
  lb.addEventListener(
    "touchstart",
    (e) => {
      tx = e.touches[0].clientX;
    },
    { passive: true },
  );
  lb.addEventListener("touchend", (e) => {
    if (tx == null) return;
    const d = e.changedTouches[0].clientX - tx;
    if (Math.abs(d) > 50) show(idx + (d < 0 ? 1 : -1));
    tx = null;
  });

  /* ---------- poptávkové formuláře ---------- */
  const params = new URLSearchParams(location.search);
  $$("form[data-inquiry]").forEach((form) => {
    const msg = form.querySelector("[name=zprava]");
    const model = params.get("model");
    if (model && msg && !msg.value) msg.value = "Mám zájem o: " + model + "\n";
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const t = form.querySelector("[name=telefon]"),
        err = form.querySelector(".err");
      const bad = t.value.replace(/\D/g, "").length < 9;
      if (err) err.hidden = !bad;
      if (bad) {
        t.focus();
        return;
      }
      const fd = new FormData(form);
      const checked = [...form.querySelectorAll(".for-whom input:checked")]
        .map((i) => i.value)
        .join(", ");
      if (checked) fd.set("co_hleda", checked);
      fd.set(
        "_subject",
        "Poptávka z webu: " +
          (fd.get("model") || fd.get("jmeno") || "bez jména") +
          ", " +
          fd.get("telefon"),
      );
      fd.set("_template", "table");
      fd.set("_captcha", "false");
      fd.set("stranka", location.href);
      const btn = form.querySelector("button[type=submit]"),
        ok = form.querySelector(".ok-msg"),
        fail = form.querySelector(".err-msg");
      btn.disabled = true;
      btn.textContent = "Odesílám…";
      if (fail) fail.hidden = true;
      try {
        const r = await fetch(form.action.replace("formsubmit.co/", "formsubmit.co/ajax/"), {
          method: "POST",
          body: fd,
          headers: { Accept: "application/json" },
        });
        if (!r.ok) throw new Error(String(r.status));
        form.querySelectorAll("input,textarea").forEach((i) => {
          if (i.type === "checkbox") i.checked = false;
          else if (i.type !== "hidden") i.value = "";
        });
        if (ok) ok.hidden = false;
        btn.textContent = "Odesláno";
      } catch (_) {
        if (fail) fail.hidden = false;
        btn.disabled = false;
        btn.textContent = "Odeslat poptávku";
      }
    });
  });

  /* ---------- odkazy „Poptat“ s předvyplněním na stejné stránce ---------- */
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-prefill]");
    if (!a) return;
    const msg = document.querySelector("form[data-inquiry] [name=zprava]");
    if (msg && !msg.value.includes(a.dataset.prefill))
      msg.value = ("Mám zájem o: " + a.dataset.prefill + "\n" + msg.value).trim() + "\n";
  });

  /* ---------- okno s detailem (matrace apod.) ---------- */
  document.addEventListener("click", (e) => {
    const open = e.target.closest("[data-mopen]");
    if (open) {
      const dlg = document.getElementById(open.dataset.mopen);
      if (dlg && dlg.showModal) {
        dlg.showModal();
        document.body.classList.add("no-scroll");
      }
      return;
    }
    if (e.target.closest("[data-mclose]")) {
      e.target.closest("dialog").close();
      return;
    }
    if (e.target.matches("dialog.mdlg")) {
      const r = e.target.getBoundingClientRect();
      const outside =
        e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      if (outside) e.target.close();
    }
  });
  $$("dialog.mdlg").forEach((d) =>
    d.addEventListener("close", () => document.body.classList.remove("no-scroll")),
  );
})();

/* Kubiš – effects.js
 * Vlastní implementace (inspirace: 21st.dev, kód nekopírován). Čisté JS, bez závislostí.
 * Aktivace: atribut data-fx="nazev [nazev2]" na prvku. Bez JS zůstává obsah plně viditelný
 * a použitelný (stavy "skryto" jsou v CSS jen pod třídou .fx-js).
 * prefers-reduced-motion: reduce => žádné animace pohybu, obsah je hned v cílovém stavu.
 * Efekty: reveal, reveal-group, headline, fill, mark, count, parallax, lift (jen CSS),
 *   scroller, compare, zoom, thumbs, panels, accordion, quotes, header, progress.
 */
(function () {
  "use strict";
  var d = document,
    root = d.documentElement;
  if (!d.querySelector || !d.addEventListener) return;
  root.classList.add("fx-js");

  var mq = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : { matches: false };
  function RM() {
    return mq.matches;
  }

  /* ---------- pomocné funkce ---------- */
  function all(sel, ctx) {
    return [].slice.call((ctx || d).querySelectorAll(sel));
  }
  function mk(tag, cls) {
    var e = d.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }
  function num(el, attr, def) {
    var v = parseFloat(el.getAttribute(attr));
    return isNaN(v) ? def : v;
  }
  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }
  function btn(txt, label) {
    var b = mk("button", "fx-btn");
    b.type = "button";
    b.setAttribute("aria-label", label);
    b.textContent = txt;
    return b;
  }
  function each(name, fn) {
    all('[data-fx~="' + name + '"]').forEach(function (el) {
      try {
        fn(el);
      } catch (e) {
        if (window.console) console.warn("fx:" + name, e);
      }
    });
  }
  /* jednorázové sledování vstupu do viewportu; bez IntersectionObserver ihned spustí */
  function watch(el, cb, margin) {
    if (!("IntersectionObserver" in window)) {
      cb(el);
      return;
    }
    var o = new IntersectionObserver(
      function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting) {
            o.unobserve(e.target);
            cb(e.target);
          }
        });
      },
      { rootMargin: margin || "0px 0px -8% 0px", threshold: 0.01 },
    );
    o.observe(el);
  }
  /* jeden scroll/resize posluchač, volaný přes rAF */
  var ticks = [],
    queued = false;
  function onScroll() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      ticks.forEach(function (f) {
        f();
      });
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  /* rozdělení textu na slova (zachová vnořené <em>, <br> apod.) */
  function splitWords(node, cls, inner) {
    var out = [];
    (function walk(n) {
      [].slice.call(n.childNodes).forEach(function (c) {
        if (c.nodeType === 3) {
          var f = d.createDocumentFragment();
          c.nodeValue.split(/(\s+)/).forEach(function (p) {
            if (!p) return;
            if (/^\s+$/.test(p)) {
              f.appendChild(d.createTextNode(p));
              return;
            }
            var s = mk("span", cls);
            if (inner) {
              var i = mk("span");
              i.textContent = p;
              s.appendChild(i);
            } else {
              s.textContent = p;
            }
            f.appendChild(s);
            out.push(s);
          });
          n.replaceChild(f, c);
        } else if (c.nodeType === 1 && c.tagName !== "SCRIPT") {
          walk(c);
        }
      });
    })(node);
    return out;
  }

  /* ---------- 1) reveal: jemné odhalení při scrollu ---------- */
  each("reveal-group", function (g) {
    /* děti dostanou reveal se zpožděním po řadě */
    [].forEach.call(g.children, function (c, i) {
      c.setAttribute("data-fx", (c.getAttribute("data-fx") || "") + " reveal");
      c.style.setProperty("--fx-d", Math.min(i, 6) * 90 + "ms");
    });
  });
  each("reveal", function (el) {
    if (RM()) {
      el.classList.add("is-in");
      return;
    }
    watch(el, function (e) {
      e.classList.add("is-in");
    });
  });

  /* ---------- 2) headline: nadpis po slovech ---------- */
  each("headline", function (h) {
    var n = 0;
    splitWords(h, "fx-w", true).forEach(function (s) {
      s.firstChild.style.transitionDelay = Math.min(n++, 12) * 55 + "ms";
    });
    h.classList.add("fx-split");
    if (RM()) {
      h.classList.add("is-in");
      return;
    }
    watch(
      h,
      function (e) {
        e.classList.add("is-in");
      },
      "0px 0px -12% 0px",
    );
  });

  /* ---------- 3) fill: slova se při scrollu "vyplní" inkoustem ---------- */
  each("fill", function (h) {
    var ws = splitWords(h, "fx-f"),
      last = -1;
    h.classList.add("fx-fill-on");
    if (RM()) {
      ws.forEach(function (w) {
        w.classList.add("is-lit");
      });
      return;
    }
    function t() {
      var r = h.getBoundingClientRect(),
        vh = window.innerHeight;
      var p = clamp((vh * 0.9 - r.top) / (vh * 0.45 + r.height), 0, 1);
      var k = Math.round(p * ws.length);
      if (k === last) return;
      last = k;
      ws.forEach(function (w, i) {
        w.classList.toggle("is-lit", i < k);
      });
    }
    ticks.push(t);
    t();
  });

  /* ---------- 4) mark: zvýrazňovač pod klíčovým slovem ---------- */
  each("mark", function (m) {
    if (RM()) {
      m.classList.add("is-in");
      return;
    }
    watch(
      m,
      function (e) {
        e.classList.add("is-in");
      },
      "0px 0px -15% 0px",
    );
  });

  /* ---------- 5) count: počítadlo (např. "35 let") ---------- */
  each("count", function (c) {
    var raw = c.textContent.trim(),
      to = parseFloat(raw.replace(/\s/g, "").replace(",", "."));
    if (isNaN(to) || RM()) return;
    var dec = (raw.split(/[,.]/)[1] || "").length;
    var nf = new Intl.NumberFormat("cs-CZ", {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    });
    c.setAttribute("data-fx-final", raw);
    c.textContent = nf.format(0);
    watch(
      c,
      function (e) {
        var t0 = null,
          dur = 1300;
        (function step(ts) {
          if (t0 === null) t0 = ts;
          var p = clamp((ts - t0) / dur, 0, 1),
            v = to * (1 - Math.pow(1 - p, 3));
          e.textContent = p < 1 ? nf.format(v) : raw;
          if (p < 1) requestAnimationFrame(step);
        })(performance.now());
      },
      "0px 0px -10% 0px",
    );
  });

  /* ---------- 6) parallax: fotka se posouvá pomaleji než stránka ---------- */
  each("parallax", function (box) {
    var img = box.querySelector("img");
    if (!img || RM()) return;
    var amt = num(box, "data-fx-amount", 0.07); /* podíl výšky, 0.05–0.10 */
    box.classList.add("fx-parallax-on");
    img.style.transform = "scale(" + (1 + amt * 2) + ")";
    function t() {
      var r = box.getBoundingClientRect(),
        vh = window.innerHeight;
      if (r.bottom < 0 || r.top > vh) return;
      var p = clamp((r.top + r.height / 2 - vh / 2) / (vh / 2 + r.height / 2), -1, 1);
      img.style.transform =
        "translate3d(0," + (-p * amt * r.height).toFixed(1) + "px,0) scale(" + (1 + amt * 2) + ")";
    }
    ticks.push(t);
    t();
  });

  /* ---------- 7) scroller: vodorovná galerie s přetahováním ---------- */
  each("scroller", function (s) {
    s.classList.add("fx-scroller-on");
    if (!s.hasAttribute("tabindex")) s.tabIndex = 0;
    s.setAttribute("role", "region");
    if (!s.hasAttribute("aria-label"))
      s.setAttribute(
        "aria-label",
        s.getAttribute("data-fx-label") || "Galerie, posouvejte do stran",
      );
    all("img", s).forEach(function (i) {
      i.draggable = false;
    });
    var nav = mk("div", "fx-nav"),
      prev = btn("‹", "Předchozí"),
      next = btn("›", "Další");
    nav.appendChild(prev);
    nav.appendChild(next);
    s.parentNode.insertBefore(nav, s.nextSibling);
    function step(dir) {
      s.scrollBy({ left: dir * s.clientWidth * 0.85, behavior: RM() ? "auto" : "smooth" });
    }
    function upd() {
      prev.disabled = s.scrollLeft < 4;
      next.disabled = s.scrollLeft > s.scrollWidth - s.clientWidth - 4;
      nav.hidden = s.scrollWidth <= s.clientWidth + 4;
    }
    prev.addEventListener("click", function () {
      step(-1);
    });
    next.addEventListener("click", function () {
      step(1);
    });
    s.addEventListener("scroll", upd, { passive: true });
    window.addEventListener("resize", upd);
    upd();
    s.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        step(1);
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        step(-1);
      }
    });
    /* přetahování myší (dotyk má nativní swipe) */
    var down = false,
      moved = false,
      sx = 0,
      sl = 0;
    s.addEventListener("pointerdown", function (e) {
      if (e.pointerType !== "mouse" || e.button !== 0) return;
      down = true;
      moved = false;
      sx = e.clientX;
      sl = s.scrollLeft;
    });
    window.addEventListener("pointermove", function (e) {
      if (!down) return;
      var dx = e.clientX - sx;
      if (!moved && Math.abs(dx) > 5) {
        moved = true;
        s.classList.add("is-drag");
      }
      if (moved) s.scrollLeft = sl - dx;
    });
    function end() {
      if (!down) return;
      down = false;
      s.classList.remove("is-drag");
      setTimeout(function () {
        moved = false;
      }, 60);
    }
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
    s.addEventListener(
      "click",
      function (e) {
        if (moved) {
          e.preventDefault();
          e.stopPropagation();
        }
      },
      true,
    );
  });

  /* ---------- 8) compare: před / po (nativní range = klávesnice i čtečky) ---------- */
  each("compare", function (c) {
    var im = all("img", c);
    if (im.length < 2) return;
    c.classList.add("fx-compare-on");
    var r = mk("input", "fx-range");
    r.type = "range";
    r.min = 0;
    r.max = 100;
    r.step = 1;
    r.value = num(c, "data-fx-start", 50);
    r.setAttribute(
      "aria-label",
      c.getAttribute("data-fx-label") || "Porovnání dvou fotografií, posouvejte jezdec",
    );
    var line = mk("span", "fx-line"),
      knob = mk("span", "fx-knob"),
      tb = mk("span", "fx-tag fx-tag-l"),
      ta = mk("span", "fx-tag fx-tag-r");
    knob.textContent = "↔";
    line.appendChild(knob);
    tb.textContent = c.getAttribute("data-fx-before") || "Před";
    ta.textContent = c.getAttribute("data-fx-after") || "Po";
    [r, line, tb, ta].forEach(function (n) {
      c.appendChild(n);
    });
    function set() {
      c.style.setProperty("--fx-pos", r.value + "%");
      r.setAttribute("aria-valuetext", r.value + " %");
    }
    r.addEventListener("input", set);
    set();
  });

  /* ---------- 9) zoom: lupa na detail (myš = po najetí, dotyk/klávesnice = klik) ---------- */
  each("zoom", function (z) {
    var img = z.querySelector("img");
    if (!img) return;
    var k = num(z, "data-fx-zoom", 2.5),
      on = false,
      ox = 50,
      oy = 50,
      type = "mouse",
      big = z.getAttribute("data-fx-big"),
      swapped = false;
    z.classList.add("fx-zoom-on");
    z.tabIndex = 0;
    z.setAttribute("role", "button");
    z.setAttribute("aria-pressed", "false");
    if (!z.hasAttribute("aria-label")) z.setAttribute("aria-label", "Přiblížit detail dřeva");
    function apply() {
      z.classList.toggle("is-zoomed", on);
      z.setAttribute("aria-pressed", on ? "true" : "false");
      img.style.transformOrigin = ox + "% " + oy + "%";
      img.style.transform = on ? "scale(" + k + ")" : "";
      if (on && big && !swapped) {
        swapped = true;
        img.removeAttribute("srcset");
        img.src = big;
      }
    }
    function pos(e) {
      var r = z.getBoundingClientRect();
      ox = clamp(((e.clientX - r.left) / r.width) * 100, 0, 100);
      oy = clamp(((e.clientY - r.top) / r.height) * 100, 0, 100);
    }
    z.addEventListener("pointerdown", function (e) {
      type = e.pointerType;
    });
    z.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "mouse") {
        pos(e);
        on = true;
        apply();
      }
    });
    z.addEventListener("pointermove", function (e) {
      if (on) {
        pos(e);
        apply();
      }
    });
    z.addEventListener("pointerleave", function (e) {
      if (e.pointerType === "mouse") {
        on = false;
        apply();
      }
    });
    z.addEventListener("click", function (e) {
      if (type === "mouse" && e.detail !== 0) return; /* myš už zoomuje hoverem */
      on = !on;
      if (e.detail !== 0) pos(e);
      apply();
    });
    z.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        on = !on;
        ox = oy = 50;
        apply();
      } else if (on) {
        var m = { ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, -12], ArrowDown: [0, 12] }[
          e.key
        ];
        if (m) {
          e.preventDefault();
          ox = clamp(ox + m[0], 0, 100);
          oy = clamp(oy + m[1], 0, 100);
          apply();
        }
        if (e.key === "Escape") {
          on = false;
          apply();
        }
      }
    });
    z.addEventListener("blur", function () {
      if (type !== "mouse") {
        on = false;
        apply();
      }
    });
  });

  /* ---------- 10) thumbs: velká fotka + náhledy (odkazy fungují i bez JS) ---------- */
  each("thumbs", function (t) {
    var links = all(".fx-thumbs-strip a", t);
    if (!links.length) return;
    var main = t.querySelector(".fx-thumbs-main");
    if (!main) {
      main = mk("figure", "fx-thumbs-main");
      t.insertBefore(main, t.firstChild);
    }
    var img = main.querySelector("img") || main.appendChild(mk("img"));
    var cap = main.querySelector("figcaption") || main.appendChild(mk("figcaption"));
    var token = 0;
    function show(a, instant) {
      links.forEach(function (l) {
        l.removeAttribute("aria-current");
      });
      a.setAttribute("aria-current", "true");
      var th = a.querySelector("img"),
        src = a.getAttribute("href"),
        alt = th ? th.alt : "",
        my = ++token;
      function swap() {
        if (my !== token) return;
        img.src = src;
        img.alt = alt;
        cap.textContent = alt;
        img.classList.remove("is-out");
      }
      if (instant) {
        swap();
        return;
      }
      var pre = new Image();
      pre.onload = pre.onerror = function () {
        if (my !== token) return;
        if (RM()) swap();
        else {
          img.classList.add("is-out");
          setTimeout(swap, 180);
        }
      };
      pre.src = src;
    }
    t.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest(".fx-thumbs-strip a") : null;
      if (!a || links.indexOf(a) < 0) return;
      e.preventDefault();
      show(a);
    });
    t.addEventListener("keydown", function (e) {
      var i = links.indexOf(d.activeElement),
        dir = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (i < 0 || !dir) return;
      e.preventDefault();
      var n = links[(i + dir + links.length) % links.length];
      n.focus();
      show(n);
    });
    t.classList.add("fx-thumbs-on");
    show(links[0], true);
  });

  /* ---------- 11) panels: obrázkový akordeon (kategorie), hover/focus; na dotyku pod sebou ---------- */
  each("panels", function (p) {
    var ps = [].slice.call(p.children);
    function set(x) {
      ps.forEach(function (y) {
        y.classList.toggle("is-active", y === x);
      });
    }
    ps.forEach(function (x) {
      x.addEventListener("mouseenter", function () {
        set(x);
      });
      x.addEventListener("focusin", function () {
        set(x);
      });
    });
    if (ps[0]) set(ps[0]);
  });

  /* ---------- 12) accordion: plynulé rozbalení nativních <details> ---------- */
  each("accordion", function (a) {
    var ds = all("details", a),
      single = a.hasAttribute("data-fx-single");
    function run(dt, kf, done) {
      var b = dt._b;
      if (!b.animate || RM()) {
        done();
        return;
      }
      if (b._a) b._a.cancel();
      var an = (b._a = b.animate(kf, { duration: 260, easing: "ease" }));
      an.onfinish = function () {
        b._a = null;
        done();
      };
    }
    function close(dt) {
      dt.classList.add("is-closing");
      run(
        dt,
        [
          { height: dt._b.offsetHeight + "px", opacity: 1 },
          { height: "0px", opacity: 0 },
        ],
        function () {
          dt.open = false;
          dt.classList.remove("is-closing");
        },
      );
    }
    ds.forEach(function (dt) {
      var s = dt.querySelector("summary");
      if (!s) return;
      var b = mk("div", "fx-acc-body");
      while (s.nextSibling) b.appendChild(s.nextSibling);
      dt.appendChild(b);
      dt._b = b;
      s.addEventListener("click", function (e) {
        e.preventDefault();
        if (dt.open && !dt.classList.contains("is-closing")) {
          close(dt);
          return;
        }
        if (single)
          ds.forEach(function (o) {
            if (o !== dt && o.open) close(o);
          });
        dt.classList.remove("is-closing");
        dt.open = true;
        run(
          dt,
          [
            { height: "0px", opacity: 0 },
            { height: b.scrollHeight + "px", opacity: 1 },
          ],
          function () {},
        );
      });
    });
    a.classList.add("fx-acc-on");
  });

  /* ---------- 13) quotes: reference po jedné, ručně (bez autoplay) ---------- */
  each("quotes", function (q) {
    var items = [].slice.call(q.children).filter(function (c) {
      return c.tagName === "FIGURE";
    });
    if (items.length < 2) return;
    var list = mk("div", "fx-qlist");
    list.setAttribute("aria-live", "polite");
    items.forEach(function (f) {
      list.appendChild(f);
    });
    var ctrl = mk("div", "fx-qctrl"),
      prev = btn("‹", "Předchozí reference"),
      next = btn("›", "Další reference"),
      st = mk("span", "fx-qcount");
    ctrl.appendChild(prev);
    ctrl.appendChild(st);
    ctrl.appendChild(next);
    q.appendChild(list);
    q.appendChild(ctrl);
    q.classList.add("fx-quotes-on");
    var i = 0;
    function go(n) {
      i = (n + items.length) % items.length;
      items.forEach(function (f, k) {
        f.classList.toggle("is-on", k === i);
        f.setAttribute("aria-hidden", k === i ? "false" : "true");
      });
      st.textContent = i + 1 + " / " + items.length;
    }
    prev.addEventListener("click", function () {
      go(i - 1);
    });
    next.addEventListener("click", function () {
      go(i + 1);
    });
    q.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") go(i - 1);
      if (e.key === "ArrowRight") go(i + 1);
    });
    var x0 = null;
    list.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "touch") x0 = e.clientX;
    });
    list.addEventListener("pointerup", function (e) {
      if (x0 === null) return;
      var dx = e.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 50) go(i + (dx < 0 ? 1 : -1));
    });
    go(0);
  });

  /* ---------- 14) header: lepkavá hlavička (stín, volitelně schování při rolování dolů) ---------- */
  each("header", function (h) {
    var hide = h.hasAttribute("data-fx-hide"),
      last = window.pageYOffset;
    function t() {
      var y = window.pageYOffset;
      h.classList.toggle("is-stuck", y > 24);
      if (hide && !RM()) {
        var open = h.querySelector('[aria-expanded="true"]');
        if (y > last + 6 && y > 240 && !open) h.classList.add("is-hidden");
        else if (y < last - 6 || y < 240) h.classList.remove("is-hidden");
      }
      last = y;
    }
    h.addEventListener("focusin", function () {
      h.classList.remove("is-hidden");
    });
    ticks.push(t);
    t();
  });

  /* ---------- 15) progress: tenký ukazatel čtení článku ---------- */
  each("progress", function (b) {
    b.setAttribute("aria-hidden", "true");
    function t() {
      var m = root.scrollHeight - window.innerHeight;
      b.style.setProperty("--fx-p", m > 0 ? clamp(window.pageYOffset / m, 0, 1).toFixed(4) : 0);
    }
    ticks.push(t);
    t();
  });
  /* 16) lift = jen CSS (viz effects.css) */

  onScroll();
})();
