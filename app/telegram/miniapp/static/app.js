(() => {
  const TOKEN_KEY = "smoxi_staff_token";
  const bootEl = document.getElementById("boot");
  const bootMsg = document.getElementById("boot-msg");
  const loginForm = document.getElementById("login-form");
  const appEl = document.getElementById("app");
  const subtitle = document.getElementById("subtitle");
  let initData = "";
  let authToken = sessionStorage.getItem(TOKEN_KEY) || "";
  let ready = false;

  function setBoot(msg, isError) {
    bootMsg.textContent = msg;
    bootMsg.className = isError ? "boot-msg err" : "boot-msg";
  }

  function showLogin(prefChatId) {
    loginForm.hidden = false;
    setBoot("Xodim sifatida kiring", false);
    if (prefChatId) {
      document.getElementById("login-chat").value = String(prefChatId);
    }
  }

  function unlockApp() {
    document.body.classList.remove("locked");
    bootEl.hidden = true;
    appEl.hidden = false;
    ready = true;
  }

  function lockApp(message) {
    ready = false;
    authToken = "";
    sessionStorage.removeItem(TOKEN_KEY);
    document.body.classList.add("locked");
    appEl.hidden = true;
    bootEl.hidden = false;
    showLogin(guessTelegramId());
    if (message) {
      const status = document.getElementById("login-status");
      status.className = "hint err";
      status.textContent = message;
    }
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
        try {
          tg.setHeaderColor("#121a27");
          tg.setBackgroundColor("#0b1220");
        } catch (_) {
          /* older clients */
        }
      } catch (_) {
        /* ignore */
      }
      if (tg.initData) return tg.initData;
    }
    return readInitDataFromHash();
  }

  function waitForInitData(timeoutMs) {
    return new Promise((resolve) => {
      const started = Date.now();
      const tick = () => {
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

  function guessTelegramId() {
    const tg = window.Telegram && window.Telegram.WebApp;
    try {
      const id = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.id;
      return id ? String(id) : "";
    } catch (_) {
      return "";
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    if (authToken) headers.Authorization = "Bearer " + authToken;
    if (initData) headers["X-Telegram-Init-Data"] = initData;
    const res = await fetch(path, Object.assign({}, options, { headers: headers }));
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    if (!res.ok) {
      const detail = (data && data.detail) || res.statusText || "Xatolik";
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail) && detail[0] && detail[0].msg
            ? String(detail[0].msg)
            : JSON.stringify(detail);
      const err = new Error(message);
      err.status = res.status;
      if (res.status === 401 && ready) {
        lockApp(message);
      }
      throw err;
    }
    return data;
  }

  function cardHtml(title, body, meta) {
    return (
      '<article class="card"><h3>' +
      escapeHtml(title) +
      "</h3><p>" +
      escapeHtml(body || "") +
      "</p>" +
      (meta ? '<div class="meta">' + escapeHtml(meta) + "</div>" : "") +
      "</article>"
    );
  }

  function activateTab(name) {
    if (!ready) return;
    document.querySelectorAll(".tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    const panel = document.getElementById("panel-" + name);
    if (panel) panel.classList.add("active");
    const fab = document.getElementById("fab-intake");
    if (fab) fab.classList.toggle("active", name === "intake");
    document.querySelectorAll(".dock-side").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    if (name === "unread") loadUnread();
    if (name === "orders") loadOrders();
    if (name === "reply") loadReplyChats();
    if (name === "ready") loadReady();
    if (name === "pickup") loadPickup();
    if (name === "stock") loadStock();
  }

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });
  document.querySelectorAll(".dock-side").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });
  document.getElementById("fab-intake").addEventListener("click", () => {
    activateTab("intake");
    const phone = document.getElementById("in-phone");
    if (phone) phone.focus();
  });
  document.getElementById("logout-btn").addEventListener("click", () => {
    lockApp("");
  });

  async function enterWithSession(token, companyName, fullName) {
    authToken = token;
    sessionStorage.setItem(TOKEN_KEY, token);
    subtitle.textContent = companyName + " · " + fullName;
    unlockApp();
    await loadUnread();
  }

  async function loadMeIntoSession() {
    const me = await api("/api/me");
    subtitle.textContent = me.company + " · " + me.user.full_name;
    unlockApp();
    await loadUnread();
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = document.getElementById("login-status");
    const btn = document.getElementById("login-submit");
    const chatId = document.getElementById("login-chat").value.trim();
    status.className = "hint";
    status.textContent = "";
    if (!chatId) {
      status.className = "hint err";
      status.textContent = "Telegram ID majburiy.";
      return;
    }
    btn.disabled = true;
    try {
      const res = await fetch("/api/auth/staff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => d.msg || d).join("; ")
              : "Kirish muvaffaqiyatsiz";
        throw new Error(msg);
      }
      await enterWithSession(data.token, data.company, data.user.full_name);
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    } finally {
      btn.disabled = false;
    }
  });

  async function loadUnread() {
    const data = await api("/api/unread");
    document.getElementById("unread-summary").textContent =
      "Xabarlar: " +
      data.unread_messages +
      " · Bildirishnomalar: " +
      data.unread_notifications;
    const list = document.getElementById("unread-list");
    if (!data.threads.length) {
      list.innerHTML = '<div class="empty">Oʻqilmagan suhbat yoʻq</div>';
      return;
    }
    list.innerHTML = data.threads
      .map((t) =>
        cardHtml(
          t.customer_name + " (" + t.unread_count + ")",
          t.last_body,
          "chat: " + t.chat_id
        )
      )
      .join("");
  }

  async function loadOrders() {
    const data = await api("/api/orders");
    const list = document.getElementById("orders-list");
    if (!data.orders.length) {
      list.innerHTML = '<div class="empty">Buyurtmalar yoʻq</div>';
      return;
    }
    list.innerHTML = data.orders
      .map((o) => cardHtml(o.number + " — " + o.status_label, o.problem))
      .join("");
  }

  async function loadReplyChats() {
    const data = await api("/api/threads");
    const select = document.getElementById("reply-chat");
    if (!data.threads.length) {
      select.innerHTML = '<option value="">Suhbat yoʻq</option>';
      return;
    }
    select.innerHTML = data.threads
      .map(
        (t) =>
          '<option value="' +
          escapeAttr(t.chat_id) +
          '">' +
          escapeHtml(t.customer_name) +
          (t.unread_count ? " (" + t.unread_count + ")" : "") +
          "</option>"
      )
      .join("");
  }

  async function loadReady() {
    const data = await api("/api/orders?ready_only=true");
    const list = document.getElementById("ready-list");
    if (!data.orders.length) {
      list.innerHTML =
        '<div class="empty">Tayyorlash mumkin boʻlgan buyurtma yoʻq</div>';
      return;
    }
    list.innerHTML = data.orders
      .map(
        (o) =>
          '<article class="card pick" data-number="' +
          escapeAttr(o.number) +
          '"><h3>' +
          escapeHtml(o.number) +
          "</h3><p>" +
          escapeHtml(o.status_label) +
          "</p></article>"
      )
      .join("");
    list.querySelectorAll(".card.pick").forEach((el) => {
      el.addEventListener("click", () => {
        document.getElementById("ready-number").value = el.dataset.number || "";
      });
    });
  }

  async function loadPickup() {
    const data = await api("/api/orders?pickup_only=true");
    const list = document.getElementById("pickup-list");
    if (!data.orders.length) {
      list.innerHTML =
        '<div class="empty">Olishga tayyor buyurtma yoʻq — avval «Tayyor» qiling</div>';
      return;
    }
    list.innerHTML = data.orders
      .map((o) => {
        const debt =
          o.unpaid_balance > 0
            ? '<p class="warn-line">Qarz: ' +
              Number(o.unpaid_balance).toLocaleString("uz-UZ") +
              " soʻm</p>"
            : "";
        return (
          '<article class="card pick" data-number="' +
          escapeAttr(o.number) +
          '"><h3>' +
          escapeHtml(o.number) +
          "</h3><p>" +
          escapeHtml(o.status_label) +
          "</p>" +
          debt +
          '<button type="button" class="btn mini primary deliver-btn">Topshirish</button></article>'
        );
      })
      .join("");
    list.querySelectorAll(".card.pick").forEach((el) => {
      const fill = () => {
        document.getElementById("pickup-number").value = el.dataset.number || "";
      };
      el.addEventListener("click", fill);
      const btn = el.querySelector(".deliver-btn");
      if (btn) {
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          fill();
          document.getElementById("pickup-send").click();
        });
      }
    });
  }

  async function loadStock() {
    const q = document.getElementById("stock-q").value.trim();
    const low = document.getElementById("stock-low").checked;
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (low) params.set("low_stock_only", "true");
    const data = await api("/api/inventory?" + params.toString());
    const list = document.getElementById("stock-list");
    if (!data.items.length) {
      list.innerHTML = '<div class="empty">Ombor boʻsh yoki topilmadi</div>';
      return;
    }
    list.innerHTML = data.items
      .map((item) => {
        const lowCls = item.low_stock ? " low" : "";
        const badgeCls = item.low_stock ? "qty-badge low" : "qty-badge";
        return (
          '<article class="card' +
          lowCls +
          '" data-id="' +
          item.id +
          '"><h3>' +
          escapeHtml(item.name) +
          "</h3><p>" +
          escapeHtml(item.sku) +
          (item.sale_price
            ? " · " + Number(item.sale_price).toLocaleString("uz-UZ") + " soʻm"
            : "") +
          '</p><span class="' +
          badgeCls +
          '">Qoldiq: ' +
          item.quantity_on_hand +
          " " +
          escapeHtml(item.unit || "dona") +
          '</span><div class="stock-actions">' +
          '<button type="button" class="btn mini" data-act="in">Kirim</button>' +
          '<button type="button" class="btn mini warn" data-act="out">Chiqim</button>' +
          '<button type="button" class="btn mini danger" data-act="set">Belgilash</button>' +
          "</div></article>"
        );
      })
      .join("");

    list.querySelectorAll(".card").forEach((card) => {
      const itemId = card.dataset.id;
      card.querySelectorAll("[data-act]").forEach((btn) => {
        btn.addEventListener("click", () => adjustStock(itemId, btn.dataset.act));
      });
    });
  }

  async function adjustStock(itemId, act) {
    const status = document.getElementById("stock-status");
    status.className = "hint";
    status.textContent = "";
    const card = document.querySelector('.card[data-id="' + itemId + '"]');
    const titleEl = card && (card.querySelector("h3") || card.querySelector(".card-title"));
    const title = (titleEl && titleEl.textContent) || ("#" + itemId);
    openAdjustSheet(itemId, act, title);
  }

  let adjustCtx = null;

  function openAdjustSheet(itemId, act, title) {
    adjustCtx = { itemId: itemId, act: act };
    const sheet = document.getElementById("adjust-sheet");
    const qtyLabel = document.getElementById("adjust-qty-label");
    const qty = document.getElementById("adjust-qty");
    const reason = document.getElementById("adjust-reason");
    const adjStatus = document.getElementById("adjust-status");
    const headings = {
      in: "Kirim",
      out: "Chiqim",
      set: "Qoldiqni belgilash",
    };
    document.getElementById("adjust-title").textContent = headings[act] || "Qoldiqni yangilash";
    document.getElementById("adjust-item").textContent = title;
    qtyLabel.textContent = act === "set" ? "Yangi qoldiq" : "Miqdor";
    qty.min = act === "set" ? "0" : "1";
    qty.value = act === "set" ? "0" : "1";
    reason.value = "";
    adjStatus.className = "hint";
    adjStatus.textContent = "";
    sheet.hidden = false;
    qty.focus();
    qty.select();
  }

  function closeAdjustSheet() {
    document.getElementById("adjust-sheet").hidden = true;
    adjustCtx = null;
  }

  async function submitAdjustSheet() {
    if (!adjustCtx) return;
    const status = document.getElementById("stock-status");
    const adjStatus = document.getElementById("adjust-status");
    const tg = window.Telegram && window.Telegram.WebApp;
    const qty = parseInt(document.getElementById("adjust-qty").value, 10);
    const reasonText = document.getElementById("adjust-reason").value.trim();
    const act = adjustCtx.act;
    let movementType = "adjust";
    let quantity = qty;
    let reason = reasonText || "Mini App";
    if (act === "in") {
      if (!quantity || quantity < 1) {
        adjStatus.className = "hint err";
        adjStatus.textContent = "Miqdor notoʻgʻri.";
        return;
      }
      movementType = "in";
      reason = reasonText || "Mini App kirim";
    } else if (act === "out") {
      if (!quantity || quantity < 1) {
        adjStatus.className = "hint err";
        adjStatus.textContent = "Miqdor notoʻgʻri.";
        return;
      }
      movementType = "out";
      reason = reasonText || "Mini App chiqim";
    } else {
      if (Number.isNaN(quantity) || quantity < 0) {
        adjStatus.className = "hint err";
        adjStatus.textContent = "Qoldiq notoʻgʻri.";
        return;
      }
      movementType = "adjust";
      reason = reasonText || "Mini App qoldiq belgilash";
    }
    adjStatus.className = "hint";
    adjStatus.textContent = "Saqlanmoqda…";
    try {
      const res = await api("/api/inventory/" + adjustCtx.itemId + "/adjust", {
        method: "POST",
        body: JSON.stringify({
          movement_type: movementType,
          quantity: quantity,
          reason: reason,
        }),
      });
      closeAdjustSheet();
      status.className = "hint ok";
      status.textContent = "Yangilandi. Qoldiq: " + res.quantity_on_hand;
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      await loadStock();
    } catch (e) {
      adjStatus.className = "hint err";
      adjStatus.textContent = e.message || "Xatolik";
      if (e.status === 401) lockApp(e.message);
    }
  }

  document.getElementById("adjust-close").addEventListener("click", closeAdjustSheet);
  document.getElementById("adjust-backdrop").addEventListener("click", closeAdjustSheet);
  document.getElementById("adjust-submit").addEventListener("click", () => {
    submitAdjustSheet().catch(() => {});
  });
  document.getElementById("adjust-qty").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      submitAdjustSheet().catch(() => {});
    }
  });

  document.getElementById("stock-refresh").addEventListener("click", () => {
    loadStock().catch((e) => {
      document.getElementById("stock-status").className = "hint err";
      document.getElementById("stock-status").textContent = e.message || "Xatolik";
    });
  });
  document.getElementById("stock-low").addEventListener("change", () => {
    if (ready) loadStock();
  });
  let stockSearchTimer = null;
  document.getElementById("stock-q").addEventListener("input", () => {
    if (!ready) return;
    clearTimeout(stockSearchTimer);
    stockSearchTimer = setTimeout(() => loadStock(), 300);
  });

  document.getElementById("stock-create").addEventListener("click", async () => {
    const status = document.getElementById("stock-create-status");
    status.className = "hint";
    status.textContent = "";
    const sku = document.getElementById("st-sku").value.trim();
    const name = document.getElementById("st-name").value.trim();
    const qty = parseInt(document.getElementById("st-qty").value, 10) || 0;
    const minQty = parseInt(document.getElementById("st-min").value, 10) || 0;
    const price = parseInt(document.getElementById("st-price").value, 10) || 0;
    if (!sku || !name) {
      status.className = "hint err";
      status.textContent = "SKU va nom majburiy.";
      return;
    }
    try {
      await api("/api/inventory", {
        method: "POST",
        body: JSON.stringify({
          sku: sku,
          name: name,
          quantity_on_hand: qty,
          min_quantity: minQty,
          sale_price: price,
        }),
      });
      status.className = "hint ok";
      status.textContent = "Tovar qoʻshildi.";
      document.getElementById("st-sku").value = "";
      document.getElementById("st-name").value = "";
      document.getElementById("st-qty").value = "0";
      document.getElementById("st-min").value = "0";
      document.getElementById("st-price").value = "0";
      await loadStock();
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    }
  });

  document.getElementById("reply-send").addEventListener("click", async () => {
    const status = document.getElementById("reply-status");
    const chatId = document.getElementById("reply-chat").value;
    const body = document.getElementById("reply-body").value.trim();
    status.className = "hint";
    status.textContent = "";
    if (!chatId || !body) {
      status.className = "hint err";
      status.textContent = "Suhbat va matn majburiy.";
      return;
    }
    try {
      await api("/api/reply", {
        method: "POST",
        body: JSON.stringify({ chat_id: chatId, body: body }),
      });
      status.className = "hint ok";
      status.textContent = "Javob yuborildi.";
      document.getElementById("reply-body").value = "";
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    }
  });

  document.getElementById("ready-send").addEventListener("click", async () => {
    const status = document.getElementById("ready-status");
    const number = document.getElementById("ready-number").value.trim();
    status.className = "hint";
    status.textContent = "";
    if (!number) {
      status.className = "hint err";
      status.textContent = "Buyurtma raqamini kiriting.";
      return;
    }
    try {
      const res = await api("/api/ready", {
        method: "POST",
        body: JSON.stringify({ number: number }),
      });
      status.className = "hint ok";
      status.textContent =
        res.number + " tayyor. Telegram: " + (res.telegram || "");
      loadReady();
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    }
  });

  document.getElementById("pickup-send").addEventListener("click", async () => {
    const status = document.getElementById("pickup-status");
    const number = document.getElementById("pickup-number").value.trim();
    const allowUnpaid = document.getElementById("pickup-allow-unpaid").checked;
    status.className = "hint";
    status.textContent = "";
    if (!number) {
      status.className = "hint err";
      status.textContent = "Buyurtma raqamini kiriting.";
      return;
    }
    try {
      const res = await api("/api/deliver", {
        method: "POST",
        body: JSON.stringify({
          number: number,
          allow_unpaid: allowUnpaid,
          note: "Mini App: mijozga topshirildi",
        }),
      });
      status.className = "hint ok";
      status.textContent =
        res.number +
        " topshirildi. Telegram: " +
        (res.telegram || "") +
        (res.unpaid_balance
          ? " · Qarz: " + Number(res.unpaid_balance).toLocaleString("uz-UZ")
          : "");
      document.getElementById("pickup-number").value = "";
      loadPickup();
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    }
  });

  document.getElementById("intake-send").addEventListener("click", async () => {
    const status = document.getElementById("intake-status");
    const btn = document.getElementById("intake-send");
    status.className = "hint";
    status.textContent = "";
    const phone = document.getElementById("in-phone").value.trim();
    const model = document.getElementById("in-model").value.trim();
    const problem = document.getElementById("in-problem").value.trim();
    if (!phone || !model || !problem) {
      status.className = "hint err";
      status.textContent = "Telefon, model va muammo majburiy.";
      return;
    }
    btn.disabled = true;
    try {
      const res = await api("/api/intake", {
        method: "POST",
        body: JSON.stringify({
          phone: phone,
          display_name: document.getElementById("in-name").value.trim() || null,
          device_brand: document.getElementById("in-brand").value.trim() || null,
          device_model: model,
          problem_description: problem,
          estimated_cost: parseInt(document.getElementById("in-cost").value, 10) || 0,
          accessories: document.getElementById("in-acc").value.trim() || null,
        }),
      });
      status.className = "hint ok";
      status.textContent =
        "Yaratildi: " +
        res.number +
        " · " +
        res.customer +
        (res.telegram_sent ? " · Telegram yuborildi" : "");
      document.getElementById("in-phone").value = "";
      document.getElementById("in-name").value = "";
      document.getElementById("in-brand").value = "";
      document.getElementById("in-model").value = "";
      document.getElementById("in-problem").value = "";
      document.getElementById("in-cost").value = "0";
      document.getElementById("in-acc").value = "";
    } catch (e) {
      status.className = "hint err";
      status.textContent = e.message || "Xatolik";
    } finally {
      btn.disabled = false;
    }
  });

  (async () => {
    setBoot("Kirish tekshirilmoqda…");
    initData = await waitForInitData(1800);

    if (authToken) {
      try {
        await loadMeIntoSession();
        return;
      } catch (_) {
        authToken = "";
        sessionStorage.removeItem(TOKEN_KEY);
      }
    }

    if (initData) {
      try {
        setBoot("Telegram orqali kirish…");
        const res = await fetch("/api/auth/telegram", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: initData }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Telegram kirish xato");
        await enterWithSession(data.token, data.company, data.user.full_name);
        return;
      } catch (e) {
        showLogin(guessTelegramId());
        const status = document.getElementById("login-status");
        status.className = "hint err";
        status.textContent = e.message || "Telegram kirish ishlamadi. ID bilan kiring.";
        return;
      }
    }

    showLogin(guessTelegramId());
  })();
})();
