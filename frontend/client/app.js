/* Mijoz Mini App — vet qidirish, chaqirish, so'rovlar va profil. */
(function () {
  "use strict";

  const API = "/api/v1";
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  const statusEl = document.getElementById("status");
  const appEl = document.getElementById("app");

  const MONTHS = ["Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];
  const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const TYPE_ICON = { home: "🏠", online: "💬", contact: "📞" };
  const ACTIVE_STATUSES = ["pending", "accepted", "on_way"];
  const SR_STATUS_CLASS = { open: "pending", assigned: "accepted", completed: "completed", cancelled: "cancelled", expired: "cancelled" };
  function statusLabel(status) { return I18N.t("st_" + status); }
  function srStatusLabel(status) { return I18N.t("sr_st_" + status); }

  let token = null;
  let me = null;
  let specs = [];
  let activeSpec = "";
  let coords = { lat: null, lng: null };
  let searchTimer = null;
  let currentTab = "home";
  let vetDetailFrom = "home";
  let myRequests = [];
  let myPets = [];
  let myTenders = [];
  let visitsSeg = "upcoming";
  let tenderSpecId = null;
  let tenderType = "home";
  let tenderPetId = null;
  let vetsView = "list";
  let currentVetsList = [];
  let yandexMap = null;
  let yandexUserMarker = null;
  let mapPlacemarks = [];
  const TASHKENT_CENTER = [41.311, 69.240];

  function setStatus(msg) { statusEl.textContent = msg; statusEl.hidden = false; }

  let reauthPromise = null;

  async function api(path, options = {}, _retried) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    if (token) headers["Authorization"] = "Bearer " + token;
    const url = path.startsWith("http") ? path : API + path;
    const res = await fetch(url, Object.assign({}, options, { headers }));
    // Access token ~2 soatda eskiradi — buni sezmasdan yangilab, so'rovni qaytadan yuboramiz
    // (aks holda foydalanuvchiga tushunarsiz "API 401" xatosi chiqib qolardi).
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

  // Xom API xatosini foydalanuvchiga tushunarli matnga aylantiradi.
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
  // so'rov (ikkilanган hayvon/chaqiruv/taklif) yuborilib ketmasligi uchun.
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

  function fmtDate(iso) {
    const d = new Date(iso);
    return { day: d.getDate(), month: MONTHS[d.getMonth()] };
  }

  function fmtTime(iso) {
    const d = new Date(iso);
    return d.getHours().toString().padStart(2, "0") + ":" + d.getMinutes().toString().padStart(2, "0");
  }

  function fmtReviewDate(iso) {
    const { day, month } = fmtDate(iso);
    return day + " " + month;
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
    me = data.user;
    I18N.setLang(me.language);
    I18N.applyStatic();
  }

  // --- Mutaxassisliklar ---
  async function loadSpecs() {
    specs = await api("/specializations/");
    renderHomeSpecs();
    renderSpecChips();
    renderTenderSpecChips();
  }

  function renderHomeSpecs() {
    const box = document.getElementById("home-specs");
    box.innerHTML = "";
    specs.forEach((s) => {
      const el = document.createElement("div");
      el.className = "spec-item";
      el.innerHTML = `<div class="circle">${s.icon || "🐾"}</div><span class="label">${s.name}</span>`;
      el.onclick = () => {
        activeSpec = s.slug;
        syncSpecChips();
        goTab("vets");
        search();
      };
      box.appendChild(el);
    });
  }

  function renderSpecChips() {
    const box = document.getElementById("spec-filter");
    box.innerHTML = "";
    const mkChip = (slug, label) => {
      const el = document.createElement("div");
      el.className = "chip" + (slug === activeSpec ? " active" : "");
      el.textContent = label;
      el.dataset.slug = slug;
      el.onclick = () => {
        activeSpec = activeSpec === slug ? "" : slug;
        syncSpecChips();
        search();
      };
      box.appendChild(el);
    };
    mkChip("", "Barchasi");
    specs.forEach((s) => mkChip(s.slug, (s.icon ? s.icon + " " : "") + s.name));
  }

  function syncSpecChips() {
    document.querySelectorAll("#spec-filter .chip").forEach((c) => {
      c.classList.toggle("active", c.dataset.slug === activeSpec);
    });
  }

  // --- Ochiq so'rov (tender) ---
  function renderTenderSpecChips() {
    const box = document.getElementById("tender-spec-filter");
    box.innerHTML = "";
    specs.forEach((s) => {
      const el = document.createElement("div");
      el.className = "chip" + (s.id === tenderSpecId ? " active" : "");
      el.textContent = (s.icon ? s.icon + " " : "") + s.name;
      el.onclick = () => {
        tenderSpecId = s.id;
        box.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        el.classList.add("active");
      };
      box.appendChild(el);
    });
    if (tenderSpecId == null && specs.length) tenderSpecId = specs[0].id;
    if (box.firstChild) box.firstChild.classList.add("active");
  }

  function renderTenderPetChips() {
    const box = document.getElementById("tender-pet-picker");
    // Hayvon o'chirilgan bo'lsa, unga eski tanlov ilashib qolmasligi kerak.
    if (tenderPetId && !myPets.some((p) => p.id === tenderPetId)) tenderPetId = null;
    box.innerHTML = myPets
      .map((p) => `<span class="chip${p.id === tenderPetId ? " active" : ""}" data-pet-id="${p.id}">🐾 ${p.name}</span>`)
      .join("");
    box.querySelectorAll(".chip").forEach((el) => {
      el.onclick = () => {
        const isActive = el.classList.contains("active");
        box.querySelectorAll(".chip").forEach((x) => x.classList.remove("active"));
        tenderPetId = isActive ? null : Number(el.dataset.petId);
        if (!isActive) el.classList.add("active");
      };
    });
  }

  // --- Viloyat -> tuman select'lari (ochiq so'rov formasi) ---
  function fillTenderRegionOptions() {
    const sel = document.getElementById("tender-city");
    const placeholder = sel.firstElementChild;
    sel.innerHTML = "";
    sel.appendChild(placeholder);
    (window.UZ_REGIONS || []).forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.name;
      opt.textContent = r.name;
      sel.appendChild(opt);
    });
  }

  function fillTenderDistrictOptions(regionName) {
    const districtSel = document.getElementById("tender-district");
    const placeholder = districtSel.firstElementChild;
    districtSel.innerHTML = "";
    districtSel.appendChild(placeholder);
    districtSel.disabled = !regionName;
    const region = (window.UZ_REGIONS || []).find((r) => r.name === regionName);
    if (!region) return;
    region.districts.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      districtSel.appendChild(opt);
    });
  }

  // Viloyat/tuman profildan olinadi (foydalanuvchi xohlasa o'zgartirishi mumkin).
  function prefillTenderRegion() {
    const city = me && me.city && (window.UZ_REGIONS || []).some((r) => r.name === me.city) ? me.city : "";
    document.getElementById("tender-city").value = city;
    fillTenderDistrictOptions(city);
    const districtSel = document.getElementById("tender-district");
    if (city && me.district && [...districtSel.options].some((o) => o.value === me.district)) districtSel.value = me.district;
  }

  async function createTender() {
    if (!tenderSpecId) return popup("Mutaxassislikni tanlang");
    const cityName = document.getElementById("tender-city").value;
    const payload = {
      specialization: tenderSpecId,
      type: tenderType,
      city: cityName,
      district: document.getElementById("tender-district").value,
      note: document.getElementById("tender-note").value.trim(),
    };
    // Aniq GPS bo'lmasa ham, tanlangan viloyat markazi koordinatasi yozib qo'yiladi —
    // shunda so'rov xaritada va masofa bo'yicha saralashda ishlatilishi mumkin.
    const region = (window.UZ_REGIONS || []).find((r) => r.name === cityName);
    if (coords.lat != null) { payload.lat = coords.lat; payload.lng = coords.lng; }
    else if (region && region.center) { payload.lat = region.center[0]; payload.lng = region.center[1]; }
    if (tenderPetId) payload.pet = tenderPetId;
    const budget = document.getElementById("tender-budget").value;
    if (budget) {
      if (Number(budget) < 0) return popup("Byudjet manfiy bo'lishi mumkin emas");
      payload.budget_hint = budget;
    }
    try {
      await api("/service-requests/", { method: "POST", body: JSON.stringify(payload) });
      prefillTenderRegion();
      document.getElementById("tender-note").value = "";
      document.getElementById("tender-budget").value = "";
      popup("Ochiq so'rov joylandi ✅");
      await loadMyTenders();
    } catch (e) { popup(friendlyError(e)); }
  }

  async function loadMyTenders() {
    const data = await api("/service-requests/");
    myTenders = data.results || data;
    const ul = document.getElementById("tender-list");
    ul.innerHTML = "";
    document.getElementById("tender-empty").hidden = myTenders.length > 0;
    myTenders.forEach((sr) => ul.appendChild(tenderCardEl(sr)));
  }

  function tenderCardEl(sr) {
    const li = document.createElement("li");
    li.className = "tender-card";
    const specTxt = sr.specialization_info ? (sr.specialization_info.icon ? sr.specialization_info.icon + " " : "") + sr.specialization_info.name : "";
    const canCancel = sr.status === "open" || sr.status === "assigned";
    const canReview = sr.status === "completed";
    const stCls = SR_STATUS_CLASS[sr.status] || "cancelled";
    const assignedTxt = sr.assigned_offer_info
      ? `<div class="ts">🩺 ${sr.assigned_offer_info.vet_info?.full_name || "Veterinar"} — ${Number(sr.assigned_offer_info.price).toLocaleString()} so'm</div>
         ${sr.assigned_offer_info.vet_info?.phone ? `<div class="ts"><a class="tel-link" href="tel:${sr.assigned_offer_info.vet_info.phone}">📞 ${sr.assigned_offer_info.vet_info.phone}</a></div>` : ""}`
      : "";
    li.innerHTML = `
      <div class="tender-top">
        <div>
          <div class="tt">${TYPE_ICON[sr.type] || ""} ${specTxt}${sr.city ? " · " + sr.city : ""}</div>
          <div class="ts">${sr.note || "Izohsiz"}${sr.budget_hint ? " · 💰 ~" + Number(sr.budget_hint).toLocaleString() + " so'm" : ""}</div>
          ${assignedTxt || `<div class="ts">${sr.offers_count} ta taklif</div>`}
        </div>
        <span class="st st-${stCls}">${srStatusLabel(sr.status)}</span>
      </div>
      <div id="offers-box-${sr.id}"></div>
      <div style="display:flex;gap:8px;margin-top:10px">
        ${sr.status === "open" && sr.offers_count > 0 ? `<button class="btn-secondary offers-btn" style="flex:1">${I18N.t("view_offers")}</button>` : ""}
        ${canCancel ? `<button class="btn-secondary cancel-btn" style="flex:1;color:var(--red)">${I18N.t("cancel")}</button>` : ""}
      </div>
      ${canReview ? `<button class="btn-secondary review-btn" style="margin-top:8px;width:100%">${sr.my_review ? I18N.t("review_edit") : I18N.t("review")}</button>` : ""}
      ${canReview && sr.assigned_offer_info ? `<button class="btn-secondary report-btn" style="margin-top:6px;width:100%;color:var(--red)">${I18N.t("report")}</button>` : ""}`;
    const offersBtn = li.querySelector(".offers-btn");
    if (offersBtn) offersBtn.onclick = () => toggleTenderOffers(sr, li, offersBtn);
    const cancelBtn = li.querySelector(".cancel-btn");
    if (cancelBtn) cancelBtn.onclick = () => confirmAction("Ochiq so'rovni bekor qilasizmi?", () => withBusy(cancelBtn, async () => {
      try {
        await api("/service-requests/" + sr.id + "/cancel/", { method: "POST" });
        popup("Bekor qilindi");
        await loadMyTenders();
      } catch (e) { popup(friendlyError(e)); }
    }));
    const reviewBtn = li.querySelector(".review-btn");
    if (reviewBtn) reviewBtn.onclick = () => openReviewForm({ service_request: sr.id }, li, loadMyTenders, sr.my_review);
    const reportBtn = li.querySelector(".report-btn");
    if (reportBtn) reportBtn.onclick = () => openReportForm(sr.assigned_offer_info?.vet_info?.user_id, { service_request: sr.id }, li);
    return li;
  }

  async function toggleTenderOffers(sr, li, btn) {
    const box = document.getElementById("offers-box-" + sr.id);
    if (box.dataset.open === "1") { box.innerHTML = ""; box.dataset.open = "0"; btn.textContent = I18N.t("view_offers"); return; }
    box.innerHTML = '<p class="muted" style="margin:8px 0">Yuklanmoqda...</p>';
    try {
      const offers = await api("/service-requests/" + sr.id + "/offers/");
      box.innerHTML = offers.length ? '<p class="muted" style="margin:0 0 6px;font-size:11.5px">Eng arzonidan qimmatiga saralangan</p>' : "";
      offers.forEach((o) => {
        const row = document.createElement("div");
        row.className = "offer-row";
        const canAccept = sr.status === "open" && o.status === "sent";
        row.innerHTML = `
          <div class="oi">
            <div class="on">${o.vet_info?.full_name || "Veterinar"} — ${Number(o.price).toLocaleString()} so'm</div>
            <div class="op">${o.vet_info?.clinic_name || ""}${o.message ? " · " + o.message : ""}</div>
          </div>
          ${canAccept ? `<button class="accept-btn">${I18N.t("accept")}</button>` : ""}`;
        const acceptBtn = row.querySelector(".accept-btn");
        if (acceptBtn) acceptBtn.onclick = () => withBusy(acceptBtn, async () => {
          try {
            await api("/offers/" + o.id + "/accept/", { method: "POST" });
            popup("Taklif qabul qilindi ✅");
            await loadMyTenders();
          } catch (e) { popup(friendlyError(e)); }
        });
        box.appendChild(row);
      });
      box.dataset.open = "1";
      btn.textContent = I18N.t("hide");
    } catch (e) { box.innerHTML = ""; }
  }

  // --- Qidiruv (Vets tab) ---
  function buildSearchParams() {
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
    if (me && me.city) params.set("city", me.city);
    return params;
  }

  let vetsNextUrl = null;

  let vetsTotalCount = 0;

  async function search() {
    const data = await api("/vets/?" + buildSearchParams().toString());
    const vets = data.results || data;
    vetsNextUrl = data.next || null;
    currentVetsList = vets;
    vetsTotalCount = data.count != null ? data.count : vets.length;
    document.getElementById("vets-count").textContent = data.count ? I18N.t("vets_count", { n: data.count }) : I18N.t("vets_count_empty");
    renderVetList(document.getElementById("vet-list"), vets);
    document.getElementById("empty").hidden = vets.length > 0;
    document.getElementById("vets-load-more").hidden = !vetsNextUrl;
    if (vetsView === "map") { renderMapMarkers(); updateMapBottomCard(); }
  }

  async function loadMoreVets() {
    if (!vetsNextUrl) return;
    const data = await api(vetsNextUrl);
    vetsNextUrl = data.next || null;
    const newVets = data.results || data;
    currentVetsList = currentVetsList.concat(newVets);
    renderVetList(document.getElementById("vet-list"), newVets, true);
    document.getElementById("vets-load-more").hidden = !vetsNextUrl;
    if (vetsView === "map") { renderMapMarkers(); updateMapBottomCard(); }
  }

  // --- Xarita (Yandex Maps) ---
  function goVetsView(view) {
    document.querySelectorAll("#screen-vets .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    setVetsView(view);
  }

  function setVetsView(view) {
    vetsView = view;
    document.getElementById("screen-vets").classList.toggle("map-mode", view === "map");
    document.getElementById("vets-list-view").hidden = view !== "list";
    document.getElementById("vets-map-view").hidden = view !== "map";
    if (view === "map" && !yandexMap) {
      const emptyEl = document.getElementById("map-empty");
      emptyEl.textContent = "Xarita yuklanmoqda...";
      emptyEl.hidden = false;
    }
    if (view === "map") {
      updateMapLocationPill();
      updateMapBottomCard();
      waitForYmaps(() => {
        initMap();
        setTimeout(() => {
          // Marker'lar konteyner haqiqiy o'lchamiga kelgandan KEYIN qo'shilishi kerak —
          // aks holda (map hali "hidden" ekrandan endigina ko'rinayotganda) noto'g'ri
          // piksel pozitsiyasida chizilib qoladi (masalan, tabbar ostida yashiringan).
          if (yandexMap) yandexMap.container.fitToViewport();
          renderMapMarkers();
        }, 50);
      });
    }
  }

  function updateMapLocationPill() {
    const mainEl = document.getElementById("map-loc-main");
    const subEl = document.getElementById("map-loc-sub");
    if (!mainEl) return;
    if (me && me.city) {
      mainEl.textContent = me.city;
      subEl.textContent = me.district || "";
    } else {
      mainEl.textContent = I18N.t("map_loc_unknown");
      subEl.textContent = "";
    }
  }

  function updateMapBottomCard() {
    const card = document.getElementById("map-bottom-card");
    const textEl = document.getElementById("map-bottom-text");
    if (!card) return;
    const n = vetsTotalCount;
    card.hidden = n === 0;
    textEl.innerHTML = n > 0 ? I18N.t("map_candidates", { n }) : I18N.t("map_candidates_empty");
  }

  // Ba'zi WebView'larda (mas. Telegram iOS) Yandex skripti sekin yuklanadi —
  // shu sabab darhol berilib ketish o'rniga bir necha marta qayta tekshiramiz.
  function waitForYmaps(cb, attempt) {
    attempt = attempt || 0;
    if (typeof ymaps !== "undefined") { ymaps.ready(cb); return; }
    if (attempt >= 20) {
      const emptyEl = document.getElementById("map-empty");
      emptyEl.textContent = "Xarita yuklanmadi. Internetni tekshirib, qaytadan urinib ko'ring.";
      emptyEl.hidden = false;
      return;
    }
    setTimeout(() => waitForYmaps(cb, attempt + 1), 300);
  }

  function initMap() {
    if (yandexMap) return;
    const center = coords.lat != null ? [coords.lat, coords.lng] : TASHKENT_CENTER;
    yandexMap = new ymaps.Map("vets-map", { center, zoom: 12, controls: [] });
    // zoomControl'ni pastki-o'ngga suramiz — top qismi bizning "joylashuv" pilli
    // va ikonka tugmalari bilan band, past qismi esa "N ta nomzod" kartochkasi bilan.
    yandexMap.controls.add("zoomControl", { position: { right: 10, bottom: 90 } });
  }

  function avatarMarkerOptions(photo, variant, fallback) {
    const layout = ymaps.templateLayoutFactory.createClass(
      '<div class="me-marker-wrap ' + variant + '">' +
        '<div class="me-marker-pulse"></div>' +
        '<div class="me-marker-dot">' + (photo ? '<img src="' + photo + '" alt="" />' : fallback) + '</div>' +
      '</div>'
    );
    return {
      iconLayout: layout,
      iconShape: { type: "Circle", coordinates: [0, 0], radius: 27 },
    };
  }

  function createVetPlacemark(v) {
    const specTxt = v.specializations.map((s) => s.icon || s.name).join(" ");
    const options = avatarMarkerOptions(v.photo, "vet-marker", v.specializations[0]?.icon || "👨‍⚕️");
    const placemark = new ymaps.Placemark([v.lat, v.lng], {
      balloonContentHeader: v.full_name || "Veterinar",
      balloonContentBody: `
        <div style="min-width:160px;font-family:inherit">
          <span style="color:#93887e;font-size:12px">${v.clinic_name || v.city || ""} ${specTxt}</span><br/>
          ⭐ ${Number(v.rating_avg).toFixed(1)}
          <button id="map-open-${v.id}" style="display:block;margin-top:6px;width:100%;padding:7px;border:none;border-radius:8px;background:#e8774a;color:#fff;font-weight:700;cursor:pointer">Ko'rish</button>
        </div>`,
    }, options);
    placemark.events.add("balloonopen", () => {
      const btn = document.getElementById("map-open-" + v.id);
      if (btn) btn.onclick = () => openVetDetail(v.id);
    });
    return placemark;
  }

  function renderMapMarkers() {
    if (!yandexMap) return;
    yandexMap.geoObjects.removeAll();
    yandexUserMarker = null;
    mapPlacemarks = [];
    const withCoords = currentVetsList.filter((v) => v.lat != null && v.lng != null);
    document.getElementById("map-empty").hidden = withCoords.length > 0;
    withCoords.forEach((v) => {
      const placemark = createVetPlacemark(v);
      yandexMap.geoObjects.add(placemark);
      mapPlacemarks.push({ placemark, v });
    });
    if (coords.lat != null) {
      yandexUserMarker = new ymaps.Placemark([coords.lat, coords.lng], {
        hintContent: "Siz shu yerdasiz",
      }, Object.assign(avatarMarkerOptions(me && me.photo, "", "🧑"), { zIndex: 1000 }));
      yandexMap.geoObjects.add(yandexUserMarker);
    }
  }

  async function loadHomeVets() {
    const params = new URLSearchParams();
    params.set("sort", coords.lat != null ? "distance" : "rating");
    if (coords.lat != null) { params.set("lat", coords.lat); params.set("lng", coords.lng); }
    if (me && me.city) params.set("city", me.city);
    const data = await api("/vets/?" + params.toString());
    const vets = (data.results || data).slice(0, 3);
    renderVetList(document.getElementById("home-vets"), vets);
  }

  function vetCardHtml(v) {
    const specsTxt = v.specializations.map((s) => s.icon || s.name).join(" ");
    const dist = v.distance_km != null ? `📍 ${v.distance_km} km` : "";
    const avatarInner = v.photo ? `<img src="${v.photo}" alt="" />` : (v.specializations[0]?.icon || "👨‍⚕️");
    return `
      <div class="avatar">${avatarInner}</div>
      <div class="info">
        <div class="name">${v.full_name || "Veterinar"}</div>
        <div class="sub">${v.clinic_name || v.city || ""} ${specsTxt}</div>
        <div class="badges">
          ${v.is_top ? '<span class="badge top">TOP</span>' : ""}
          ${v.is_verified ? '<span class="badge verified">✓ Tasdiqlangan</span>' : ""}
          ${v.is_available ? '<span class="badge avail">Bo\'sh</span>' : ""}
        </div>
      </div>
      <div class="right">
        <div class="rating">⭐ ${Number(v.rating_avg).toFixed(1)}</div>
        <div class="distance">${dist}</div>
      </div>`;
  }

  function renderVetList(ul, vets, append) {
    if (!append) ul.innerHTML = "";
    vets.forEach((v) => {
      const li = document.createElement("li");
      li.className = "vet-card";
      li.innerHTML = vetCardHtml(v);
      li.onclick = () => openVetDetail(v.id);
      ul.appendChild(li);
    });
  }

  // --- Vet sahifasi + chaqirish ---
  async function openVetDetail(id) {
    vetDetailFrom = currentTab;
    document.getElementById("detail-content").innerHTML = `<p class="center muted">${I18N.t("loading")}</p>`;
    showScreen("screen-vet-detail");
    const v = await api("/vets/" + id + "/");
    const services = (v.services || [])
      .map((s) => `<div class="svc-row selectable" data-id="${s.id}" data-title="${s.title}" data-price="${s.price}"><span>${s.title}</span><span>${Number(s.price).toLocaleString()} so'm</span></div>`)
      .join("");
    const specChips = v.specializations.map((s) => `<span class="pill">${s.icon ? s.icon + " " : ""}${s.name}</span>`).join("") || '<span class="muted">—</span>';

    const types = [];
    if (v.accepts_home_visit) types.push(["home", I18N.t("type_home_short")]);
    if (v.accepts_online) types.push(["online", I18N.t("type_online")]);
    types.push(["contact", I18N.t("type_contact")]);

    const avatarXlInner = v.photo ? `<img src="${v.photo}" alt="" />` : (v.specializations[0]?.icon || "👨‍⚕️");
    const petChips = myPets.map((p) => `<span class="chip" data-pet-id="${p.id}">🐾 ${p.name}</span>`).join("");
    document.getElementById("detail-content").innerHTML = `
      <div class="vd-banner">
        <div class="avatar-xl">${avatarXlInner}</div>
        <h2>${v.full_name || I18N.t("unnamed_vet")}</h2>
        <div class="spec">${v.specializations[0]?.name || v.clinic_name || ""}</div>
        ${v.is_verified ? `<div class="verified-row">${I18N.t("vd_verified")}</div>` : ""}
      </div>
      <div class="stat-row">
        <div class="stat-box"><div class="v">⭐ ${Number(v.rating_avg).toFixed(1)}</div><div class="l">${v.rating_count} ${I18N.t("vd_reviews_stat")}</div></div>
        <div class="stat-box"><div class="v">${v.experience_years}</div><div class="l">${I18N.t("vd_years_stat")}</div></div>
        <div class="stat-box"><div class="v">${v.distance_km != null ? v.distance_km + " km" : "—"}</div><div class="l">${I18N.t("vd_distance_stat")}</div></div>
      </div>
      ${v.bio ? `<div class="detail-card"><h3>${I18N.t("vd_about_title")}</h3><p style="margin:0;font-size:13.5px">${v.bio}</p></div>` : ""}
      <div class="detail-card"><h3>${I18N.t("vd_spec_title")}</h3><div class="pill-row">${specChips}</div></div>
      <div class="detail-card" id="services-card">
        <h3>${I18N.t("vd_services_title")}${v.min_price != null ? ` <span class="badge-verified">${I18N.t("vd_from_price", { n: Number(v.min_price).toLocaleString() })}</span>` : ""}</h3>
        ${(v.services || []).length ? `<p class="muted" style="margin:0 0 8px;font-size:12px">${I18N.t("vd_services_hint")}</p>` : `<p class="muted">${I18N.t("vd_services_empty")}</p>`}
        ${services}
      </div>
      <div class="detail-card"><h3>${I18N.t("vd_reviews_title")} (${v.rating_count})</h3><div id="reviews">...</div></div>
      <div class="detail-card">
        <h3>${I18N.t("vd_call_title")}</h3>
        <div class="type-opts" id="type-opts">
          ${types.map((t, i) => `<div class="type-opt${i === 0 ? " active" : ""}" data-type="${t[0]}">${t[1]}</div>`).join("")}
        </div>
        ${myPets.length ? `<p class="muted" style="margin:0 0 6px;font-size:12px">${I18N.t("vd_pet_title")}</p><div class="chips" id="call-pet-picker" style="padding:0 0 8px">${petChips}</div>` : ""}
        <input type="text" id="call-address" placeholder="Manzil (ko'cha, uy) — GPS bo'lmasa ham yordam beradi" data-i18n-ph="vd_address_placeholder" style="margin-bottom:8px" ${types[0][0] !== "home" ? "hidden" : ""} />
        <label class="muted" style="font-size:12px;display:block;margin-bottom:4px">${I18N.t("vd_scheduled_label")}</label>
        <input type="datetime-local" id="call-scheduled" style="width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:14px;margin-bottom:8px" />
        <textarea id="call-note" rows="2" placeholder="Muammoni qisqacha yozing..." data-i18n-ph="vd_note_placeholder"></textarea>
      </div>
      <button class="btn-primary" id="call-btn">${I18N.t("vd_send")}</button>`;
    I18N.applyStatic();

    let chosenType = types[0][0];
    const addressInput = document.getElementById("call-address");
    document.querySelectorAll("#type-opts .type-opt").forEach((el) => {
      el.onclick = () => {
        document.querySelectorAll("#type-opts .type-opt").forEach((x) => x.classList.remove("active"));
        el.classList.add("active");
        chosenType = el.dataset.type;
        addressInput.hidden = chosenType !== "home";
      };
    });

    let chosenPetId = null;
    document.querySelectorAll("#call-pet-picker .chip").forEach((el) => {
      el.onclick = () => {
        const isActive = el.classList.contains("active");
        document.querySelectorAll("#call-pet-picker .chip").forEach((x) => x.classList.remove("active"));
        chosenPetId = isActive ? null : Number(el.dataset.petId);
        if (!isActive) el.classList.add("active");
      };
    });

    let chosenService = null;
    document.querySelectorAll("#services-card .svc-row.selectable").forEach((el) => {
      el.onclick = () => {
        const isActive = el.classList.contains("active");
        document.querySelectorAll("#services-card .svc-row.selectable").forEach((x) => x.classList.remove("active"));
        if (isActive) { chosenService = null; return; }
        el.classList.add("active");
        chosenService = { title: el.dataset.title, price: el.dataset.price };
      };
    });

    const callBtn = document.getElementById("call-btn");
    callBtn.onclick = () => withBusy(callBtn, async () => {
      const noteText = document.getElementById("call-note").value.trim();
      const payload = {
        vet: v.id,
        type: chosenType,
        note: chosenService
          ? `Xizmat: ${chosenService.title} (${Number(chosenService.price).toLocaleString()} so'm)${noteText ? "\n" + noteText : ""}`
          : noteText,
      };
      if (chosenPetId) payload.pet = chosenPetId;
      const scheduledVal = document.getElementById("call-scheduled").value;
      if (scheduledVal) payload.scheduled_at = new Date(scheduledVal).toISOString();
      if (chosenType === "home") {
        if (coords.lat != null) {
          payload.lat = coords.lat;
          payload.lng = coords.lng;
        }
        const address = addressInput.value.trim();
        if (address) payload.address = address;
      }
      try {
        await api("/requests/", { method: "POST", body: JSON.stringify(payload) });
        popup("So'rov yuborildi ✅");
        await loadMyRequests();
        showScreen("screen-visits");
        goTab("visits");
      } catch (e) {
        popup(friendlyError(e));
      }
    });

    loadReviews(v.id);
  }

  async function loadReviews(vetId) {
    const box = document.getElementById("reviews");
    try {
      const data = await api("/vets/" + vetId + "/reviews/");
      const reviews = data.results || data;
      if (!reviews.length) {
        box.innerHTML = `<p class="muted">${I18N.t("vd_reviews_empty")}</p>`;
        return;
      }
      box.innerHTML = reviews
        .map((r) => `
          <div class="review">
            <div class="review-head">${"⭐".repeat(r.stars)} <span class="muted">${r.client_name}</span> <span class="muted" style="font-size:11px">· ${fmtReviewDate(r.created_at)}</span></div>
            ${r.comment ? `<div class="review-body">${r.comment}</div>` : ""}
          </div>`)
        .join("") + (data.next ? `<button class="btn-secondary" id="reviews-more" style="width:100%;margin-top:8px">${I18N.t("load_more")}</button>` : "");
      const moreBtn = document.getElementById("reviews-more");
      if (moreBtn) moreBtn.onclick = () => withBusy(moreBtn, () => loadMoreReviews(data.next, box));
    } catch (e) {
      box.innerHTML = "";
    }
  }

  async function loadMoreReviews(url, box) {
    try {
      const data = await api(url);
      const reviews = data.results || data;
      const oldBtn = document.getElementById("reviews-more");
      if (oldBtn) oldBtn.remove();
      box.insertAdjacentHTML("beforeend", reviews
        .map((r) => `
          <div class="review">
            <div class="review-head">${"⭐".repeat(r.stars)} <span class="muted">${r.client_name}</span> <span class="muted" style="font-size:11px">· ${fmtReviewDate(r.created_at)}</span></div>
            ${r.comment ? `<div class="review-body">${r.comment}</div>` : ""}
          </div>`)
        .join(""));
      if (data.next) {
        box.insertAdjacentHTML("beforeend", `<button class="btn-secondary" id="reviews-more" style="width:100%;margin-top:8px">${I18N.t("load_more")}</button>`);
        document.getElementById("reviews-more").onclick = () => withBusy(document.getElementById("reviews-more"), () => loadMoreReviews(data.next, box));
      }
    } catch (e) { popup(friendlyError(e)); }
  }

  // --- So'rovlarim (Visits tab + Home active card) ---
  async function loadMyRequests() {
    // Profil/Bosh sahifadagi jami hisoblagichlar to'g'ri chiqishi uchun
    // barcha sahifalar yig'ib olinadi (ro'yxat odatda kichik bo'ladi).
    let items = [];
    let url = "/requests/?role=client";
    while (url) {
      const data = await api(url);
      items = items.concat(data.results || data);
      url = data.next || null;
    }
    myRequests = items;
    renderHomeActive();
    renderVisits();
    renderProfileStats();
  }

  function renderHomeActive() {
    const wrap = document.getElementById("home-active-wrap");
    const active = myRequests.find((r) => ACTIVE_STATUSES.includes(r.status));
    if (!active) { wrap.hidden = true; return; }
    wrap.hidden = false;
    const box = document.getElementById("home-active");
    box.innerHTML = `
      <div class="dbox">${TYPE_ICON[active.type] || "📋"}</div>
      <div class="info">
        <div class="t">${active.vet_info?.full_name || "Veterinar"}</div>
        <div class="s"><span class="st st-${active.status}">${statusLabel(active.status)}</span> · ${active.vet_info?.clinic_name || ""}</div>
        ${active.vet_info?.phone ? `<div class="s"><a class="tel-link" href="tel:${active.vet_info.phone}" onclick="event.stopPropagation()">📞 ${active.vet_info.phone}</a></div>` : ""}
      </div>`;
    box.onclick = () => { goTab("visits"); };
  }

  function renderVisits() {
    const isUpcoming = visitsSeg === "upcoming";
    const items = myRequests.filter((r) => ACTIVE_STATUSES.includes(r.status) === isUpcoming);
    const ul = document.getElementById("visits-list");
    ul.innerHTML = "";
    document.getElementById("visits-empty").hidden = items.length > 0;
    items.forEach((r) => {
      const { day, month } = fmtDate(r.created_at);
      const li = document.createElement("li");
      li.className = "visit-card";
      const canReview = r.status === "completed";
      const canCancel = ACTIVE_STATUSES.includes(r.status);
      const canReport = ["completed", "rejected", "cancelled"].includes(r.status);
      li.innerHTML = `
        <div class="visit-top">
          <div class="visit-date"><div class="d">${day}</div><div class="m">${month}</div></div>
          <div class="visit-info">
            <div class="t">${TYPE_ICON[r.type] || ""} ${r.vet_info?.full_name || "Veterinar"}</div>
            <div class="s">${r.note || r.vet_info?.clinic_name || ""}</div>
            ${r.vet_info?.phone ? `<div class="s"><a class="tel-link" href="tel:${r.vet_info.phone}">📞 ${r.vet_info.phone}</a></div>` : ""}
            <div class="time">${fmtTime(r.created_at)} ${I18N.t("sent_ago")}</div>
          </div>
          <span class="st st-${r.status}">${statusLabel(r.status)}</span>
        </div>
        ${canReview ? `<button class="btn-secondary review-btn" style="margin-top:10px;width:100%">${r.my_review ? I18N.t("review_edit") : I18N.t("review")}</button>` : ""}
        ${canCancel ? `<button class="btn-secondary cancel-btn" style="margin-top:10px;width:100%;color:var(--red)">${I18N.t("cancel")}</button>` : ""}
        ${canReport ? `<button class="btn-secondary report-btn" style="margin-top:6px;width:100%;color:var(--red)">${I18N.t("report")}</button>` : ""}`;
      const btn = li.querySelector(".review-btn");
      if (btn) btn.onclick = () => openReviewForm({ request: r.id }, li, loadMyRequests, r.my_review);
      const reportBtn = li.querySelector(".report-btn");
      if (reportBtn) reportBtn.onclick = () => openReportForm(r.vet_info?.user_id, { call_request: r.id }, li);
      const cancelBtn = li.querySelector(".cancel-btn");
      if (cancelBtn) cancelBtn.onclick = () => confirmAction("So'rovni bekor qilasizmi?", () => withBusy(cancelBtn, async () => {
        try {
          await api("/requests/" + r.id + "/cancel/", { method: "POST" });
          popup("So'rov bekor qilindi");
          await loadMyRequests();
        } catch (e) { popup(friendlyError(e)); }
      }));
      ul.appendChild(li);
    });
  }

  // source: { request: id } chaqiruv uchun, { service_request: id } tender uchun.
  // existingReview: {id, stars, comment} bo'lsa — tahrirlash rejimi (PATCH + o'chirish tugmasi).
  function openReviewForm(source, li, onSaved, existingReview) {
    if (li.querySelector(".review-form")) return;
    const form = document.createElement("div");
    form.className = "review-form";
    form.innerHTML = `
      <div class="stars-pick" id="stars-pick">
        ${[1, 2, 3, 4, 5].map((n) => `<span class="star" data-n="${n}">☆</span>`).join("")}
      </div>
      <textarea class="review-text" rows="2" placeholder="Izoh (ixtiyoriy)">${existingReview ? existingReview.comment || "" : ""}</textarea>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn-primary review-send" style="flex:1">${I18N.t("save")}</button>
        ${existingReview ? `<button class="btn-secondary review-delete" style="color:var(--red)">${I18N.t("delete")}</button>` : ""}
      </div>`;
    let stars = existingReview ? existingReview.stars : 0;
    const paint = () => form.querySelectorAll(".star").forEach((s) => {
      s.textContent = Number(s.dataset.n) <= stars ? "★" : "☆";
    });
    paint();
    form.querySelectorAll(".star").forEach((s) => {
      s.onclick = () => { stars = Number(s.dataset.n); paint(); };
    });
    const sendBtn = form.querySelector(".review-send");
    sendBtn.onclick = () => withBusy(sendBtn, async () => {
      if (!stars) return popup("Bahoni tanlang");
      try {
        const body = JSON.stringify(existingReview
          ? { stars, comment: form.querySelector(".review-text").value }
          : Object.assign({ stars, comment: form.querySelector(".review-text").value }, source));
        await api(existingReview ? "/reviews/" + existingReview.id + "/" : "/reviews/", {
          method: existingReview ? "PATCH" : "POST",
          body,
        });
        popup("Rahmat! Izoh saqlandi ✅");
        await onSaved();
      } catch (e) { popup(friendlyError(e)); }
    });
    const deleteBtn = form.querySelector(".review-delete");
    if (deleteBtn) deleteBtn.onclick = () => confirmAction("Izohni o'chirasizmi?", () => withBusy(deleteBtn, async () => {
      try {
        await api("/reviews/" + existingReview.id + "/", { method: "DELETE" });
        popup("Izoh o'chirildi");
        await onSaved();
      } catch (e) { popup(friendlyError(e)); }
    }));
    li.appendChild(form);
  }

  const REPORT_REASONS = ["no_show", "rude", "fraud", "quality", "other"];

  // reportedUserId: shikoyat qilinayotgan foydalanuvchining User.id'si.
  // source: { call_request: id } yoki { service_request: id } (ixtiyoriy).
  function openReportForm(reportedUserId, source, li) {
    if (li.querySelector(".report-form")) return;
    const form = document.createElement("div");
    form.className = "report-form review-form";
    form.innerHTML = `
      <p class="muted" style="margin:0 0 6px;font-size:12px">${I18N.t("report_reason_title")}</p>
      <select class="report-reason" style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:13px">
        ${REPORT_REASONS.map((r) => `<option value="${r}">${I18N.t("report_reason_" + r)}</option>`).join("")}
      </select>
      <textarea class="review-text" rows="2" placeholder="${I18N.t("report_comment_ph")}" style="margin-top:8px"></textarea>
      <button class="btn-secondary report-send" style="width:100%;margin-top:8px;color:var(--red)">${I18N.t("report_send")}</button>`;
    const sendBtn = form.querySelector(".report-send");
    sendBtn.onclick = () => confirmAction(I18N.t("report_confirm"), () => withBusy(sendBtn, async () => {
      try {
        await api("/reports/", {
          method: "POST",
          body: JSON.stringify(Object.assign({
            reported_user: reportedUserId,
            reason: form.querySelector(".report-reason").value,
            comment: form.querySelector(".review-text").value,
          }, source)),
        });
        popup(I18N.t("report_sent"));
        form.remove();
      } catch (e) { popup(friendlyError(e)); }
    }));
    li.appendChild(form);
  }

  // --- Profil ---
  async function loadProfile() {
    me = await api("/auth/me/");
    renderProfile();
  }

  function renderProfile() {
    const name = [me.first_name, me.last_name].filter(Boolean).join(" ") || me.username || "Foydalanuvchi";
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
    fillProfileRegionOptions(me.city);
    document.getElementById("profile-city").value = me.city || "";
    fillProfileDistrictOptions(me.city, me.district);
    document.getElementById("profile-geo-info").textContent = me.lat != null
      ? `✅ ${me.lat.toFixed(3)}, ${me.lng.toFixed(3)}`
      : "";
  }

  // --- Mijoz "uy joylashuvi" (viloyat -> tuman, GPS) ---
  function fillProfileRegionOptions(currentCity) {
    const sel = document.getElementById("profile-city");
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

  function fillProfileDistrictOptions(regionName, selectedDistrict) {
    const districtSel = document.getElementById("profile-district");
    const placeholder = districtSel.firstElementChild;
    districtSel.innerHTML = "";
    districtSel.appendChild(placeholder);
    districtSel.disabled = !regionName;
    const region = (window.UZ_REGIONS || []).find((r) => r.name === regionName);
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

  // Viloyat/tuman tanlansa — aniq GPS bo'lmasa ham, kamida shahar markazi
  // koordinatasi bilan "yaqin atrofdagi veterinarlar" ishlashi uchun darhol saqlanadi.
  async function saveProfileLocation() {
    const cityName = document.getElementById("profile-city").value;
    const district = document.getElementById("profile-district").value;
    const region = (window.UZ_REGIONS || []).find((r) => r.name === cityName);
    const payload = { city: cityName, district };
    if (region && region.center) {
      payload.lat = region.center[0];
      payload.lng = region.center[1];
    }
    try {
      me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify(payload) });
      if (me.lat != null) { coords.lat = me.lat; coords.lng = me.lng; }
      document.getElementById("profile-geo-info").textContent = me.lat != null
        ? `✅ ${me.lat.toFixed(3)}, ${me.lng.toFixed(3)}`
        : "";
      popup(I18N.t("geo_saved"));
      loadHomeVets();
    } catch (e) { popup(friendlyError(e)); }
  }

  function getCurrentPositionAsync(options) {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) return reject(new Error("no-geolocation"));
      navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
  }

  async function captureProfileGeo() {
    try {
      const pos = await getCurrentPositionAsync({ timeout: 10000 });
      coords.lat = pos.coords.latitude;
      coords.lng = pos.coords.longitude;
      me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ lat: coords.lat, lng: coords.lng }) });
      document.getElementById("profile-geo-info").textContent = `✅ ${coords.lat.toFixed(3)}, ${coords.lng.toFixed(3)}`;
      popup(I18N.t("geo_saved"));
      loadHomeVets();
    } catch (e) {
      popup(e.message && e.message !== "no-geolocation" ? friendlyError(e) : I18N.t("geo_denied"));
    }
  }

  function renderProfileStats() {
    document.getElementById("stat-pets").textContent = myPets.length;
    document.getElementById("stat-active").textContent = myRequests.filter((r) => ACTIVE_STATUSES.includes(r.status)).length;
    document.getElementById("stat-total").textContent = myRequests.length;
  }

  async function loadPets() {
    const data = await api("/pets/");
    myPets = data.results || data;
    renderPets();
    renderProfileStats();
    renderTenderPetChips();
  }

  function renderPets() {
    const box = document.getElementById("pets-list");
    box.innerHTML = "";
    document.getElementById("pets-empty").hidden = myPets.length > 0;
    myPets.forEach((p) => {
      const row = document.createElement("div");
      row.className = "pet-row";
      const sub = [p.breed, p.age ? p.age + " yosh" : null].filter(Boolean).join(" · ") || p.species;
      row.innerHTML = `
        <div class="pe" title="Rasm qo'yish uchun bosing">${p.photo ? `<img src="${p.photo}" alt="" />` : "🐾"}</div>
        <input type="file" class="pet-photo-input" accept="image/png,image/jpeg,image/webp" style="display:none" />
        <div style="flex:1;min-width:0"><div class="pn">${p.name}</div><div class="ps">${sub}</div></div>
        <button class="edit" style="background:none;border:none;font-size:15px;cursor:pointer;padding:4px">✎</button>
        <button class="del" style="background:none;border:none;color:var(--red);font-size:17px;cursor:pointer;padding:4px">🗑</button>`;
      const delBtn = row.querySelector(".del");
      delBtn.onclick = () => confirmAction(`"${p.name}"ni o'chirasizmi?`, () => withBusy(delBtn, async () => {
        try {
          await api("/pets/" + p.id + "/", { method: "DELETE" });
          await loadPets();
        } catch (e) { popup(friendlyError(e)); }
      }));
      const photoInput = row.querySelector(".pet-photo-input");
      row.querySelector(".pe").onclick = () => photoInput.click();
      photoInput.onchange = () => {
        if (photoInput.files[0]) uploadPetPhoto(p.id, photoInput.files[0], row);
        photoInput.value = "";
      };
      row.querySelector(".edit").onclick = () => togglePetEditForm(p, row);
      box.appendChild(row);
    });
  }

  function togglePetEditForm(p, row) {
    const existing = row.querySelector(".pet-edit-form");
    if (existing) { existing.remove(); return; }
    const form = document.createElement("div");
    form.className = "pet-edit-form";
    form.innerHTML = `
      <div class="row2">
        <input type="text" class="f-breed" placeholder="Zoti (ixtiyoriy)" value="${p.breed || ""}" />
        <input type="number" class="f-age" placeholder="Yoshi" min="0" max="60" value="${p.age || ""}" />
      </div>
      <select class="f-gender">
        <option value="unknown"${p.gender === "unknown" ? " selected" : ""}>Jinsi: Noma'lum</option>
        <option value="male"${p.gender === "male" ? " selected" : ""}>Jinsi: Erkak</option>
        <option value="female"${p.gender === "female" ? " selected" : ""}>Jinsi: Urg'ochi</option>
      </select>
      <textarea class="f-notes" rows="2" placeholder="Izoh (allergiya, xronik kasallik va h.k.)">${p.notes || ""}</textarea>
      <button class="btn-primary f-save">Saqlash</button>`;
    row.appendChild(form);
    const saveBtn = form.querySelector(".f-save");
    saveBtn.onclick = () => withBusy(saveBtn, async () => {
      try {
        await api("/pets/" + p.id + "/", {
          method: "PATCH",
          body: JSON.stringify({
            breed: form.querySelector(".f-breed").value.trim(),
            age: form.querySelector(".f-age").value || null,
            gender: form.querySelector(".f-gender").value,
            notes: form.querySelector(".f-notes").value.trim(),
          }),
        });
        popup("Saqlandi ✅");
        await loadPets();
      } catch (e) { popup(friendlyError(e)); }
    });
  }

  async function uploadPetPhoto(petId, file, row) {
    if (file.size > 5 * 1024 * 1024) return popup("Rasm hajmi 5MB dan oshmasligi kerak.");
    const previewUrl = URL.createObjectURL(file);
    row.querySelector(".pe").innerHTML = `<img src="${previewUrl}" alt="" />`;
    const formData = new FormData();
    formData.append("photo", file);
    const headers = {};
    if (token) headers["Authorization"] = "Bearer " + token;
    try {
      const res = await fetch(API + "/pets/" + petId + "/", { method: "PATCH", body: formData, headers });
      if (!res.ok) throw new Error("API " + res.status + ": " + (await res.text()));
      await loadPets();
    } catch (e) {
      popup(friendlyError(e));
      await loadPets();
    } finally {
      URL.revokeObjectURL(previewUrl);
    }
  }

  async function addPet() {
    const nameEl = document.getElementById("pet-name");
    const specEl = document.getElementById("pet-species");
    const name = nameEl.value.trim();
    const species = specEl.value.trim();
    if (!name || !species) return popup("Ism va turini kiriting");
    try {
      await api("/pets/", { method: "POST", body: JSON.stringify({ name, species }) });
      nameEl.value = "";
      specEl.value = "";
      await loadPets();
    } catch (e) { popup(friendlyError(e)); }
  }

  // Ism/familiya/telefonni saqlaydi — profil tahrir formasi va birinchi
  // kirishdagi "profilni to'ldiring" oynasi ikkalasi ham shuni chaqiradi.
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
      renderProfile();
      popup("Saqlandi ✅");
      return true;
    } catch (e) {
      popup(friendlyError(e));
      return false;
    }
  }

  async function saveProfile() {
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
  function maybeShowIdentityOnboarding() {
    if (me.phone) return;
    const modal = document.getElementById("identity-modal");
    document.getElementById("onb-first").value = me.first_name || "";
    document.getElementById("onb-last").value = me.last_name || "";
    document.getElementById("onb-phone").value = "";
    modal.hidden = false;
  }

  // --- Profil rasmi ---
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
      renderProfile();
      popup("Rasm yangilandi ✅");
    } catch (e) {
      renderProfile();
      popup(friendlyError(e));
    } finally {
      URL.revokeObjectURL(previewUrl);
    }
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

  // Foydalanuvchi hozir "Baholash"/"Shikoyat" kabi ochiq formaga yozayotgan bo'lsa,
  // fon yangilanishi (pull-to-refresh, visibilitychange) ro'yxatni qayta qurib,
  // yozilgan matnni yo'qotib yubormasligi kerak.
  function hasOpenFormFocus() {
    const active = document.activeElement;
    if (!active || !["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) return false;
    return !!active.closest(".review-form, .report-form, .offer-form, .pet-edit-form");
  }

  function refreshCurrentTab() {
    const tasks = [refreshBadge()];
    if (hasOpenFormFocus()) return Promise.all(tasks);
    if (currentTab === "visits" || currentTab === "home") tasks.push(loadMyRequests());
    if (currentTab === "tender") tasks.push(loadMyTenders());
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
    offer_accepted: "✅", offer_declined: "❌", service_completed: "✅", review_new: "⭐",
  };
  const NOTIF_TARGET_TAB = {
    call_new: "visits", call_status: "visits",
    tender_new: "tender", offer_new: "tender", offer_accepted: "tender", offer_declined: "tender",
    service_completed: "tender", review_new: "visits",
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

  async function openNotifications() {
    showScreen("screen-notifications");
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

  // --- Navigatsiya ---
  const STACKED_SCREENS = ["screen-vet-detail", "screen-tender", "screen-notifications"];

  function showScreen(id) {
    document.querySelectorAll(".screen").forEach((s) => { s.hidden = s.id !== id; });
    document.querySelector(".tabbar").hidden = STACKED_SCREENS.includes(id);
  }

  function goTab(name) {
    currentTab = name;
    document.querySelectorAll(".tab-btn").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    showScreen("screen-" + name);
    if (name === "visits") { loadMyRequests(); }
    if (name === "profile") { loadProfile(); loadPets(); }
    if (name === "home") { loadMyRequests(); }
    if (name === "tender") { prefillTenderRegion(); loadMyTenders(); }
  }

  // Avval profilda saqlangan joylashuv bo'lsa, shuni darhol ishlatamiz (GPS
  // kutmasdan) — so'ng jonli GPS urinib ko'riladi va muvaffaqiyatli bo'lsa
  // profilga jimgina qayta saqlanadi. GPS rad etilsa/ishlamasa ham jim
  // qoladi — profildagi (yoki viloyat tanlangan) joylashuv zaxira bo'lib xizmat qiladi
  // (10-bo'lim: pilotda aniqlangan kamchilik — avval GPS muvaffaqiyatsiz bo'lsa
  // hech qanday zaxira yo'q edi, "yaqin atrofdagi veterinarlar" hech qachon ishlamasdi).
  function requestGeo() {
    if (me && me.lat != null) {
      coords.lat = me.lat;
      coords.lng = me.lng;
      loadHomeVets();
    }
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        coords.lat = pos.coords.latitude;
        coords.lng = pos.coords.longitude;
        loadHomeVets();
        if (yandexMap) { yandexMap.setCenter([coords.lat, coords.lng], 12); renderMapMarkers(); }
        try {
          me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ lat: coords.lat, lng: coords.lng }) });
        } catch (e) { /* jim — asosiy oqimga xalaqit bermasin */ }
      },
      () => { /* jim — profildagi joylashuv (bo'lsa) allaqachon zaxira sifatida ishlatildi */ },
      { timeout: 10000 },
    );
  }

  function setGreeting() {
    const now = new Date();
    document.getElementById("home-date").textContent = WEEKDAYS[now.getDay()] + ", " + now.getDate() + " " + MONTHS[now.getMonth()].toLowerCase();
    const hour = now.getHours();
    const part = hour < 12 ? I18N.t("greet_morning") : hour < 18 ? I18N.t("greet_day") : I18N.t("greet_evening");
    const name = me && me.first_name ? me.first_name : "";
    document.getElementById("home-greeting").textContent = `${part}, ${name} 👋`;
  }

  // --- Ishga tushirish ---
  async function init() {
    if (tg) { tg.ready(); tg.expand(); }
    try {
      await authenticate();
      await loadSpecs();
      setGreeting();
      requestGeo();
      await search();
      await loadHomeVets();
      await loadMyRequests();
      await loadPets();
      statusEl.hidden = true;
      appEl.hidden = false;
      goTab("home");
      maybeShowIdentityOnboarding();

      document.getElementById("type-filter").onchange = search;
      document.getElementById("sort").onchange = search;
      document.getElementById("vets-load-more").onclick = loadMoreVets;
      document.getElementById("back-btn").onclick = () => goTab(vetDetailFrom);
      document.getElementById("tender-back-btn").onclick = () => goTab("home");
      const tenderSendBtn = document.getElementById("tender-send-btn");
      tenderSendBtn.onclick = () => withBusy(tenderSendBtn, createTender);
      fillTenderRegionOptions();
      document.getElementById("tender-city").onchange = (e) => fillTenderDistrictOptions(e.target.value);
      document.querySelectorAll("#tender-type-opts .type-opt").forEach((el) => {
        el.onclick = () => {
          document.querySelectorAll("#tender-type-opts .type-opt").forEach((x) => x.classList.remove("active"));
          el.classList.add("active");
          tenderType = el.dataset.type;
        };
      });
      document.getElementById("bell").onclick = openNotifications;
      document.getElementById("notif-back-btn").onclick = () => goTab(currentTab);
      document.getElementById("search-q").oninput = () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(search, 350);
      };

      document.querySelectorAll(".tab-btn").forEach((t) => { t.onclick = () => goTab(t.dataset.tab); });
      document.querySelectorAll("[data-goto]").forEach((el) => { el.onclick = () => goTab(el.dataset.goto); });
      document.querySelectorAll("#screen-visits .seg-btn").forEach((btn) => {
        btn.onclick = () => {
          visitsSeg = btn.dataset.seg;
          document.querySelectorAll("#screen-visits .seg-btn").forEach((b) => b.classList.toggle("active", b === btn));
          renderVisits();
        };
      });
      document.querySelectorAll("#screen-vets .seg-btn").forEach((btn) => {
        btn.onclick = () => goVetsView(btn.dataset.view);
      });
      document.getElementById("map-list-btn").onclick = () => goVetsView("list");
      document.getElementById("map-search-btn").onclick = () => {
        goVetsView("list");
        setTimeout(() => document.getElementById("search-q").focus(), 50);
      };
      document.getElementById("map-bottom-view-btn").onclick = () => goVetsView("list");

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
      const editSaveBtn = document.getElementById("edit-save");
      editSaveBtn.onclick = () => withBusy(editSaveBtn, saveProfile);
      const onbSaveBtn = document.getElementById("onb-save");
      onbSaveBtn.onclick = () => withBusy(onbSaveBtn, async () => {
        const ok = await saveNamePhone(
          document.getElementById("onb-first").value,
          document.getElementById("onb-last").value,
          document.getElementById("onb-phone").value,
          { requirePhone: true },
        );
        if (ok) {
          document.getElementById("identity-modal").hidden = true;
          goTab("profile");
          const cam = document.getElementById("profile-avatar-cam");
          cam.classList.add("pulse");
          setTimeout(() => cam.classList.remove("pulse"), 2600);
        }
      });
      document.getElementById("onb-skip").onclick = () => { document.getElementById("identity-modal").hidden = true; };
      document.getElementById("profile-city").onchange = (e) => {
        fillProfileDistrictOptions(e.target.value, null);
        saveProfileLocation();
      };
      document.getElementById("profile-district").onchange = () => saveProfileLocation();
      const profileGeoBtn = document.getElementById("profile-geo-btn");
      profileGeoBtn.onclick = () => withBusy(profileGeoBtn, captureProfileGeo);
      const petAddBtn = document.getElementById("pet-add");
      petAddBtn.onclick = () => withBusy(petAddBtn, addPet);
      document.getElementById("help-row").onclick = openSupport;
      document.getElementById("privacy-row").onclick = () => { document.getElementById("privacy-modal").hidden = false; };
      document.getElementById("oferta-row").onclick = () => {
        const url = location.origin + "/legal/oferta-mijoz.html";
        if (tg && tg.openLink) tg.openLink(url); else window.open(url, "_blank");
      };
      document.getElementById("privacy-close").onclick = () => { document.getElementById("privacy-modal").hidden = true; };
      document.getElementById("lang-row").onclick = () => withBusy(document.getElementById("lang-row"), async () => {
        const newLang = me.language === "ru" ? "uz" : "ru";
        try {
          me = await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ language: newLang }) });
          I18N.setLang(me.language);
          I18N.applyStatic();
          renderProfile();
          popup(newLang === "ru" ? "Til: Русский" : "Til: O'zbekcha");
        } catch (e) { popup(friendlyError(e)); }
      });

      refreshBadge();
      setInterval(refreshBadge, 20000);
      setupPullToRefresh(refreshCurrentTab);
      // Foydalanuvchi Telegram'dan qaytib kelganda (chat ro'yxatiga chiqib, orqaga
      // kirganda) joriy ekran ma'lumotini yangilaydi — chin real-vaqt o'rniga.
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
