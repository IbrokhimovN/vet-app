/* Mijoz Mini App — vet qidirish va ko'rish (ARCHITECTURE.md 6.2). */
(function () {
  "use strict";

  const API = "/api/v1";
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  const statusEl = document.getElementById("status");
  const listView = document.getElementById("list-view");
  const detailView = document.getElementById("detail-view");

  let token = null;
  let activeSpec = "";
  let coords = { lat: null, lng: null };
  let searchTimer = null;

  function setStatus(msg) { statusEl.textContent = msg; statusEl.hidden = false; }

  async function api(path, options = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(API + path, Object.assign({}, options, { headers }));
    if (!res.ok) throw new Error("API " + res.status + ": " + (await res.text()));
    return res.status === 204 ? null : res.json();
  }

  // --- Auth ---
  async function authenticate() {
    if (!tg || !tg.initData) {
      setStatus("⚠️ Bu sahifa Telegram ichida ochilishi kerak.");
      throw new Error("no-telegram");
    }
    const data = await api("/auth/telegram/", {
      method: "POST",
      body: JSON.stringify({ init_data: tg.initData, app: "client" }),
    });
    token = data.access;
  }

  // --- Mutaxassislik filtri ---
  async function loadSpecs() {
    const specs = await api("/specializations/");
    const box = document.getElementById("spec-filter");
    const mkChip = (slug, label) => {
      const el = document.createElement("div");
      el.className = "chip" + (slug === activeSpec ? " active" : "");
      el.textContent = label;
      el.onclick = () => {
        activeSpec = activeSpec === slug ? "" : slug;
        document.querySelectorAll("#spec-filter .chip").forEach((c) => c.classList.remove("active"));
        if (activeSpec) el.classList.add("active");
        search();
      };
      box.appendChild(el);
    };
    mkChip("", "Barchasi");
    specs.forEach((s) => mkChip(s.slug, (s.icon ? s.icon + " " : "") + s.name));
  }

  // --- Qidiruv ---
  async function search() {
    const params = new URLSearchParams();
    if (activeSpec) params.set("spec", activeSpec);
    const type = document.getElementById("type-filter").value;
    if (type) params.set("type", type);
    const sort = document.getElementById("sort").value;
    params.set("sort", sort);
    const q = document.getElementById("search-q").value.trim();
    if (q) params.set("q", q);
    if (sort === "distance" && coords.lat != null) {
      params.set("lat", coords.lat);
      params.set("lng", coords.lng);
    }
    const data = await api("/vets/?" + params.toString());
    renderList(data.results || data);
  }

  function renderList(vets) {
    const ul = document.getElementById("vet-list");
    ul.innerHTML = "";
    document.getElementById("empty").hidden = vets.length > 0;
    vets.forEach((v) => {
      const li = document.createElement("li");
      li.className = "vet-card";
      li.onclick = () => openDetail(v.id);

      const specs = v.specializations.map((s) => s.icon || s.name).join(" ");
      const dist = v.distance_km != null ? `📍 ${v.distance_km} km` : "";
      li.innerHTML = `
        <div class="avatar">${v.specializations[0]?.icon || "👨‍⚕️"}</div>
        <div class="info">
          <div class="name">${v.full_name || "Veterinar"}</div>
          <div class="sub">${v.clinic_name || v.city || ""} ${specs}</div>
          <div class="badges">
            ${v.is_top ? '<span class="badge top">TOP</span>' : ""}
            ${v.is_verified ? '<span class="badge verified">✓ Tasdiqlangan</span>' : ""}
            ${v.accepts_home_visit ? '<span class="badge">🏠 Uy</span>' : ""}
            ${v.accepts_online ? '<span class="badge">💬 Online</span>' : ""}
          </div>
        </div>
        <div class="right">
          <div class="rating">⭐ ${Number(v.rating_avg).toFixed(1)}</div>
          <div class="distance">${dist}</div>
        </div>`;
      ul.appendChild(li);
    });
  }

  // --- Vet sahifasi + chaqirish ---
  async function openDetail(id) {
    const v = await api("/vets/" + id + "/");
    const services = (v.services || [])
      .map((s) => `<div class="svc-row"><span>${s.title}</span><span>${Number(s.price).toLocaleString()} so'm</span></div>`)
      .join("") || '<p class="muted">Xizmatlar kiritilmagan</p>';
    const specs = v.specializations.map((s) => (s.icon ? s.icon + " " : "") + s.name).join(", ");

    // Vet qabul qiladigan chaqiruv turlari
    const types = [];
    if (v.accepts_home_visit) types.push(["home", "🏠 Uyga"]);
    if (v.accepts_online) types.push(["online", "💬 Online"]);
    types.push(["contact", "📞 Kontakt"]);

    document.getElementById("detail-content").innerHTML = `
      <div class="detail-head">
        <h2>${v.full_name || "Veterinar"}</h2>
        <p class="muted">${v.clinic_name || ""} ${v.city ? "· " + v.city : ""}</p>
        <p>⭐ ${Number(v.rating_avg).toFixed(1)} (${v.rating_count}) · ${v.experience_years} yil tajriba</p>
      </div>
      ${v.bio ? `<div class="detail-card"><h3>Haqida</h3><p>${v.bio}</p></div>` : ""}
      <div class="detail-card"><h3>Mutaxassislik</h3><p>${specs || "—"}</p></div>
      <div class="detail-card"><h3>Xizmatlar</h3>${services}</div>
      <div class="detail-card"><h3>Izohlar (${v.rating_count})</h3><div id="reviews">Yuklanmoqda...</div></div>
      <div class="booking">
        <h3>📞 Chaqirish</h3>
        <div class="type-opts" id="type-opts">
          ${types.map((t, i) => `<div class="type-opt${i === 0 ? " active" : ""}" data-type="${t[0]}">${t[1]}</div>`).join("")}
        </div>
        <textarea id="call-note" rows="2" placeholder="Muammoni qisqacha yozing..."></textarea>
      </div>
      <button class="btn-primary" id="call-btn">Yuborish</button>`;

    let chosenType = types[0][0];
    document.querySelectorAll("#type-opts .type-opt").forEach((el) => {
      el.onclick = () => {
        document.querySelectorAll("#type-opts .type-opt").forEach((x) => x.classList.remove("active"));
        el.classList.add("active");
        chosenType = el.dataset.type;
      };
    });

    document.getElementById("call-btn").onclick = async () => {
      const payload = {
        vet: v.id,
        type: chosenType,
        note: document.getElementById("call-note").value,
      };
      if (chosenType === "home" && coords.lat != null) {
        payload.lat = coords.lat;
        payload.lng = coords.lng;
      }
      try {
        await api("/requests/", { method: "POST", body: JSON.stringify(payload) });
        popup("So'rov yuborildi ✅");
        showList();
        switchTab("requests");
      } catch (e) {
        popup("Xatolik: " + e.message);
      }
    };

    loadReviews(v.id);
    listView.hidden = true;
    detailView.hidden = false;
  }

  // --- Vet izohlari ---
  async function loadReviews(vetId) {
    const box = document.getElementById("reviews");
    try {
      const reviews = await api("/vets/" + vetId + "/reviews/");
      if (!reviews.length) {
        box.innerHTML = '<p class="muted">Hali izoh yo\'q</p>';
        return;
      }
      box.innerHTML = reviews
        .map((r) => `
          <div class="review">
            <div class="review-head">${"⭐".repeat(r.stars)} <span class="muted">${r.client_name}</span></div>
            ${r.comment ? `<div class="review-body">${r.comment}</div>` : ""}
          </div>`)
        .join("");
    } catch (e) {
      box.innerHTML = "";
    }
  }

  function popup(msg) {
    tg && tg.showPopup ? tg.showPopup({ message: msg }) : alert(msg);
  }

  // --- So'rovlarim ---
  const STATUS_LABEL = {
    pending: "Kutilmoqda", accepted: "Qabul qilindi", on_way: "Yo'lda",
    completed: "Yakunlandi", rejected: "Rad etildi", cancelled: "Bekor qilindi",
  };
  async function loadMyRequests() {
    const data = await api("/requests/?role=client");
    const items = data.results || data;
    const ul = document.getElementById("my-requests");
    ul.innerHTML = "";
    document.getElementById("req-empty").hidden = items.length > 0;
    items.forEach((r) => {
      const li = document.createElement("li");
      li.className = "vet-card vet-card-col";
      const typeIcon = { home: "🏠", online: "💬", contact: "📞" }[r.type] || "";
      const canReview = r.status === "completed" && !r.has_review;
      li.innerHTML = `
        <div class="info">
          <div class="name">${typeIcon} ${r.vet_info?.full_name || "Veterinar"}</div>
          <div class="sub">${r.note || r.vet_info?.clinic_name || ""}</div>
          <div class="badges">
            <span class="st st-${r.status}">${STATUS_LABEL[r.status] || r.status}</span>
            ${r.has_review ? '<span class="badge">⭐ Baholandi</span>' : ""}
          </div>
        </div>
        ${canReview ? '<button class="btn-secondary review-btn">⭐ Baholash</button>' : ""}`;
      const btn = li.querySelector(".review-btn");
      if (btn) btn.onclick = () => openReviewForm(r.id, li);
      ul.appendChild(li);
    });
  }

  // --- Izoh qoldirish formasi (inline) ---
  function openReviewForm(callId, li) {
    if (li.querySelector(".review-form")) return;
    const form = document.createElement("div");
    form.className = "review-form";
    form.innerHTML = `
      <div class="stars-pick" id="stars-pick">
        ${[1, 2, 3, 4, 5].map((n) => `<span class="star" data-n="${n}">☆</span>`).join("")}
      </div>
      <textarea class="review-text" rows="2" placeholder="Izoh (ixtiyoriy)"></textarea>
      <button class="btn-primary review-send">Yuborish</button>`;
    let stars = 0;
    const paint = () => form.querySelectorAll(".star").forEach((s) => {
      s.textContent = Number(s.dataset.n) <= stars ? "★" : "☆";
    });
    form.querySelectorAll(".star").forEach((s) => {
      s.onclick = () => { stars = Number(s.dataset.n); paint(); };
    });
    form.querySelector(".review-send").onclick = async () => {
      if (!stars) return popup("Bahoni tanlang");
      try {
        await api("/reviews/", {
          method: "POST",
          body: JSON.stringify({
            request: callId, stars,
            comment: form.querySelector(".review-text").value,
          }),
        });
        popup("Rahmat! Izoh qoldirildi ✅");
        loadMyRequests();
      } catch (e) { popup("Xatolik: " + e.message); }
    };
    li.appendChild(form);
  }

  // --- Bildirishnomalar (o'qilmaganlar belgisi) ---
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

  // --- Tab almashish ---
  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.tab === name)
    );
    document.getElementById("tab-search").hidden = name !== "search";
    document.getElementById("tab-requests").hidden = name !== "requests";
    if (name === "requests") { loadMyRequests(); markRequestsRead(); }
  }

  async function markRequestsRead() {
    try { await api("/notifications/read/", { method: "POST" }); } catch (e) {}
    refreshBadge();
  }

  function showList() {
    detailView.hidden = true;
    listView.hidden = false;
  }

  // --- Geolokatsiya (masofa uchun) ---
  function requestGeo() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      coords.lat = pos.coords.latitude;
      coords.lng = pos.coords.longitude;
    });
  }

  // --- Ishga tushirish ---
  async function init() {
    if (tg) { tg.ready(); tg.expand(); }
    try {
      await authenticate();
      await loadSpecs();
      requestGeo();
      await search();
      statusEl.hidden = true;
      listView.hidden = false;

      document.getElementById("type-filter").onchange = search;
      document.getElementById("sort").onchange = search;
      document.getElementById("back-btn").onclick = showList;
      document.querySelectorAll(".tab").forEach((t) => {
        t.onclick = () => switchTab(t.dataset.tab);
      });
      document.getElementById("search-q").oninput = () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(search, 350);
      };
      document.getElementById("bell").onclick = openNotifications;
      refreshBadge();
      setInterval(refreshBadge, 20000);
    } catch (e) {
      if (e.message !== "no-telegram") setStatus("Xatolik: " + e.message);
    }
  }

  init();
})();
