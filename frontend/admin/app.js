/* Vet-App admin panel — vanilla JS. Barcha foydalanuvchi matnlari esc() bilan
   ekranlanadi (XSS'dan himoya), token localStorage'da saqlanadi. */
(function () {
  "use strict";

  const API = "/api/v1/admin";
  const TOKEN_KEY = "vetadmin_token";
  const ME_KEY = "vetadmin_me";

  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const ICONS = {
    dashboard: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    vets: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    calls: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>',
    tenders: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
    reviews: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    reports: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
    notifications: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  };
  const svg = (name) => `<svg viewBox="0 0 24 24">${ICONS[name]}</svg>`;

  // ---------- Yordamchi ko'rinish funksiyalari ----------
  const STATUS_LABEL = {
    pending: ["Kutilmoqda", "amber"], accepted: ["Qabul qilindi", "blue"], on_way: ["Yo'lda", "blue"],
    completed: ["Yakunlandi", "green"], rejected: ["Rad etildi", "red"], cancelled: ["Bekor qilindi", "red"],
    open: ["Ochiq", "amber"], assigned: ["Vet tayinlandi", "blue"], expired: ["Muddati tugadi", "gray"],
  };
  const TYPE_LABEL = { home: "🏠 Uyga", online: "💬 Online", contact: "📞 Kontakt" };
  const REASON_LABEL = {
    no_show: "Kelmadi / javob bermadi", rude: "Muomalasi yomon", fraud: "Firibgarlik",
    quality: "Xizmat sifati past", other: "Boshqa",
  };
  const ROLE_LABEL = { client: ["Mijoz", "blue"], vet: ["Veterinar", "green"], admin: ["Admin", "amber"] };

  const badge = (text, color) => `<span class="badge b-${color}">${esc(text)}</span>`;
  const statusBadge = (s) => { const x = STATUS_LABEL[s] || [s, "gray"]; return badge(x[0], x[1]); };
  const money = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString("ru-RU") + " so'm");
  const fmtDate = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
  };
  const avatarHtml = (name, photo) => {
    const initial = esc((name || "?").trim().charAt(0).toUpperCase() || "?");
    return `<span class="avatar">${photo ? `<img src="${esc(photo)}" alt="" />` : initial}</span>`;
  };
  const userCell = (name, sub, photo) =>
    `<div class="cell-user">${avatarHtml(name, photo)}<div><div class="name">${esc(name || "—")}</div>${sub ? `<div class="sub">${esc(sub)}</div>` : ""}</div></div>`;

  // ---------- Bo'limlar konfiguratsiyasi ----------
  const SECTIONS = {
    dashboard: { title: "Bosh sahifa", icon: "dashboard" },
    vets: {
      title: "Veterinarlar", icon: "vets", endpoint: "/vets/", searchable: true, tabParam: "verified",
      tabs: [["Barchasi", ""], ["Tasdiqlangan", "1"], ["Tasdiqlanmagan", "0"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Veterinar", (r) => userCell(r.full_name.trim() || r.username, r.phone || "@" + r.username, r.photo)],
        ["Shahar / Klinika", (r) => `${esc(r.city || "—")}<div class="sub muted">${esc(r.clinic_name || "")}</div>`],
        ["Mutaxassislik", (r) => `<div class="clip">${esc(r.specializations.join(", ") || "—")}</div>`],
        ["Reyting", (r) => `<span class="stars">★</span> ${Number(r.rating_avg).toFixed(1)} <span class="muted">(${r.rating_count})</span>`],
        ["Hujjat", (r) => r.license_document ? `<a href="${esc(r.license_document)}" target="_blank" rel="noopener">📎 Ko'rish</a>` : `<span class="muted">Yuklanmagan</span>`],
        ["Hamyon", (r) => money(r.wallet_balance)],
        ["Holat", (r) => `<div class="badges">${r.is_verified ? badge("Tasdiqlangan", "green") : badge("Tasdiqlanmagan", "amber")}${r.is_available ? badge("Bo'sh", "blue") : badge("Band", "gray")}${r.is_top ? badge("TOP", "amber") : ""}${r.is_active ? "" : badge("Bloklangan", "red")}</div>`],
      ],
      actions: (r) => [
        { label: r.is_verified ? "Tasdiqni bekor qilish" : "✓ Tasdiqlash", danger: r.is_verified, run: () => post(`/vets/${r.id}/toggle-verify/`), ok: "Saqlandi" },
        {
          label: r.is_top ? "TOP'ni o'chirish" : "👑 TOP yoqish",
          danger: r.is_top,
          run: () => {
            if (r.is_top) return post(`/vets/${r.id}/toggle-top/`);
            const days = window.prompt("Necha kunga TOP yoqilsin?", "7");
            if (days === null || !Number(days)) throw new Error("Bekor qilindi");
            return post(`/vets/${r.id}/toggle-top/`, { days: Number(days) });
          },
          ok: "Saqlandi",
        },
        {
          label: "💰 Hamyonni to'ldirish/tuzatish",
          run: () => {
            const amount = window.prompt("Necha so'm qo'shilsin? (ayirish uchun manfiy son yozing, masalan -20000)", "50000");
            if (amount === null || amount.trim() === "" || Number.isNaN(Number(amount))) throw new Error("Bekor qilindi");
            return post(`/vets/${r.id}/wallet-adjust/`, { amount });
          },
          ok: "Hamyon yangilandi",
        },
      ],
    },
    users: {
      title: "Foydalanuvchilar", icon: "users", endpoint: "/users/", searchable: true, tabParam: "role",
      tabs: [["Barchasi", ""], ["Mijozlar", "client"], ["Veterinarlar", "vet"], ["Adminlar", "admin"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Foydalanuvchi", (r) => userCell(r.full_name, "@" + r.username, r.photo)],
        ["Rol", (r) => { const x = ROLE_LABEL[r.role] || [r.role, "gray"]; return badge(x[0], x[1]); }],
        ["Telefon", (r) => esc(r.phone || "—")],
        ["Til", (r) => esc((r.language || "").toUpperCase())],
        ["Qo'shilgan", (r) => fmtDate(r.date_joined)],
        ["Holat", (r) => (r.is_active ? badge("Faol", "green") : badge("Bloklangan", "red"))],
      ],
      actions: (r) => [
        { label: r.is_active ? "🚫 Bloklash" : "Blokdan chiqarish", danger: r.is_active, confirm: r.is_active ? `"${r.full_name}" bloklansinmi?` : null, run: () => post(`/users/${r.id}/toggle-active/`), ok: "Saqlandi" },
        { label: "🗑 Butunlay o'chirish", danger: true, confirm: `"${r.full_name}" butunlay o'chirilsinmi? Bu amalni qaytarib bo'lmaydi — uning barcha chaqiruvlari, izohlari va (vet bo'lsa) profili ham birga o'chadi.`, run: () => del(`/users/${r.id}/`), ok: "Foydalanuvchi o'chirildi" },
      ],
    },
    calls: {
      title: "Chaqiruvlar", icon: "calls", endpoint: "/calls/", tabParam: "status",
      tabs: [["Barchasi", ""], ["Kutilmoqda", "pending"], ["Qabul qilindi", "accepted"], ["Yo'lda", "on_way"], ["Yakunlandi", "completed"], ["Rad etildi", "rejected"], ["Bekor qilindi", "cancelled"], ["Muddati tugadi", "expired"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Mijoz", (r) => userCell(r.client_name)],
        ["Veterinar", (r) => esc(r.vet_name || "—")],
        ["Hayvon", (r) => esc(r.pet_info ? `${r.pet_info.name} (${r.pet_info.species})` : "—")],
        ["Turi", (r) => TYPE_LABEL[r.type] || esc(r.type)],
        ["Izoh", (r) => `<div class="clip">${esc(r.note || "—")}</div>`],
        ["Narx", (r) => money(r.price_agreed)],
        ["Sana", (r) => fmtDate(r.created_at)],
        ["Holat", (r) => statusBadge(r.status)],
      ],
    },
    tenders: {
      title: "Ochiq so'rovlar (tender)", icon: "tenders", endpoint: "/tenders/", tabParam: "status",
      tabs: [["Barchasi", ""], ["Ochiq", "open"], ["Vet tayinlandi", "assigned"], ["Yakunlandi", "completed"], ["Bekor qilindi", "cancelled"], ["Muddati tugadi", "expired"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Mijoz", (r) => userCell(r.client_name)],
        ["Mutaxassislik", (r) => esc(r.specialization_name || "—")],
        ["Turi", (r) => TYPE_LABEL[r.type] || esc(r.type)],
        ["Shahar", (r) => esc(r.city || "—")],
        ["Byudjet", (r) => money(r.budget_hint)],
        ["Takliflar", (r) => r.offers_count],
        ["Sana", (r) => fmtDate(r.created_at)],
        ["Holat", (r) => statusBadge(r.status)],
      ],
    },
    reviews: {
      title: "Izohlar", icon: "reviews", endpoint: "/reviews/",
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Mijoz", (r) => userCell(r.client_name)],
        ["Veterinar", (r) => esc(r.vet_name || "—")],
        ["Baho", (r) => `<span class="stars">${"★".repeat(r.stars)}${"☆".repeat(5 - r.stars)}</span>`],
        ["Izoh", (r) => `<div class="clip" title="${esc(r.comment)}">${esc(r.comment || "—")}</div>`],
        ["Sana", (r) => fmtDate(r.created_at)],
      ],
      actions: (r) => [
        { label: "🗑 O'chirish", danger: true, confirm: "Bu izoh o'chirilsinmi? Vet reytingi qayta hisoblanadi.", run: () => del(`/reviews/${r.id}/`), ok: "Izoh o'chirildi" },
      ],
    },
    reports: {
      title: "Shikoyatlar", icon: "reports", endpoint: "/reports/", tabParam: "resolved",
      tabs: [["Barchasi", ""], ["Ko'rib chiqilmagan", "0"], ["Ko'rib chiqilgan", "1"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Kim shikoyat qildi", (r) => userCell(r.reporter_name)],
        ["Kimdan", (r) => userCell(r.reported_name)],
        ["Sabab", (r) => esc(REASON_LABEL[r.reason] || r.reason)],
        ["Izoh", (r) => `<div class="clip" title="${esc(r.comment)}">${esc(r.comment || "—")}</div>`],
        ["Sana", (r) => fmtDate(r.created_at)],
        ["Holat", (r) => (r.is_resolved ? badge("Ko'rib chiqilgan", "green") : badge("Yangi", "red"))],
      ],
      actions: (r) => [
        ...(r.is_resolved ? [] : [{ label: "✓ Ko'rib chiqildi", run: () => post(`/reports/${r.id}/resolve/`), ok: "Belgilandi" }]),
        { label: "🚫 Foydalanuvchini bloklash/ochish", danger: true, confirm: `"${r.reported_name}" holati o'zgartirilsinmi?`, run: () => post(`/users/${r.reported_user_id}/toggle-active/`), ok: "Foydalanuvchi holati o'zgardi" },
      ],
    },
    notifications: {
      title: "Bildirishnomalar", icon: "notifications", endpoint: "/notifications/", tabParam: "failed",
      tabs: [["Barchasi", ""], ["Yetkazilmagan", "1"]],
      columns: [
        ["ID", (r) => "#" + r.id],
        ["Qabul qiluvchi", (r) => userCell(r.recipient_name)],
        ["Bot", (r) => r.bot === "vet" ? "Vet" : "Mijoz"],
        ["Sarlavha", (r) => esc(r.title || "—")],
        ["Xatolik", (r) => r.error ? `<div class="clip" title="${esc(r.error)}">${esc(r.error)}</div>` : "—"],
        ["Sana", (r) => fmtDate(r.created_at)],
        ["Holat", (r) => (r.is_sent ? badge("Yetkazildi", "green") : badge("Yetkazilmadi", "red"))],
      ],
      actions: (r) => [
        ...(r.is_sent ? [] : [{ label: "↻ Qayta yuborish", run: () => post(`/notifications/${r.id}/retry/`), ok: "Navbatga qo'yildi" }]),
      ],
    },
  };

  const DASH_CARDS = [
    ["total_clients", "Mijozlar", "users", "blue", "users"],
    ["total_vets", "Veterinarlar", "vets", "green", "vets"],
    ["unverified_vets", "Tasdiqlanmagan vetlar", "vets", "amber", "vets", "0"],
    ["verified_vets", "Tasdiqlangan vetlar", "vets", "green", "vets", "1"],
    ["active_calls", "Faol chaqiruvlar", "calls", "blue", "calls"],
    ["calls_today", "Bugungi chaqiruvlar", "calls", "amber", "calls"],
    ["completed_calls", "Yakunlangan chaqiruvlar", "calls", "green", "calls", "completed"],
    ["open_tenders", "Ochiq tenderlar", "tenders", "amber", "tenders", "open"],
    ["total_reviews", "Izohlar", "reviews", "amber", "reviews"],
    ["unresolved_reports", "Ko'rib chiqilmagan shikoyatlar", "reports", "red", "reports", "0"],
    ["failed_notifications", "Yetkazilmagan bildirishnomalar", "notifications", "red", "notifications", "1"],
  ];
  // Pilot KPI'lari — oddiy son emas, shuning uchun alohida formatlanadi (30 kunlik oyna).
  const KPI_CARDS = [
    ["avg_response_minutes", "O'rtacha javob vaqti", "calls", "blue", "calls", "", (v) => v == null ? "—" : v + " daq"],
    ["completion_rate", "Yakunlanish ulushi", "calls", "green", "calls", "completed", (v) => v == null ? "—" : v + "%"],
    ["avg_offers_per_tender", "O'rtacha taklif / tender", "tenders", "amber", "tenders", "", (v) => v == null ? "—" : v],
  ];

  // ---------- Holat ----------
  const state = { section: "dashboard", tab: "", q: "", page: 1, stats: null };
  let searchTimer = null;

  // ---------- Tarmoq ----------
  async function request(path, options = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(path.startsWith("http") ? path : API + path, Object.assign({}, options, { headers }));
    if (res.status === 401 || res.status === 403) {
      if (path !== "/login/") { logout(); throw new Error("Sessiya tugadi, qaytadan kiring."); }
    }
    if (!res.ok) {
      let msg = "Xatolik (" + res.status + ")";
      try { const d = await res.json(); msg = d.detail || msg; } catch (e) { /* jim */ }
      throw new Error(msg);
    }
    return res.status === 204 ? null : res.json();
  }
  const post = (p, body) => request(p, body ? { method: "POST", body: JSON.stringify(body) } : { method: "POST" });
  const del = (p) => request(p, { method: "DELETE" });

  function toast(msg, isError) {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast" + (isError ? " error" : "");
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 2600);
  }

  // ---------- Auth ----------
  function showLogin() {
    $("shell").hidden = true;
    $("login-screen").hidden = false;
    $("login-password").value = "";
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ME_KEY);
    showLogin();
  }

  function showShell() {
    $("login-screen").hidden = true;
    $("shell").hidden = false;
    let me = null;
    try { me = JSON.parse(localStorage.getItem(ME_KEY) || "null"); } catch (e) { /* jim */ }
    const name = (me && me.full_name) || "Admin";
    $("me-name").textContent = name;
    $("me-avatar").textContent = name.charAt(0).toUpperCase();
    renderNav();
    go(location.hash.replace("#", "") || "dashboard");
    refreshBell();
  }

  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("login-btn");
    const errEl = $("login-error");
    errEl.hidden = true;
    btn.disabled = true;
    try {
      const data = await request("/login/", {
        method: "POST",
        body: JSON.stringify({ username: $("login-username").value.trim(), password: $("login-password").value }),
      });
      localStorage.setItem(TOKEN_KEY, data.access);
      localStorage.setItem(ME_KEY, JSON.stringify(data.user));
      showShell();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  $("logout-btn").onclick = logout;

  // ---------- Navigatsiya ----------
  function renderNav() {
    $("nav").innerHTML = Object.keys(SECTIONS).map((key) => {
      const s = SECTIONS[key];
      const n = key === "reports" ? state.reportCount : key === "notifications" ? state.notifFailedCount : 0;
      const count = n ? `<span class="badge-count">${n}</span>` : "";
      return `<button class="nav-item${key === state.section ? " active" : ""}" data-section="${key}">${svg(s.icon)}<span>${esc(s.title.split(" (")[0])}</span>${count}</button>`;
    }).join("");
    $("nav").querySelectorAll(".nav-item").forEach((b) => { b.onclick = () => go(b.dataset.section); });
  }

  async function refreshBell() {
    try {
      const st = await request("/stats/");
      state.stats = st;
      state.reportCount = st.unresolved_reports;
      state.notifFailedCount = st.failed_notifications;
      $("bell-count").textContent = st.unresolved_reports;
      $("bell-count").hidden = st.unresolved_reports === 0;
      renderNav();
    } catch (e) { /* jim */ }
  }
  $("bell-btn").onclick = () => go("reports", "0");

  function go(section, tab) {
    if (!SECTIONS[section]) section = "dashboard";
    state.section = section;
    state.tab = tab || "";
    state.q = "";
    state.page = 1;
    $("search-input").value = "";
    location.hash = section;
    renderNav();
    load();
  }

  // ---------- Yuklash va chizish ----------
  async function load() {
    const sec = SECTIONS[state.section];
    $("page-title").textContent = sec.title;
    $("search-input").parentElement.style.visibility = sec.searchable ? "visible" : "hidden";
    if (state.section === "dashboard") { $("tabs").innerHTML = ""; return loadDashboard(); }
    renderTabs(sec);
    $("view").innerHTML = '<div class="loading">Yuklanmoqda...</div>';
    const params = new URLSearchParams();
    if (sec.tabParam && state.tab !== "") params.set(sec.tabParam, state.tab);
    if (state.q) params.set("q", state.q);
    if (state.page > 1) params.set("page", state.page);
    const section = state.section;
    try {
      const data = await request(sec.endpoint + (params.toString() ? "?" + params : ""));
      if (section !== state.section) return; // foydalanuvchi boshqa bo'limga o'tib ketgan
      renderTable(sec, data);
    } catch (e) {
      $("view").innerHTML = `<div class="empty">${esc(e.message)}</div>`;
    }
  }

  function renderTabs(sec) {
    if (!sec.tabs) { $("tabs").innerHTML = ""; return; }
    $("tabs").innerHTML = sec.tabs.map(([label, val]) =>
      `<button class="tab${state.tab === val ? " active" : ""}" data-val="${esc(val)}">${esc(label)}</button>`).join("");
    $("tabs").querySelectorAll(".tab").forEach((b) => {
      b.onclick = () => { state.tab = b.dataset.val; state.page = 1; load(); };
    });
  }

  function renderTable(sec, data) {
    const rows = data.results || data;
    if (!rows.length) { $("view").innerHTML = '<div class="empty">Ma\'lumot topilmadi</div>'; return; }
    const hasActions = typeof sec.actions === "function";
    const head = sec.columns.map((c) => `<th>${esc(c[0])}</th>`).join("") + (hasActions ? "<th></th>" : "");
    const body = rows.map((r, i) => {
      const cells = sec.columns.map((c) => `<td>${c[1](r)}</td>`).join("");
      const menu = hasActions
        ? `<td style="text-align:right"><div class="menu"><button class="menu-btn" data-row="${i}">⋮</button></div></td>` : "";
      return `<tr class="row">${cells}${menu}</tr>`;
    }).join("");
    const pageSize = 20;
    const pages = Math.max(1, Math.ceil((data.count || rows.length) / pageSize));
    $("view").innerHTML = `
      <div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
      <div class="pager">
        <span>Jami: ${data.count != null ? data.count : rows.length}</span>
        <span>
          <button id="prev-btn" ${data.previous ? "" : "disabled"}>‹ Oldingi</button>
          <span style="margin:0 10px">${state.page} / ${pages}</span>
          <button id="next-btn" ${data.next ? "" : "disabled"}>Keyingi ›</button>
        </span>
      </div>`;
    $("prev-btn").onclick = () => { state.page--; load(); };
    $("next-btn").onclick = () => { state.page++; load(); };
    if (hasActions) {
      $("view").querySelectorAll(".menu-btn").forEach((btn) => {
        btn.onclick = (e) => { e.stopPropagation(); openMenu(btn, sec.actions(rows[Number(btn.dataset.row)])); };
      });
    }
  }

  function closeMenus() { document.querySelectorAll(".menu-list").forEach((m) => m.remove()); }
  document.addEventListener("click", closeMenus);

  function openMenu(btn, actions) {
    const wasOpen = btn.dataset.open === "1";
    closeMenus();
    document.querySelectorAll(".menu-btn").forEach((b) => { b.dataset.open = "0"; });
    if (wasOpen) return;
    btn.dataset.open = "1";
    const list = document.createElement("div");
    list.className = "menu-list";
    const rect = btn.getBoundingClientRect();
    list.style.position = "fixed";
    list.style.top = rect.bottom + 4 + "px";
    list.style.right = Math.max(8, window.innerWidth - rect.right) + "px";
    actions.forEach((a) => {
      const item = document.createElement("button");
      item.textContent = a.label;
      if (a.danger) item.className = "danger";
      item.onclick = async (e) => {
        e.stopPropagation();
        closeMenus();
        if (a.confirm && !window.confirm(a.confirm)) return;
        try {
          await a.run();
          toast(a.ok || "Bajarildi");
          load();
          refreshBell();
        } catch (err) { toast(err.message, true); }
      };
      list.appendChild(item);
    });
    document.body.appendChild(list);
  }

  async function loadDashboard() {
    $("view").innerHTML = '<div class="loading">Yuklanmoqda...</div>';
    try {
      const st = await request("/stats/");
      state.stats = st;
      const colors = { blue: ["var(--blue-soft)", "var(--blue)"], green: ["var(--green-soft)", "var(--green)"], amber: ["var(--amber-soft)", "var(--amber)"], red: ["var(--red-soft)", "var(--red)"] };
      const card = (bg, fg, icon, value, label, target, tab, alert) =>
        `<button class="stat-card link${alert || ""}" data-target="${target}" data-tab="${tab || ""}">
          <span class="ic" style="background:${bg};color:${fg}">${svg(icon)}</span>
          <span class="v">${value}</span>
          <span class="l">${esc(label)}</span>
        </button>`;
      const mainCards = DASH_CARDS.map(([key, label, icon, color, target, tab]) => {
        const [bg, fg] = colors[color];
        const alert = ["unresolved_reports", "failed_notifications"].includes(key) && st[key] > 0 ? " alert" : "";
        return card(bg, fg, icon, Number(st[key]).toLocaleString("ru-RU"), label, target, tab, alert);
      }).join("");
      const kpiCards = KPI_CARDS.map(([key, label, icon, color, target, tab, fmt]) => {
        const [bg, fg] = colors[color];
        return card(bg, fg, icon, esc(String(fmt(st[key]))), label, target, tab);
      }).join("");
      $("view").innerHTML = `<div class="stat-grid">${mainCards}</div>
        <p class="muted" style="margin:22px 0 10px;font-size:13px">Pilot ko'rsatkichlari (so'nggi 30 kun)</p>
        <div class="stat-grid">${kpiCards}</div>`;
      $("view").querySelectorAll(".stat-card").forEach((c) => { c.onclick = () => go(c.dataset.target, c.dataset.tab); });
    } catch (e) {
      $("view").innerHTML = `<div class="empty">${esc(e.message)}</div>`;
    }
  }

  $("search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.q = e.target.value.trim(); state.page = 1; load(); }, 350);
  });

  // ---------- Ishga tushirish ----------
  if (localStorage.getItem(TOKEN_KEY)) showShell(); else showLogin();
})();
