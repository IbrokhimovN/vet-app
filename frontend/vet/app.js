/* Veterinar Mini App — profil, chaqiruvlar va tender. */
(function () {
  "use strict";

  const API = "/api/v1";
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  const statusEl = document.getElementById("status");
  const appEl = document.getElementById("app");

  const MONTHS = ["Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];
  const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const TYPE_ICON = { home: "🏠", online: "💬", contact: "📞" };
  function statusLabel(status) { return I18N.t("st_" + status); }
  const NEXT_ACTIONS = {
    pending: [["accept", "accept"], ["reject", "reject", "danger"]],
    accepted: [["on_way", "on_the_way"], ["complete", "finish"]],
    on_way: [["complete", "finish"]],
  };

  let token = null;
  let me = null;
  let profile = null;
  let allSpecs = [];
  let selectedSpecs = new Set();
  let currentTab = "home";
  let calls = [];
  let tender = [];
  let locationMap = null;
  let locationMarker = null;
  const TASHKENT_CENTER = [41.311, 69.240];

  function setStatus(msg) { statusEl.textContent = msg; statusEl.hidden = false; }

  let reauthPromise = null;

  async function api(path, options = {}, _retried) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    if (token) headers["Authorization"] = "Bearer " + token;
    const url = path.startsWith("http") ? path : API + path;
    const res = await fetch(url, Object.assign({}, options, { headers }));
    // Access token ~2 soatda eskiradi — buni sezmasdan yangilab, so'rovni qaytadan yuboramiz.
    if (res.status === 401 && !_retried && path.indexOf("/auth/telegram/") === -1) {
      if (!reauthPromise) reauthPromise = authenticate().finally(() => { reauthPromise = null; });
      try {
        await reauthPromise;
        return api(path, options, true);
      } catch (e) { /* pastda umumiy xato sifatida ko'tariladi */ }
    }
    if (!res.ok) throw new Error("API " + res.status + ": " + (await res.text()));
    return res.status === 204 ? null : res.json();
  }

  function popup(msg) {
    tg && tg.showPopup ? tg.showPopup({ message: msg }) : alert(msg);
  }

  // --- Qo'llab-quvvatlash: haqiqiy Telegram hisob backend .env'idan olinadi
  // (SUPPORT_TELEGRAM_USERNAME) — kodga qattiq yozilmaydi.
  let supportUsernameCache;
  async function openSupport() {
    try {
      if (supportUsernameCache === undefined) {
        const cfg = await api("/auth/config/");
        supportUsernameCache = cfg.support_telegram_username || "";
      }
      if (!supportUsernameCache) {
        popup("Qo'llab-quvvatlash hozircha ulanmagan. Birozdan so'ng qayta urinib ko'ring.");
        return;
      }
      const url = "https://t.me/" + supportUsernameCache;
      if (tg && tg.openTelegramLink) tg.openTelegramLink(url);
      else window.open(url, "_blank");
    } catch (e) {
      popup("Yordam ma'lumotini yuklab bo'lmadi. Internetni tekshiring.");
    }
  }

  // O'zbek telefon raqamini "+998901234567" formatiga keltiradi (bo'sh joy/tire
  // olib tashlanadi, "998..." yoki 9 xonali mahalliy raqamga "+998" qo'shiladi).
  function normalizePhone(raw) {
    const p = (raw || "").trim();
    if (!p) return "";
    const digits = p.replace(/[^\d+]/g, "");
    if (/^\+998\d{9}$/.test(digits)) return digits;
    if (/^998\d{9}$/.test(digits)) return "+" + digits;
    if (/^\d{9}$/.test(digits)) return "+998" + digits;
    return digits;
  }

  function friendlyError(e) {
    const msg = (e && e.message) || "";
    const m = msg.match(/^API (\d+):\s*([\s\S]*)$/);
    if (!m) {
      if (/Failed to fetch|NetworkError|Load failed/i.test(msg)) {
        return "Internet aloqasi yo'q. Ulanishni tekshirib, qaytadan urinib ko'ring.";
      }
      return "Nimadir xato ketdi. Birozdan keyin qaytadan urinib ko'ring.";
    }
    const status = Number(m[1]);
    if (status === 401) return "Sessiya tugadi. Ilovani yopib, qaytadan oching.";
    if (status === 403) return "Bu amalni bajarish uchun ruxsatingiz yo'q.";
    if (status === 404) return "Topilmadi — balki allaqachon o'chirilgan yoki o'zgargan.";
    if (status === 400 || status === 422) {
      try {
        const data = JSON.parse(m[2]);
        const first = Array.isArray(data) ? data[0] : Object.values(data)[0];
        const text = Array.isArray(first) ? first[0] : first;
        if (typeof text === "string") return text;
      } catch (e2) { /* jim */ }
      return "Ma'lumotlarni tekshirib, qaytadan urinib ko'ring.";
    }
    if (status >= 500) return "Serverda vaqtinchalik nosozlik. Birozdan keyin qaytadan urinib ko'ring.";
    return "Nimadir xato ketdi. Birozdan keyin qaytadan urinib ko'ring.";
  }

  // Tugmani so'rov davomida o'chirib turadi — ikki marta bosib, takroriy
  // so'rov yuborilib ketmasligi uchun.
  async function withBusy(btn, fn) {
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    try {
      await fn();
    } finally {
      btn.disabled = false;
    }
  }

  function confirmAction(message, onConfirm) {
    if (tg && tg.showConfirm) {
      tg.showConfirm(message, (ok) => { if (ok) onConfirm(); });
    } else if (window.confirm(message)) {
      onConfirm();
    }
  }

  // --- Auth ---
  async function authenticate() {
    if (!tg || !tg.initData) {
      setStatus("⚠️ Bu sahifa Telegram ichida ochilishi kerak.");
      throw new Error("no-telegram");
    }
    const data = await api("/auth/telegram/", {
      method: "POST",
      body: JSON.stringify({ init_data: tg.initData, app: "vet" }),
    });
    token = data.access;
    me = data.user;
    I18N.setLang(me.language);
    I18N.applyStatic();
  }

  async function loadProfileData() {
    allSpecs = await api("/specializations/");
    profile = await api("/vets/me/");
  }

  // --- Home ---
  function setGreeting() {
    const now = new Date();
    document.getElementById("home-date").textContent =
      WEEKDAYS[now.getDay()] + ", " + now.getDate() + " " + MONTHS[now.getMonth()].toLowerCase();
    const hour = now.getHours();
    const part = hour < 12 ? I18N.t("greet_morning") : hour < 18 ? I18N.t("greet_day") : I18N.t("greet_evening");
    document.getElementById("home-greeting").textContent = `${part}, Dr. ${me.first_name || ""} 👋`;
  }

  function renderAvailability() {
    document.getElementById("home-available").checked = !!profile.is_available;
    document.getElementById("is_available").checked = !!profile.is_available;
    document.getElementById("avail-sub").textContent = profile.is_available
      ? "Mijozlarga ko'rinasiz" : "Yashirin — chaqiruv kelmaydi";
  }

  async function setAvailability(value) {
    profile = await api("/vets/me/availability/", { method: "PUT", body: JSON.stringify({ is_available: value }) })
      .then((r) => Object.assign(profile, r));
    renderAvailability();
  }

  function renderHomeStats() {
    const pending = calls.filter((c) => c.status === "pending").length;
    document.getElementById("stat-pending").textContent = pending;
    document.getElementById("stat-tender").textContent = tender.length;
    document.getElementById("stat-rating").textContent = profile.rating_count > 0 ? Number(profile.rating_avg).toFixed(1) : "—";

    const callsDot = document.getElementById("calls-dot");
    callsDot.textContent = pending;
    callsDot.hidden = pending === 0;
    const tenderDot = document.getElementById("tender-dot");
    tenderDot.textContent = tender.length;
    tenderDot.hidden = tender.length === 0;
  }

  function renderHomeCalls() {
    const ul = document.getElementById("home-calls");
    const preview = calls.slice(0, 3);
    ul.innerHTML = "";
    document.getElementById("home-calls-empty").hidden = preview.length > 0;
    preview.forEach((r) => ul.appendChild(callCardEl(r, false)));
  }

  function fmtScheduled(iso) {
    const d = new Date(iso);
    return d.getDate() + " " + MONTHS[d.getMonth()] + ", " + d.getHours().toString().padStart(2, "0") + ":" + d.getMinutes().toString().padStart(2, "0");
  }

  // --- Call card (used on Home preview + Calls tab) ---
  function callCardEl(r, withActions) {
    const li = document.createElement("li");
    li.className = "req-card";
    const typeLabel = { home: "🏠 Uyga", online: "💬 Online", contact: "📞 Kontakt" }[r.type] || r.type;
    const acts = withActions
      ? (NEXT_ACTIONS[r.status] || [])
          .map((a) => `<button data-act="${a[0]}" class="${a[2] || ""}">${I18N.t(a[1])}</button>`)
          .join("")
      : "";
    li.innerHTML = `
      <div class="req-top">
        <div class="req-icon">${TYPE_ICON[r.type] || "📋"}</div>
        <div class="req-info">
          <div class="t">${typeLabel} · ${r.pet_info?.name || "Hayvon"}</div>
          <div class="s">${r.note || "Izohsiz"}</div>
          ${r.address ? `<div class="addr">📍 ${r.address}</div>` : ""}
          ${r.scheduled_at ? `<div class="addr">🕒 ${fmtScheduled(r.scheduled_at)}</div>` : ""}
          ${r.client_info?.phone ? `<div class="addr"><a class="tel-link" href="tel:${r.client_info.phone}">📞 ${r.client_info.phone}</a></div>` : ""}
        </div>
        <span class="st st-${r.status}">${statusLabel(r.status)}</span>
      </div>
      ${acts ? `<div class="req-actions">${acts}</div>` : ""}
      ${withActions && ["accepted", "on_way", "completed"].includes(r.status) ? `
      <div class="price-row" style="margin-top:8px;display:flex;gap:8px;align-items:center">
        <input type="number" min="0" class="price-input" placeholder="${I18N.t("price_agreed_ph")}" value="${r.price_agreed || ""}" style="flex:1;padding:8px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:13px" />
        <button class="btn-secondary price-save-btn" style="width:auto;flex:0 0 auto;margin-top:0;padding:8px 14px">${I18N.t("save")}</button>
      </div>` : ""}
      ${withActions && ["completed", "rejected", "cancelled"].includes(r.status) ? `<button class="btn-secondary report-btn" style="margin-top:8px;width:100%;color:var(--red)">${I18N.t("report")}</button>` : ""}`;
    if (withActions) {
      const priceBtn = li.querySelector(".price-save-btn");
      if (priceBtn) priceBtn.onclick = () => withBusy(priceBtn, async () => {
        const val = li.querySelector(".price-input").value;
        if (!val) return popup(I18N.t("price_enter_first"));
        try {
          await api("/requests/" + r.id + "/price/", { method: "POST", body: JSON.stringify({ price_agreed: val }) });
          popup(I18N.t("price_saved"));
          await loadCalls();
        } catch (e) { popup(friendlyError(e)); }
      });
      li.querySelectorAll(".req-actions button").forEach((btn) => {
        const run = () => withBusy(btn, async () => {
          try {
            await api("/requests/" + r.id + "/" + btn.dataset.act + "/", { method: "POST" });
            await loadCalls();
            renderHomeStats();
          } catch (e) { popup(friendlyError(e)); }
        });
        btn.onclick = btn.dataset.act === "reject"
          ? () => confirmAction("Bu chaqiruvni rad etasizmi?", run)
          : run;
      });
      const reportBtn = li.querySelector(".report-btn");
      if (reportBtn) reportBtn.onclick = () => openReportForm(r.client_info?.id, { call_request: r.id }, li);
    }
    return li;
  }

  const REPORT_REASONS = ["no_show", "rude", "fraud", "quality", "other"];

  function openReportForm(reportedUserId, source, li) {
    if (li.querySelector(".report-form")) return;
    const form = document.createElement("div");
    form.className = "report-form";
    form.style.cssText = "margin-top:10px;padding-top:10px;border-top:1px solid var(--border)";
    form.innerHTML = `
      <p class="muted" style="margin:0 0 6px;font-size:12px">${I18N.t("report_reason_title")}</p>
      <select class="report-reason" style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:13px">
        ${REPORT_REASONS.map((r) => `<option value="${r}">${I18N.t("report_reason_" + r)}</option>`).join("")}
      </select>
      <textarea class="report-text" rows="2" placeholder="${I18N.t("report_comment_ph")}" style="margin-top:8px;width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:13px"></textarea>
      <button class="btn-secondary report-send" style="width:100%;margin-top:8px;color:var(--red)">${I18N.t("report_send")}</button>`;
    const sendBtn = form.querySelector(".report-send");
    sendBtn.onclick = () => confirmAction(I18N.t("report_confirm"), () => withBusy(sendBtn, async () => {
      try {
        await api("/reports/", {
          method: "POST",
          body: JSON.stringify(Object.assign({
            reported_user: reportedUserId,
            reason: form.querySelector(".report-reason").value,
            comment: form.querySelector(".report-text").value,
          }, source)),
        });
        popup(I18N.t("report_sent"));
        form.remove();
      } catch (e) { popup(friendlyError(e)); }
    }));
    li.appendChild(form);
  }

  let callsStatusFilter = "all";

  async function loadCalls() {
    // Barcha sahifalarni yig'ib olamiz — aks holda eski chaqiruvlar
    // qidiruv/filtrga kirmay qoladi (faqat 1-sahifa ko'rinardi).
    let items = [];
    let url = "/requests/?role=vet";
    while (url) {
      const data = await api(url);
      items = items.concat(data.results || data);
      url = data.next || null;
    }
    calls = items;
    renderCallsList();
    renderHomeCalls();
    renderHomeStats();
  }

  function renderCallsList() {
    const q = (document.getElementById("calls-search").value || "").toLowerCase().trim();
    const filtered = calls.filter((r) => {
      if (callsStatusFilter !== "all" && r.status !== callsStatusFilter) return false;
      if (!q) return true;
      const hay = [r.pet_info?.name, r.note, r.address].filter(Boolean).join(" ").toLowerCase();
      return hay.includes(q);
    });
    const ul = document.getElementById("calls-list");
    ul.innerHTML = "";
    document.getElementById("calls-empty").hidden = filtered.length > 0;
    filtered.forEach((r) => ul.appendChild(callCardEl(r, true)));
  }

  // --- Tender ---
  async function loadWonTenders() {
    const won = await api("/service-requests/won/");
    const section = document.getElementById("won-section");
    const ul = document.getElementById("won-list");
    ul.innerHTML = "";
    section.hidden = won.length === 0;
    won.forEach((sr) => {
      const li = document.createElement("li");
      li.className = "req-card";
      const price = sr.assigned_offer_info ? Number(sr.assigned_offer_info.price).toLocaleString() + " so'm" : "";
      const canComplete = sr.status === "assigned";
      const canReport = ["completed", "cancelled"].includes(sr.status);
      li.innerHTML = `
        <div class="req-top">
          <div class="req-icon">${sr.specialization_info?.icon || "🐾"}</div>
          <div class="req-info">
            <div class="t">${sr.specialization_info?.name || ""} · ${sr.city || ""}</div>
            <div class="s">${sr.note || "Izohsiz"}</div>
            <div class="addr">💰 ${price}</div>
            ${sr.client_info?.phone ? `<div class="addr"><a class="tel-link" href="tel:${sr.client_info.phone}">📞 ${sr.client_info.phone}</a></div>` : ""}
          </div>
          <span class="st st-${sr.status === "completed" ? "completed" : "accepted"}">${sr.status === "completed" ? I18N.t("st_completed") : I18N.t("working")}</span>
        </div>
        ${canComplete ? `<button class="btn-secondary complete-btn" style="margin-top:10px;width:100%">${I18N.t("complete")}</button>` : ""}
        ${canReport ? `<button class="btn-secondary report-btn" style="margin-top:8px;width:100%;color:var(--red)">${I18N.t("report")}</button>` : ""}`;
      const completeBtn = li.querySelector(".complete-btn");
      if (completeBtn) completeBtn.onclick = () => confirmAction("Bu ishni yakunlaysizmi?", () => withBusy(completeBtn, async () => {
        try {
          await api("/service-requests/" + sr.id + "/complete/", { method: "POST" });
          popup("Yakunlandi ✅");
          await loadWonTenders();
        } catch (e) { popup(friendlyError(e)); }
      }));
      const reportBtn = li.querySelector(".report-btn");
      if (reportBtn) reportBtn.onclick = () => openReportForm(sr.client_info?.id, { service_request: sr.id }, li);
      ul.appendChild(li);
    });
  }

  async function loadTender() {
    await loadWonTenders();
    const data = await api("/service-requests/feed/");
    tender = data.results || data;
    const ul = document.getElementById("tender-list");
    ul.innerHTML = "";
    document.getElementById("tender-empty").hidden = tender.length > 0;
    tender.forEach((r) => {
      const li = document.createElement("li");
      li.className = "req-card";
      const typeLabel = { home: "🏠", online: "💬", contact: "📞" }[r.type] || "";
      const alreadySent = r.my_offer && r.my_offer.status === "sent";
      li.innerHTML = `
        <div class="req-top">
          <div class="req-icon">${r.specialization_info?.icon || "🐾"}</div>
          <div class="req-info">
            <div class="t">${typeLabel} ${r.specialization_info?.name || ""} · ${r.city || ""}</div>
            <div class="s">${r.note || "Izohsiz"}</div>
            ${r.budget_hint ? `<div class="addr">💰 ~${Number(r.budget_hint).toLocaleString()} so'm</div>` : ""}
          </div>
        </div>
        ${alreadySent
          ? `<div class="offer-form"><span class="muted" style="flex:1">✅ Taklif yuborildi: ${Number(r.my_offer.price).toLocaleString()} so'm</span><button class="o-withdraw" style="background:none;border:1px solid var(--red);color:var(--red)">Qaytarib olish</button></div>`
          : `<div class="offer-form"><input type="number" placeholder="Narxingiz (so'm)" class="o-price" /><button class="o-send">Taklif</button></div>`}`;
      if (alreadySent) {
        const withdrawBtn = li.querySelector(".o-withdraw");
        withdrawBtn.onclick = () => confirmAction("Taklifni qaytarib olasizmi?", () => withBusy(withdrawBtn, async () => {
          try {
            await api("/offers/" + r.my_offer.id + "/withdraw/", { method: "POST" });
            popup("Taklif qaytarib olindi");
            await loadTender();
          } catch (e) { popup(friendlyError(e)); }
        }));
      } else {
        const price = li.querySelector(".o-price");
        const sendBtn = li.querySelector(".o-send");
        sendBtn.onclick = () => withBusy(sendBtn, async () => {
          if (!price.value) return popup("Narxni kiriting");
          try {
            await api("/service-requests/" + r.id + "/offer/", { method: "POST", body: JSON.stringify({ price: price.value }) });
            popup("Taklif yuborildi ✅");
            await loadTender();
          } catch (e) { popup(friendlyError(e)); }
        });
      }
      ul.appendChild(li);
    });
    renderHomeStats();
  }

  // --- Profil formasi ---
  function renderSpecs() {
    const box = document.getElementById("specializations");
    box.innerHTML = "";
    allSpecs.forEach((s) => {
      const el = document.createElement("div");
      el.className = "chip" + (selectedSpecs.has(s.id) ? " active" : "");
      el.textContent = (s.icon ? s.icon + " " : "") + s.name;
      el.onclick = () => {
        if (selectedSpecs.has(s.id)) selectedSpecs.delete(s.id);
        else selectedSpecs.add(s.id);
        el.classList.toggle("active");
      };
      box.appendChild(el);
    });
  }

  function renderServices(services) {
    const box = document.getElementById("services");
    box.innerHTML = "";
    (services || []).forEach((svc) => {
      const row = document.createElement("div");
      row.className = "svc-row";
      row.innerHTML = `<span>${svc.title} — ${Number(svc.price).toLocaleString()} so'm</span><button class="del">🗑</button>`;
      const delBtn = row.querySelector(".del");
      delBtn.onclick = () => confirmAction(`"${svc.title}" xizmatini o'chirasizmi?`, () => withBusy(delBtn, async () => {
        try {
          await api("/vets/me/services/" + svc.id + "/", { method: "DELETE" });
          row.remove();
        } catch (e) { popup(friendlyError(e)); }
      }));
      box.appendChild(row);
    });
  }

  async function addService() {
    const titleEl = document.getElementById("svc-title");
    const priceEl = document.getElementById("svc-price");
    const title = titleEl.value.trim();
    const price = priceEl.value;
    if (!title || !price) return popup("Nomi va narxini kiriting");
    try {
      await api("/vets/me/services/", { method: "POST", body: JSON.stringify({ title, price, duration_min: 30 }) });
      titleEl.value = "";
      priceEl.value = "";
      renderServices(await api("/vets/me/services/"));
    } catch (e) { popup(friendlyError(e)); }
  }

  // --- Shaxsiy ma'lumotlar (ism, telefon, rasm) ---
  function renderIdentity() {
    const name = [me.first_name, me.last_name].filter(Boolean).join(" ") || me.username || "Veterinar";
    const avatarEl = document.getElementById("profile-avatar");
    if (me.photo) {
      avatarEl.innerHTML = `<img src="${me.photo}" alt="" />`;
    } else {
      avatarEl.textContent = name.charAt(0).toUpperCase();
    }
    document.getElementById("profile-name").textContent = name;
    document.getElementById("profile-sub").textContent = me.phone || (me.username ? "@" + me.username : "Telefon kiritilmagan");
    document.getElementById("edit-first").value = me.first_name || "";
    document.getElementById("edit-last").value = me.last_name || "";
    document.getElementById("edit-phone").value = me.phone || "";
    document.getElementById("lang-current").textContent = me.language === "ru" ? "Русский" : "O'zbekcha";
  }

  // Ism/familiya/telefonni saqlaydi — profil tahrir formasi va birinchi kirishdagi
  // "tanishaylik" oynasi ikkalasi ham shuni chaqiradi.
  async function saveNamePhone(firstName, lastName, phoneRaw, { requirePhone } = {}) {
    const phone = normalizePhone(phoneRaw);
    const first = firstName.trim();
    if (requirePhone && !first) {
      popup(I18N.t("identity_first_required"));
      return false;
    }
    if (phone && !/^\+998\d{9}$/.test(phone)) {
      popup("Telefon raqami noto'g'ri. Namuna: +998901234567");
      return false;
    }
    if (requirePhone && !phone) {
      popup("Telefon raqami noto'g'ri. Namuna: +998901234567");
      return false;
    }
    try {
      me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ first_name: first, last_name: lastName.trim(), phone }) });
      renderIdentity();
      setGreeting();
      popup("Saqlandi ✅");
      return true;
    } catch (e) {
      popup(friendlyError(e));
      return false;
    }
  }

  async function saveIdentity() {
    const ok = await saveNamePhone(
      document.getElementById("edit-first").value,
      document.getElementById("edit-last").value,
      document.getElementById("edit-phone").value,
    );
    if (ok) document.getElementById("profile-edit-wrap").hidden = true;
  }

  // --- Birinchi kirishda ism/telefon so'rash ---
  // Telegram profilida ism odatda bor, lekin telefon hech qachon berilmaydi —
  // shuning uchun aynan telefon yo'qligiga qarab so'raymiz.
  // Viloyat ham shart: mijozlar va ochiq so'rovlar viloyat bo'yicha filtrlanadi,
  // viloyati yo'q vet hech kimga ko'rinmaydi — shuning uchun uni o'tkazib yuborib bo'lmaydi.
  function maybeShowIdentityOnboarding() {
    const needsRegion = !profile || !profile.city;
    if (me.phone && !needsRegion) return;
    const modal = document.getElementById("identity-modal");
    document.getElementById("onb-first").value = me.first_name || "";
    document.getElementById("onb-last").value = me.last_name || "";
    document.getElementById("onb-phone").value = me.phone || "";
    fillOnbRegionOptions();
    document.getElementById("onb-skip").hidden = needsRegion;
    modal.hidden = false;
  }

  function fillOnbRegionOptions() {
    const sel = document.getElementById("onb-city");
    const placeholder = sel.firstElementChild;
    sel.innerHTML = "";
    sel.appendChild(placeholder);
    (window.UZ_REGIONS || []).forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.name;
      opt.textContent = r.name;
      sel.appendChild(opt);
    });
    fillOnbDistrictOptions("");
  }

  function fillOnbDistrictOptions(regionName) {
    const sel = document.getElementById("onb-district");
    const placeholder = sel.firstElementChild;
    sel.innerHTML = "";
    sel.appendChild(placeholder);
    sel.disabled = !regionName;
    const region = (window.UZ_REGIONS || []).find((r) => r.name === regionName);
    (region ? region.districts : []).forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    });
  }

  async function saveOnboarding() {
    const needsRegion = !profile || !profile.city;
    const city = document.getElementById("onb-city").value;
    const district = document.getElementById("onb-district").value;
    if (needsRegion && (!city || !district)) {
      popup(I18N.t("identity_region_required"));
      return false;
    }
    const ok = await saveNamePhone(
      document.getElementById("onb-first").value,
      document.getElementById("onb-last").value,
      document.getElementById("onb-phone").value,
      { requirePhone: true },
    );
    if (!ok) return false;
    if (needsRegion) {
      const payload = { city, district };
      // Aniq joy hali belgilanmagan bo'lsa viloyat markazini qo'yamiz — vet xaritada darhol ko'rinadi.
      const region = (window.UZ_REGIONS || []).find((r) => r.name === city);
      if (profile.lat == null && region && region.center) {
        payload.lat = region.center[0];
        payload.lng = region.center[1];
      }
      try {
        profile = await api("/vets/me/", { method: "PATCH", body: JSON.stringify(payload) });
        fillForm(profile);
        if (profile.lat != null) setLocation(profile.lat, profile.lng, { persist: false });
      } catch (e) {
        popup(friendlyError(e));
        return false;
      }
    }
    return true;
  }

  async function uploadLicense(file) {
    if (file.size > 10 * 1024 * 1024) return popup("Fayl hajmi 10MB dan oshmasligi kerak.");
    const formData = new FormData();
    formData.append("license_document", file);
    const headers = {};
    if (token) headers["Authorization"] = "Bearer " + token;
    try {
      const res = await fetch(API + "/vets/me/", { method: "PATCH", body: formData, headers });
      if (!res.ok) throw new Error("API " + res.status + ": " + (await res.text()));
      profile = await res.json();
      fillForm(profile);
      popup("Fayl yuklandi ✅. Admin tekshiruvidan so'ng tasdiqlanadi.");
    } catch (e) { popup(friendlyError(e)); }
  }

  async function uploadPhoto(file) {
    if (file.size > 5 * 1024 * 1024) return popup("Rasm hajmi 5MB dan oshmasligi kerak.");
    // Server javobini kutmasdan tanlangan rasmni darhol ko'rsatamiz — foydalanuvchi
    // noto'g'ri fayl tanlaganini yuklanishni kutmasdan ko'radi.
    const previewUrl = URL.createObjectURL(file);
    const avatarEl = document.getElementById("profile-avatar");
    avatarEl.innerHTML = `<img src="${previewUrl}" alt="" />`;
    const formData = new FormData();
    formData.append("photo", file);
    const headers = {};
    if (token) headers["Authorization"] = "Bearer " + token;
    try {
      const res = await fetch(API + "/auth/me/", { method: "PATCH", body: formData, headers });
      if (!res.ok) throw new Error("API " + res.status + ": " + (await res.text()));
      me = await res.json();
      renderIdentity();
      popup("Rasm yangilandi ✅");
    } catch (e) {
      renderIdentity();
      popup(friendlyError(e));
    } finally {
      URL.revokeObjectURL(previewUrl);
    }
  }

  // --- Viloyat -> tuman select'lari (erkin matn o'rniga ro'yxatdan tanlash) ---
  // `currentCity` — profilda eski (erkin matn davridan qolgan) qiymat bo'lsa,
  // ro'yxatda topilmasa ham yo'qolib qolmasligi uchun alohida variant qo'shiladi.
  function fillRegionOptions(currentCity) {
    const sel = document.getElementById("city");
    const placeholder = sel.firstElementChild;
    sel.innerHTML = "";
    sel.appendChild(placeholder);
    const regions = window.UZ_REGIONS || [];
    regions.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.name;
      opt.textContent = r.name;
      sel.appendChild(opt);
    });
    if (currentCity && !regions.some((r) => r.name === currentCity)) {
      const opt = document.createElement("option");
      opt.value = currentCity;
      opt.textContent = currentCity + " (eski qiymat)";
      sel.appendChild(opt);
    }
  }

  function fillDistrictOptions(regionName, selectedDistrict) {
    const districtSel = document.getElementById("district");
    const placeholder = districtSel.firstElementChild;
    districtSel.innerHTML = "";
    districtSel.appendChild(placeholder);
    const region = (window.UZ_REGIONS || []).find((r) => r.name === regionName);
    districtSel.disabled = !regionName;
    const districts = region ? region.districts : [];
    districts.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      districtSel.appendChild(opt);
    });
    if (selectedDistrict && !districts.includes(selectedDistrict)) {
      const opt = document.createElement("option");
      opt.value = selectedDistrict;
      opt.textContent = selectedDistrict + " (eski qiymat)";
      districtSel.appendChild(opt);
    }
    if (selectedDistrict) districtSel.value = selectedDistrict;
  }

  function fillForm(p) {
    document.getElementById("bio").value = p.bio || "";
    document.getElementById("clinic_name").value = p.clinic_name || "";
    document.getElementById("experience_years").value = p.experience_years || 0;
    fillRegionOptions(p.city);
    document.getElementById("city").value = p.city || "";
    fillDistrictOptions(p.city, p.district);
    document.getElementById("address").value = p.address || "";
    document.getElementById("accepts_home_visit").checked = !!p.accepts_home_visit;
    document.getElementById("accepts_online").checked = !!p.accepts_online;
    selectedSpecs = new Set((p.specializations || []).map((s) => s.id));
    document.getElementById("verified-badge").innerHTML = p.is_verified
      ? `<span class="badge-verified">${I18N.t("verified")}</span>`
      : `<span class="badge-unverified">${I18N.t("unverified")}</span>`;
    document.getElementById("license-status").textContent = p.license_document
      ? I18N.t("license_uploaded")
      : I18N.t("license_not_uploaded");
    document.getElementById("license-upload-btn").textContent = p.license_document
      ? I18N.t("license_change_btn")
      : I18N.t("license_upload_btn");
    renderAvailability();
    renderSpecs();
    renderServices(p.services || []);
    renderOnboarding(p);
  }

  // Yangi vet uchun: mijozlar uni topishi uchun to'ldirishi kerak bo'lgan
  // asosiy maydonlar ro'yxati. Hammasi bajarilsa, karta o'zi yashiriladi.
  function renderOnboarding(p) {
    const checklist = [
      { done: !!(p.specializations && p.specializations.length), label: I18N.t("onboard_spec") },
      { done: p.lat != null && p.lng != null, label: I18N.t("onboard_location") },
      { done: !!(p.services && p.services.length), label: I18N.t("onboard_service") },
      { done: !!p.bio, label: I18N.t("onboard_bio") },
    ];
    const card = document.getElementById("onboard-card");
    const remaining = checklist.filter((c) => !c.done);
    card.hidden = remaining.length === 0;
    if (remaining.length === 0) return;
    document.getElementById("onboard-list").innerHTML = checklist
      .map((c) => `<li class="${c.done ? "done" : ""}">${c.done ? "✅" : "⬜️"} ${c.label}</li>`)
      .join("");
  }

  async function save() {
    const payload = {
      bio: document.getElementById("bio").value,
      clinic_name: document.getElementById("clinic_name").value,
      experience_years: Number(document.getElementById("experience_years").value) || 0,
      city: document.getElementById("city").value,
      district: document.getElementById("district").value,
      address: document.getElementById("address").value,
      accepts_home_visit: document.getElementById("accepts_home_visit").checked,
      accepts_online: document.getElementById("accepts_online").checked,
      specialization_ids: Array.from(selectedSpecs),
    };
    if (window._lat != null && window._lng != null) {
      payload.lat = window._lat;
      payload.lng = window._lng;
    }
    try {
      profile = await api("/vets/me/", { method: "PATCH", body: JSON.stringify(payload) });
      renderAvailability();
      popup("Saqlandi ✅");
    } catch (e) { popup(friendlyError(e)); }
  }

  function captureLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      setLocation(pos.coords.latitude, pos.coords.longitude);
      if (locationMap) locationMap.setCenter([window._lat, window._lng], 15);
    });
  }

  // "Manzil" maydonidagi matnni xaritadagi nuqtaga aylantiradi (bepul OSM
  // qidiruvi — foydalanuvchi aniq bosganda, avtomatik/ommaviy emas).
  async function geocodeAddress() {
    const query = [
      document.getElementById("city").value,
      document.getElementById("district").value,
      document.getElementById("address").value,
    ].filter(Boolean).join(", ");
    if (!query) return popup("Avval shahar yoki manzilni kiriting");
    try {
      const res = await fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(query));
      const results = await res.json();
      if (!results.length) return popup("Manzil topilmadi. Xaritadan qo'lda belgilang.");
      const lat = Number(results[0].lat);
      const lng = Number(results[0].lon);
      setLocation(lat, lng);
      if (locationMap) locationMap.setCenter([lat, lng], 15);
    } catch (e) {
      popup("Qidirishda xatolik. Xaritadan qo'lda belgilang.");
    }
  }

  // --- Joylashuv xaritasi (Yandex Maps — bosib/tortib qo'lda belgilash) ---
  // Muhim: joylashuvni GPS/xarita/viloyat orqali belgilash avval faqat mahalliy
  // holatni (window._lat) o'zgartirar edi — pastdagi katta "Saqlash" tugmasi
  // bosilmaguncha backendga yozilmasdi. Shu sabab vet joylashuvni "belgilagan"
  // deb o'ylab, aslida saqlanmagani uchun mijoz xaritasida ko'rinmasdi
  // (10-bo'lim: pilotda aniqlangan kamchilik). Endi koordinata o'zgarishi
  // darhol (debounce bilan) backendga ham yoziladi.
  let locationSaveTimer = null;
  function saveLocationDebounced(lat, lng) {
    clearTimeout(locationSaveTimer);
    locationSaveTimer = setTimeout(async () => {
      try {
        profile = await api("/vets/me/", { method: "PATCH", body: JSON.stringify({ lat, lng }) });
      } catch (e) { /* jim — asosiy formani to'ldirishga xalaqit bermasin */ }
    }, 600);
  }

  // Viloyat/tuman matnini ham (koordinatadan mustaqil ravishda) darhol saqlaydi.
  async function saveCityDistrict() {
    try {
      profile = await api("/vets/me/", {
        method: "PATCH",
        body: JSON.stringify({
          city: document.getElementById("city").value,
          district: document.getElementById("district").value,
        }),
      });
    } catch (e) { /* jim */ }
  }

  function setLocation(lat, lng, opts) {
    window._lat = lat;
    window._lng = lng;
    document.getElementById("geo-info").textContent = "📍 " + lat.toFixed(5) + ", " + lng.toFixed(5);
    if (!opts || opts.persist !== false) saveLocationDebounced(lat, lng);
    if (!locationMap) return;
    if (locationMarker) {
      locationMarker.geometry.setCoordinates([lat, lng]);
    } else {
      locationMarker = new ymaps.Placemark([lat, lng], {}, { draggable: true, preset: "islands#blueDotIcon" });
      locationMarker.events.add("dragend", () => {
        const p = locationMarker.geometry.getCoordinates();
        setLocation(p[0], p[1]);
      });
      locationMap.geoObjects.add(locationMarker);
    }
  }

  function initLocationMap(lat, lng) {
    if (locationMap) return;
    const mapEl = document.getElementById("location-map");
    mapEl.textContent = "Xarita yuklanmoqda...";
    waitForYmaps(() => {
      if (locationMap) return;
      mapEl.textContent = "";
      const center = lat != null && lng != null ? [lat, lng] : TASHKENT_CENTER;
      locationMap = new ymaps.Map("location-map", { center, zoom: lat != null ? 15 : 11, controls: ["zoomControl"] });
      // Bu — mavjud (allaqachon saqlangan) qiymatni ko'rsatish, shuning uchun
      // qayta saqlash shart emas (persist: false).
      if (lat != null && lng != null) setLocation(lat, lng, { persist: false });
      locationMap.events.add("click", (e) => {
        const c = e.get("coords");
        setLocation(c[0], c[1]);
      });
      setTimeout(() => locationMap.container.fitToViewport(), 100);
    });
  }

  // Ba'zi WebView'larda (mas. Telegram iOS) Yandex skripti sekin yuklanadi —
  // shu sabab darhol berilib ketish o'rniga bir necha marta qayta tekshiramiz.
  function waitForYmaps(cb, attempt) {
    attempt = attempt || 0;
    if (typeof ymaps !== "undefined") { ymaps.ready(cb); return; }
    if (attempt >= 20) {
      document.getElementById("location-map").textContent = "Xarita yuklanmadi. Internetni tekshirib, qaytadan urinib ko'ring.";
      return;
    }
    setTimeout(() => waitForYmaps(cb, attempt + 1), 300);
  }

  // --- Bildirishnomalar ---
  async function refreshBadge() {
    try {
      const { unread } = await api("/notifications/unread-count/");
      const badge = document.getElementById("bell-count");
      const bell = document.getElementById("bell");
      bell.hidden = false;
      badge.textContent = unread;
      badge.hidden = unread === 0;
    } catch (e) { /* jim */ }
  }

  // Foydalanuvchi hozir "Shikoyat" formasiga yoki taklif narxi maydoniga
  // yozayotgan bo'lsa, fon yangilanishi (pull-to-refresh, visibilitychange)
  // ro'yxatni qayta qurib, yozilgan matnni yo'qotib yubormasligi kerak.
  function hasOpenFormFocus() {
    const active = document.activeElement;
    if (!active || !["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) return false;
    return !!active.closest(".report-form, .offer-form, .pet-edit-form");
  }

  function refreshCurrentTab() {
    const tasks = [refreshBadge()];
    if (hasOpenFormFocus()) return Promise.all(tasks);
    if (currentTab === "calls" || currentTab === "home") tasks.push(loadCalls());
    if (currentTab === "tender" || currentTab === "home") tasks.push(loadTender());
    return Promise.all(tasks);
  }

  // Pastga tortish orqali yangilash (pull-to-refresh) — telefon ilovalaridagidek.
  function setupPullToRefresh(onRefresh) {
    const indicator = document.createElement("div");
    indicator.textContent = "⬇️ Yangilash uchun torting";
    indicator.style.cssText = "position:fixed;top:0;left:0;right:0;text-align:center;font-size:12px;font-weight:700;color:var(--muted);padding:10px;background:var(--bg);transform:translateY(-100%);transition:transform .15s;z-index:80";
    document.body.appendChild(indicator);
    let startY = null;
    document.addEventListener("touchstart", (e) => {
      startY = window.scrollY <= 0 ? e.touches[0].clientY : null;
    }, { passive: true });
    document.addEventListener("touchmove", (e) => {
      if (startY == null) return;
      const dy = e.touches[0].clientY - startY;
      if (dy > 0 && window.scrollY <= 0) {
        indicator.style.transform = `translateY(${Math.min(dy / 80, 1) * 100 - 100}%)`;
        indicator.textContent = dy > 70 ? "🔄 Qo'yib yuboring" : "⬇️ Yangilash uchun torting";
      }
    }, { passive: true });
    document.addEventListener("touchend", (e) => {
      if (startY == null) return;
      const dy = e.changedTouches[0].clientY - startY;
      startY = null;
      if (dy > 70) {
        indicator.textContent = "🔄 Yangilanmoqda...";
        indicator.style.transform = "translateY(0)";
        Promise.resolve(onRefresh()).finally(() => {
          setTimeout(() => { indicator.style.transform = "translateY(-100%)"; }, 400);
        });
      } else {
        indicator.style.transform = "translateY(-100%)";
      }
    }, { passive: true });
  }

  const NOTIF_ICON = {
    call_new: "📥", call_status: "🔔", tender_new: "📢", offer_new: "💬",
    offer_accepted: "✅", offer_declined: "❌", review_new: "⭐",
  };
  const NOTIF_TARGET_TAB = {
    call_new: "calls", call_status: "calls", tender_new: "tender",
    offer_new: "tender", offer_accepted: "tender", offer_declined: "tender", review_new: "profile",
  };

  function timeAgo(iso) {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "hozir";
    if (diff < 3600) return Math.floor(diff / 60) + " daqiqa oldin";
    if (diff < 86400) return Math.floor(diff / 3600) + " soat oldin";
    return Math.floor(diff / 86400) + " kun oldin";
  }

  function notifCardEl(n) {
    const li = document.createElement("li");
    li.className = "notif-card" + (n.is_read ? "" : " unread");
    li.innerHTML = `
      <div class="notif-icon">${NOTIF_ICON[n.kind] || "🔔"}</div>
      <div class="notif-body">
        <div class="t">${n.title || n.kind_display}</div>
        ${n.body ? `<div class="s">${n.body}</div>` : ""}
        <div class="time">${timeAgo(n.created_at)}</div>
      </div>`;
    li.onclick = () => {
      const target = NOTIF_TARGET_TAB[n.kind];
      if (target) goTab(target);
    };
    return li;
  }

  function renderNotifLoadMore(ul, nextUrl) {
    const old = document.getElementById("notif-more");
    if (old) old.remove();
    if (!nextUrl) return;
    const btn = document.createElement("button");
    btn.id = "notif-more";
    btn.className = "btn-secondary";
    btn.style.cssText = "width:100%;margin-top:8px";
    btn.textContent = I18N.t("load_more");
    btn.onclick = () => withBusy(btn, async () => {
      try {
        const data = await api(nextUrl);
        (data.results || data).forEach((n) => ul.appendChild(notifCardEl(n)));
        renderNotifLoadMore(ul, data.next || null);
      } catch (e) { popup(friendlyError(e)); }
    });
    ul.parentElement.insertBefore(btn, ul.nextSibling);
  }

  async function openNotifications() {
    document.querySelectorAll(".screen").forEach((s) => { s.hidden = s.id !== "screen-notifications"; });
    document.querySelector(".tabbar").hidden = true;
    const ul = document.getElementById("notif-list");
    ul.innerHTML = "";
    let items = [];
    let nextUrl = null;
    try {
      const data = await api("/notifications/");
      items = data.results || data;
      nextUrl = data.next || null;
    } catch (e) { /* jim */ }
    document.getElementById("notif-empty").hidden = items.length > 0;
    items.forEach((n) => ul.appendChild(notifCardEl(n)));
    renderNotifLoadMore(ul, nextUrl);
    try { await api("/notifications/read/", { method: "POST" }); } catch (e) {}
    refreshBadge();
  }

  // --- Navigatsiya ---
  function goTab(name) {
    currentTab = name;
    document.querySelector(".tabbar").hidden = false;
    document.querySelectorAll(".tab-btn").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    document.querySelectorAll(".screen").forEach((s) => { s.hidden = s.id !== "screen-" + name; });
    if (name === "calls") { loadCalls(); markRead(); }
    if (name === "tender") { loadTender(); markRead(); }
    if (name === "home") { loadCalls(); loadTender(); }
    if (name === "profile") {
      initLocationMap(profile.lat, profile.lng);
      if (locationMap) setTimeout(() => locationMap.container.fitToViewport(), 50);
    }
  }

  async function markRead() {
    try { await api("/notifications/read/", { method: "POST" }); } catch (e) {}
    refreshBadge();
  }

  // --- Ishga tushirish ---
  async function init() {
    if (tg) { tg.ready(); tg.expand(); }
    try {
      await authenticate();
      await loadProfileData();
      setGreeting();
      renderIdentity();
      fillForm(profile);
      await loadCalls();
      await loadTender();
      statusEl.hidden = true;
      appEl.hidden = false;
      maybeShowIdentityOnboarding();
      goTab("home");

      document.getElementById("home-available").onchange = (e) => setAvailability(e.target.checked);
      document.getElementById("is_available").onchange = (e) => setAvailability(e.target.checked);
      document.getElementById("profile-edit-btn").onclick = () => {
        const wrap = document.getElementById("profile-edit-wrap");
        wrap.hidden = !wrap.hidden;
      };
      const photoInput = document.getElementById("photo-input");
      document.getElementById("profile-avatar").onclick = () => photoInput.click();
      document.getElementById("profile-avatar-cam").onclick = () => photoInput.click();
      photoInput.onchange = () => {
        if (photoInput.files[0]) uploadPhoto(photoInput.files[0]);
        photoInput.value = "";
      };
      const licenseInput = document.getElementById("license-input");
      const licenseBtn = document.getElementById("license-upload-btn");
      licenseBtn.onclick = () => licenseInput.click();
      licenseInput.onchange = () => withBusy(licenseBtn, async () => {
        if (licenseInput.files[0]) await uploadLicense(licenseInput.files[0]);
        licenseInput.value = "";
      });
      const editSaveBtn = document.getElementById("edit-save");
      editSaveBtn.onclick = () => withBusy(editSaveBtn, saveIdentity);
      const saveBtn = document.getElementById("save-btn");
      saveBtn.onclick = () => withBusy(saveBtn, save);
      document.getElementById("city").onchange = (e) => {
        fillDistrictOptions(e.target.value, null);
        saveCityDistrict();
        // Hali aniq joylashuv belgilanmagan bo'lsa (GPS/xarita bilan), viloyat
        // markaziga qo'yamiz — shunda vet mijozlarga darhol xaritada ko'rinadi.
        if (window._lat == null) {
          const region = (window.UZ_REGIONS || []).find((r) => r.name === e.target.value);
          if (region && region.center) {
            setLocation(region.center[0], region.center[1]);
            if (locationMap) locationMap.setCenter(region.center, 11);
          }
        }
      };
      document.getElementById("district").onchange = () => saveCityDistrict();
      const svcAddBtn = document.getElementById("svc-add");
      svcAddBtn.onclick = () => withBusy(svcAddBtn, addService);
      document.getElementById("geo-btn").onclick = captureLocation;
      const geocodeBtn = document.getElementById("geocode-btn");
      geocodeBtn.onclick = () => withBusy(geocodeBtn, geocodeAddress);
      document.getElementById("bell").onclick = openNotifications;
      document.getElementById("notif-back-btn").onclick = () => goTab(currentTab);
      document.getElementById("help-row").onclick = openSupport;
      document.getElementById("privacy-row").onclick = () => { document.getElementById("privacy-modal").hidden = false; };
      document.getElementById("oferta-row").onclick = () => {
        const url = location.origin + "/legal/oferta-vet.html";
        if (tg && tg.openLink) tg.openLink(url); else window.open(url, "_blank");
      };
      document.getElementById("privacy-close").onclick = () => { document.getElementById("privacy-modal").hidden = true; };
      const onbSaveBtn = document.getElementById("onb-save");
      document.getElementById("onb-city").onchange = (e) => fillOnbDistrictOptions(e.target.value);
      onbSaveBtn.onclick = () => withBusy(onbSaveBtn, async () => {
        const ok = await saveOnboarding();
        if (ok) {
          document.getElementById("identity-modal").hidden = true;
          goTab("profile");
          // Yangi vet rasmni qanday qo'yishni bilmasligi mumkin — kamera belgisini bir lahza urg'ulaymiz.
          const cam = document.getElementById("profile-avatar-cam");
          cam.classList.add("pulse");
          setTimeout(() => cam.classList.remove("pulse"), 2600);
        }
      });
      document.getElementById("onb-skip").onclick = () => { document.getElementById("identity-modal").hidden = true; };
      document.getElementById("lang-row").onclick = () => withBusy(document.getElementById("lang-row"), async () => {
        const newLang = me.language === "ru" ? "uz" : "ru";
        try {
          me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ language: newLang }) });
          I18N.setLang(me.language);
          I18N.applyStatic();
          renderIdentity();
          if (profile) fillForm(profile);
          popup(newLang === "ru" ? "Til: Русский" : "Til: O'zbekcha");
        } catch (e) { popup(friendlyError(e)); }
      });
      document.getElementById("calls-search").oninput = renderCallsList;
      document.querySelectorAll("#calls-status-filter .chip").forEach((chip) => {
        chip.onclick = () => {
          document.querySelectorAll("#calls-status-filter .chip").forEach((c) => c.classList.remove("active"));
          chip.classList.add("active");
          callsStatusFilter = chip.dataset.status;
          renderCallsList();
        };
      });

      document.querySelectorAll(".tab-btn").forEach((t) => { t.onclick = () => goTab(t.dataset.tab); });
      document.querySelectorAll("[data-goto]").forEach((el) => { el.onclick = () => goTab(el.dataset.goto); });

      refreshBadge();
      setInterval(refreshBadge, 20000);
      setupPullToRefresh(refreshCurrentTab);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState !== "visible") return;
        refreshCurrentTab();
      });
    } catch (e) {
      if (e.message !== "no-telegram") setStatus("Xatolik: " + e.message);
    }
  }

  init();
})();
