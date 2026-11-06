/* SMOXI Customer Mini App */
(function () {
  const statusEl = document.getElementById("status");
  const ordersEl = document.getElementById("orders");
  const detailEl = document.getElementById("detail");
  let selectedId = null;
  let initData = "";

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function detailMessage(data, fallback) {
    const d = data && data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0] && d[0].msg) return String(d[0].msg);
    return fallback || "Xato";
  }

  function readInitDataFromHash() {
    const hash = (window.location.hash || "").replace(/^#/, "");
    if (!hash) return "";
    const params = new URLSearchParams(hash);
    const raw = params.get("tgWebAppData");
    return raw ? decodeURIComponent(raw) : "";
  }

  function resolveInitData() {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
      try {
        tg.ready();
        tg.expand();
      } catch (_) {
        /* ignore */
      }
      if (tg.initData) return tg.initData;
    }
    return readInitDataFromHash();
  }

  function waitForInitData(timeoutMs) {
    return new Promise(function (resolve) {
      const started = Date.now();
      const tick = function () {
        const value = resolveInitData();
        if (value) {
          resolve(value);
          return;
        }
        if (Date.now() - started >= timeoutMs) {
          resolve("");
          return;
        }
        window.setTimeout(tick, 100);
      };
      tick();
    });
  }

  async function api(path, options) {
    const opts = options || {};
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      opts.headers || {}
    );
    if (initData) headers["X-Telegram-Init-Data"] = initData;
    const res = await fetch("/customer" + path, Object.assign({}, opts, { headers: headers }));
    const data = await res.json().catch(function () {
      return {};
    });
    if (!res.ok) {
      throw new Error(detailMessage(data, "Xato"));
    }
    return data;
  }

  function showList() {
    detailEl.classList.add("hidden");
    ordersEl.classList.remove("hidden");
  }

  function showDetail() {
    ordersEl.classList.add("hidden");
    detailEl.classList.remove("hidden");
  }

  async function loadOrders() {
    statusEl.textContent = "Yuklanmoqda…";
    try {
      const me = await api("/api/me");
      document.getElementById("subtitle").textContent =
        me.name + " · " + (me.phone || "");
      const orders = await api("/api/orders");
      ordersEl.innerHTML = "";
      if (!orders.length) {
        statusEl.textContent = "Buyurtma topilmadi.";
        return;
      }
      statusEl.textContent = "Buyurtmalar: " + orders.length;
      orders.forEach(function (o) {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML =
          "<h3>" +
          escapeHtml(o.number) +
          "</h3><p>" +
          escapeHtml(o.status_label) +
          "</p><p>" +
          escapeHtml(o.problem || "") +
          "</p>";
        card.onclick = function () {
          openOrder(o.id);
        };
        ordersEl.appendChild(card);
      });
    } catch (err) {
      statusEl.textContent = String(err.message || err);
    }
  }

  async function openOrder(id) {
    selectedId = id;
    showDetail();
    try {
      const o = await api("/api/orders/" + id);
      document.getElementById("d-number").textContent = o.number;
      document.getElementById("d-status").textContent = o.status_label;
      document.getElementById("d-problem").textContent = o.problem || "";
      document.getElementById("d-price").textContent =
        "Smeta: " + (o.estimated_cost || 0).toLocaleString("uz-UZ") + " soʻm";
      const actions = document.getElementById("d-actions");
      if (o.can_approve) actions.classList.remove("hidden");
      else actions.classList.add("hidden");

      const tl = await api("/api/orders/" + id + "/timeline");
      const box = document.getElementById("timeline");
      box.innerHTML = "";
      tl.forEach(function (e) {
        const row = document.createElement("div");
        row.className = "tl-item";
        row.textContent =
          (e.at ? e.at.slice(0, 16).replace("T", " ") + " · " : "") + e.title;
        box.appendChild(row);
      });

      const w = await api("/api/orders/" + id + "/warranty");
      const wEl = document.getElementById("warranty");
      if (w.warranty) {
        wEl.textContent =
          w.warranty.number +
          " · " +
          w.warranty.issued_at.slice(0, 10) +
          " — " +
          w.warranty.expires_at.slice(0, 10);
      } else {
        wEl.textContent = "Kafolat hali yoʻq.";
      }
    } catch (err) {
      statusEl.textContent = String(err.message || err);
      showList();
    }
  }

  document.getElementById("btn-back").onclick = function () {
    showList();
    loadOrders();
  };

  document.getElementById("btn-approve").onclick = async function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    try {
      await api("/api/orders/" + selectedId + "/approve", {
        method: "POST",
        body: JSON.stringify({ note: "Mini App tasdiq" }),
      });
      if (tg) tg.showAlert("Tasdiqlandi");
      openOrder(selectedId);
    } catch (err) {
      if (tg) tg.showAlert(String(err.message || err));
      else statusEl.textContent = String(err.message || err);
    }
  };

  document.getElementById("btn-reject").onclick = async function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    try {
      await api("/api/orders/" + selectedId + "/reject", {
        method: "POST",
        body: JSON.stringify({ note: "Mini App rad" }),
      });
      if (tg) tg.showAlert("Rad etildi");
      openOrder(selectedId);
    } catch (err) {
      if (tg) tg.showAlert(String(err.message || err));
      else statusEl.textContent = String(err.message || err);
    }
  };

  (async function boot() {
    statusEl.textContent = "Telegram ulanishi tekshirilmoqda…";
    initData = await waitForInitData(1800);
    if (!initData) {
      statusEl.textContent =
        "Telegram Mini App orqali oching. initData topilmadi.";
      return;
    }
    await loadOrders();
  })();
})();
