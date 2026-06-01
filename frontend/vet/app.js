/* Veterinar Mini App — profil to'ldirish (ARCHITECTURE.md 3, 6.3). */
(function () {
  "use strict";

  const API = "/api/v1";
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  const statusEl = document.getElementById("status");
  const appEl = document.getElementById("app");

  let token = null;
  let allSpecs = [];
  let selectedSpecs = new Set();

  function setStatus(msg) {
    statusEl.textContent = msg;
  }

  // --- API yordamchisi (JWT bilan) ---
  async function api(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(API + path, Object.assign({}, options, { headers }));
    if (!res.ok) {
      const body = await res.text();
      throw new Error("API " + res.status + ": " + body);
    }
    return res.status === 204 ? null : res.json();
  }

  // --- 1. Telegram initData orqali kirish ---
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
    return data.user;
  }

  // --- 2. Ma'lumotlarni yuklash ---
  async function loadAll() {
    allSpecs = await api("/specializations/");
    return await api("/vets/me/");
  }

  // --- Mutaxassislik chiplari ---
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

  // --- Xizmatlar ---
  function renderServices(services) {
    const ul = document.getElementById("services");
    ul.innerHTML = "";
    services.forEach((svc) => {
      const li = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = svc.title + " — " + Number(svc.price).toLocaleString() + " so'm";
      const del = document.createElement("button");
      del.className = "del";
      del.textContent = "🗑";
      del.onclick = async () => {
        await api("/vets/me/services/" + svc.id + "/", { method: "DELETE" });
        li.remove();
      };
      li.append(label, del);
      ul.appendChild(li);
    });
  }

  async function addService() {
    const title = document.getElementById("svc-title").value.trim();
    const price = document.getElementById("svc-price").value;
    if (!title || !price) return;
    await api("/vets/me/services/", {
      method: "POST",
      body: JSON.stringify({ title, price, duration_min: 30 }),
    });
    document.getElementById("svc-title").value = "";
    document.getElementById("svc-price").value = "";
    renderServices(await api("/vets/me/services/"));
  }

  // --- Formani to'ldirish ---
  function fillForm(p) {
    document.getElementById("bio").value = p.bio || "";
    document.getElementById("clinic_name").value = p.clinic_name || "";
    document.getElementById("experience_years").value = p.experience_years || 0;
    document.getElementById("city").value = p.city || "";
    document.getElementById("district").value = p.district || "";
    document.getElementById("address").value = p.address || "";
    document.getElementById("is_available").checked = !!p.is_available;
    document.getElementById("accepts_home_visit").checked = !!p.accepts_home_visit;
    document.getElementById("accepts_online").checked = !!p.accepts_online;
    selectedSpecs = new Set((p.specializations || []).map((s) => s.id));
    if (p.is_verified) {
      document.getElementById("verified-badge").textContent = "✅ Profil tasdiqlangan";
    }
    renderSpecs();
    renderServices(p.services || []);
  }

  // --- Saqlash ---
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
    await api("/vets/me/", { method: "PATCH", body: JSON.stringify(payload) });
    // Bo'sh/band holatni alohida endpoint orqali
    await api("/vets/me/availability/", {
      method: "PUT",
      body: JSON.stringify({
        is_available: document.getElementById("is_available").checked,
      }),
    });
    if (tg) tg.showPopup ? tg.showPopup({ message: "Saqlandi ✅" }) : alert("Saqlandi ✅");
  }

  // --- Geolokatsiya ---
  function captureLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      window._lat = pos.coords.latitude;
      window._lng = pos.coords.longitude;
      document.getElementById("geo-info").textContent =
        "📍 " + window._lat.toFixed(5) + ", " + window._lng.toFixed(5);
    });
  }

  function popup(msg) {
    tg && tg.showPopup ? tg.showPopup({ message: msg }) : alert(msg);
  }

  // --- Kelgan chaqiruvlar (REJIM A) ---
  const STATUS_LABEL = {
    pending: "Kutilmoqda", accepted: "Qabul qilindi", on_way: "Yo'lda",
    completed: "Yakunlandi", rejected: "Rad etildi", cancelled: "Bekor qilindi",
  };
  // Har holatda mavjud amallar
  const NEXT_ACTIONS = {
    pending: [["accept", "Qabul qilish"], ["reject", "Rad etish", "danger"]],
    accepted: [["on_way", "Yo'ldaman"], ["complete", "Yakunlash"]],
    on_way: [["complete", "Yakunlash"]],
  };

  async function loadCalls() {
    const data = await api("/requests/?role=vet");
    const items = data.results || data;
    const ul = document.getElementById("calls-list");
    ul.innerHTML = "";
    document.getElementById("calls-empty").hidden = items.length > 0;
    items.forEach((r) => {
      const li = document.createElement("li");
      li.className = "list-item";
      const typeIcon = { home: "🏠 Uyga", online: "💬 Online", contact: "📞 Kontakt" }[r.type] || r.type;
      const acts = (NEXT_ACTIONS[r.status] || [])
        .map((a) => `<button data-act="${a[0]}" class="${a[2] || ""}">${a[1]}</button>`)
        .join("");
      li.innerHTML = `
        <div class="title">${typeIcon} · ${r.pet_info?.name || "Hayvon"}</div>
        <div class="meta">${r.note || ""} ${r.address ? "📍 " + r.address : ""}</div>
        <span class="st st-${r.status}">${STATUS_LABEL[r.status] || r.status}</span>
        <div class="actions">${acts}</div>`;
      li.querySelectorAll(".actions button").forEach((btn) => {
        btn.onclick = async () => {
          try {
            await api("/requests/" + r.id + "/" + btn.dataset.act + "/", { method: "POST" });
            loadCalls();
          } catch (e) { popup("Xatolik: " + e.message); }
        };
      });
      ul.appendChild(li);
    });
  }

  // --- Tender lentasi (REJIM B) ---
  async function loadTender() {
    const data = await api("/service-requests/feed/");
    const items = data.results || data;
    const ul = document.getElementById("tender-list");
    ul.innerHTML = "";
    document.getElementById("tender-empty").hidden = items.length > 0;
    items.forEach((r) => {
      const li = document.createElement("li");
      li.className = "list-item";
      const typeIcon = { home: "🏠", online: "💬", contact: "📞" }[r.type] || "";
      li.innerHTML = `
        <div class="title">${typeIcon} ${r.specialization_info?.name || ""} · ${r.city || ""}</div>
        <div class="meta">${r.note || ""} ${r.budget_hint ? "💰 ~" + r.budget_hint : ""}</div>
        <div class="offer-form">
          <input type="number" placeholder="Narx" class="o-price" />
          <button class="o-send">Taklif</button>
        </div>`;
      const price = li.querySelector(".o-price");
      li.querySelector(".o-send").onclick = async () => {
        if (!price.value) return;
        try {
          await api("/service-requests/" + r.id + "/offer/", {
            method: "POST",
            body: JSON.stringify({ price: price.value }),
          });
          popup("Taklif yuborildi ✅");
          loadTender();
        } catch (e) { popup("Xatolik: " + e.message); }
      };
      ul.appendChild(li);
    });
  }

  // --- Bildirishnomalar (o'qilmaganlar belgisi) ---
  async function refreshBadge() {
    try {
      const { unread } = await api("/notifications/unread-count/");
      const badge = document.getElementById("bell-count");
      document.getElementById("bell").hidden = false;
      badge.textContent = unread;
      badge.hidden = unread === 0;
    } catch (e) { /* jim */ }
  }

  async function openNotifications() {
    let items = [];
    try {
      const data = await api("/notifications/");
      items = data.results || data;
    } catch (e) { return; }
    const text = items.length
      ? items.slice(0, 10).map((n) => "• " + (n.title || n.body)).join("\n")
      : "Bildirishnoma yo'q";
    popup(text);
    try { await api("/notifications/read/", { method: "POST" }); } catch (e) {}
    refreshBadge();
  }

  async function markRead() {
    try { await api("/notifications/read/", { method: "POST" }); } catch (e) {}
    refreshBadge();
  }

  // --- Tab almashish ---
  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.tab === name)
    );
    document.getElementById("tab-profile").hidden = name !== "profile";
    document.getElementById("tab-calls").hidden = name !== "calls";
    document.getElementById("tab-tender").hidden = name !== "tender";
    if (name === "calls") { loadCalls(); markRead(); }
    if (name === "tender") { loadTender(); markRead(); }
  }

  // --- Ishga tushirish ---
  async function init() {
    if (tg) { tg.ready(); tg.expand(); }
    try {
      setStatus("Yuklanmoqda...");
      const user = await authenticate();
      const profile = await loadAll();
      document.getElementById("who").textContent =
        (user.first_name || "") + " " + (user.last_name || "");
      fillForm(profile);
      statusEl.hidden = true;
      appEl.hidden = false;

      document.getElementById("save-btn").onclick = save;
      document.getElementById("svc-add").onclick = addService;
      document.getElementById("geo-btn").onclick = captureLocation;
      document.getElementById("bell").onclick = openNotifications;
      document.querySelectorAll(".tab").forEach((t) => {
        t.onclick = () => switchTab(t.dataset.tab);
      });
      refreshBadge();
      setInterval(refreshBadge, 20000);
    } catch (e) {
      if (e.message !== "no-telegram") setStatus("Xatolik: " + e.message);
    }
  }

  init();
})();
