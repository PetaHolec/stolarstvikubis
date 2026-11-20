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
