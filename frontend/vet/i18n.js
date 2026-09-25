/* Veterinar Mini App — til tizimi (uz/ru). Asosiy matnlar tarjima qilingan:
   navigatsiya, sarlavhalar, umumiy tugmalar, holat yorliqlari, bo'sh ekranlar. */
(function () {
  "use strict";

  const DICT = {
    // --- Bottom nav ---
    nav_home: { uz: "Bosh sahifa", ru: "Главная" },
    nav_calls: { uz: "Chaqiruvlar", ru: "Вызовы" },
    nav_tender: { uz: "Tender", ru: "Тендер" },
    nav_profile: { uz: "Profil", ru: "Профиль" },

    // --- Home ---
    hero_tag: { uz: "VET KABINETI", ru: "КАБИНЕТ ВРАЧА" },
    hero_title: { uz: "Sizning mehringiz,<br />ularning tinchligi.", ru: "Ваша забота —<br />их спокойствие." },
    hero_sub: { uz: "Chaqiruvlarni boshqaring, tenderlarga taklif bering va mijozlarga ochiq bo'ling.", ru: "Управляйте вызовами, отвечайте на тендеры и будьте на связи с клиентами." },
    onboard_title: { uz: "👋 Profilni to'ldiring", ru: "👋 Заполните профиль" },
    onboard_sub: { uz: "Mijozlar sizni topishi uchun quyidagilarni yakunlang:", ru: "Чтобы клиенты нашли вас, завершите следующее:" },
    onboard_goto: { uz: "Profilga o'tish", ru: "Перейти в профиль" },
    onboard_spec: { uz: "Mutaxassislik tanlang", ru: "Выберите специализацию" },
    onboard_location: { uz: "Xaritada joylashuvni belgilang", ru: "Укажите местоположение на карте" },
    onboard_service: { uz: "Kamida bitta xizmat qo'shing", ru: "Добавьте хотя бы одну услугу" },
    onboard_bio: { uz: "O'zingiz haqingizda yozing (bio)", ru: "Напишите о себе (био)" },
    avail_title: { uz: "Ish qabul qilaman", ru: "Принимаю заказы" },
    avail_on: { uz: "Mijozlarga ko'rinasiz", ru: "Вы видны клиентам" },
    avail_off: { uz: "Yashirin — chaqiruv kelmaydi", ru: "Скрыто — вызовы не поступают" },
    stat_pending: { uz: "Yangi chaqiruv", ru: "Новые вызовы" },
    stat_tender: { uz: "Ochiq tender", ru: "Открытые тендеры" },
    stat_rating: { uz: "Reyting", ru: "Рейтинг" },
    quick_title: { uz: "Tezkor bo'limlar", ru: "Быстрые разделы" },
    qt_calls: { uz: "Chaqiruvlar", ru: "Вызовы" },
    qt_tender: { uz: "Tender", ru: "Тендер" },
    qt_edit_profile: { uz: "Profilni tahrirlash", ru: "Редактировать профиль" },
    recent_calls_title: { uz: "So'nggi chaqiruvlar", ru: "Последние вызовы" },
    link_all: { uz: "Barchasi", ru: "Все" },
    calls_empty: { uz: "Hozircha chaqiruv yo'q", ru: "Вызовов пока нет" },

    // --- Calls ---
    calls_eyebrow: { uz: "To'g'ridan chaqiruv", ru: "Прямой вызов" },
    calls_title: { uz: "Chaqiruvlar", ru: "Вызовы" },
    calls_search_ph: { uz: "🔍 Hayvon, izoh yoki manzil bo'yicha qidirish...", ru: "🔍 Поиск по питомцу, заметке или адресу..." },
    filter_all: { uz: "Barchasi", ru: "Все" },
    load_more: { uz: "Yana yuklash", ru: "Загрузить ещё" },

    // --- Tender ---
    tender_eyebrow: { uz: "Ochiq so'rovlar", ru: "Открытые заявки" },
    tender_title: { uz: "Tender lentasi", ru: "Лента тендеров" },
    won_title: { uz: "G'olib bo'lgan takliflarim", ru: "Мои выигранные предложения" },
    new_requests_title: { uz: "Yangi so'rovlar", ru: "Новые заявки" },
    tender_empty: { uz: "Mutaxassisligingizga mos so'rov yo'q", ru: "Заявок по вашей специализации нет" },
    complete: { uz: "✅ Yakunlash", ru: "✅ Завершить" },
    working: { uz: "Ishlanmoqda", ru: "В работе" },
    offer_price_ph: { uz: "Narxingiz (so'm)", ru: "Ваша цена (сум)" },
    price_agreed_ph: { uz: "Kelishilgan narx (so'm)", ru: "Согласованная цена (сум)" },
    price_saved: { uz: "Narx saqlandi ✅", ru: "Цена сохранена ✅" },
    price_enter_first: { uz: "Avval narxni kiriting", ru: "Сначала введите цену" },
    offer_send: { uz: "Taklif", ru: "Предложить" },

    // --- Notifications ---
    notif_title: { uz: "Bildirishnomalar", ru: "Уведомления" },
    notif_empty: { uz: "Bildirishnoma yo'q", ru: "Уведомлений нет" },

    // --- Profile ---
    profile_eyebrow: { uz: "Hisob", ru: "Аккаунт" },
    profile_title: { uz: "Profil", ru: "Профиль" },
    photo_hint: { uz: "Rasm qo'yish uchun bosing", ru: "Нажмите, чтобы добавить фото" },
    ph_first: { uz: "Ism", ru: "Имя" },
    ph_last: { uz: "Familiya", ru: "Фамилия" },
    save: { uz: "Saqlash", ru: "Сохранить" },
    identity_onboard_title: { uz: "Profilingizni to'ldiring", ru: "Заполните профиль" },
    identity_onboard_sub: { uz: "Mijozlar sizni topishi va bog'lanishi uchun ism, telefon va viloyatingizni kiriting", ru: "Укажите имя, телефон и область, чтобы клиенты могли найти вас и связаться" },
    identity_region_required: { uz: "Viloyat va tumanni tanlang — busiz mijozlar sizni ko'rmaydi", ru: "Выберите область и район — без них клиенты вас не увидят" },
    identity_onboard_skip: { uz: "Keyinroq", ru: "Позже" },
    identity_first_required: { uz: "Ismingizni kiriting", ru: "Введите имя" },
    save_all: { uz: "💾 Saqlash", ru: "💾 Сохранить" },
    avail_toggle_label: { uz: "Ish qabul qilaman (bo'sh)", ru: "Принимаю заказы (свободен)" },
    main_info_title: { uz: "Asosiy ma'lumotlar", ru: "Основная информация" },
    bio_label: { uz: "Bio (o'zingiz haqingizda)", ru: "Био (о себе)" },
    bio_ph: { uz: "Tajriba, yo'nalish...", ru: "Опыт, направление..." },
    clinic_label: { uz: "Klinika nomi", ru: "Название клиники" },
    clinic_ph: { uz: "Masalan: VetClinic", ru: "Например: VetClinic" },
    experience_label: { uz: "Tajriba (yil)", ru: "Опыт (лет)" },
    specializations_title: { uz: "Mutaxassisliklar", ru: "Специализации" },
    accepts_title: { uz: "Qabul qiladigan chaqiruvlar", ru: "Принимаемые типы вызовов" },
    accepts_home: { uz: "🏠 Uyga boraman", ru: "🏠 Выезжаю на дом" },
    accepts_online: { uz: "💬 Online konsultatsiya", ru: "💬 Онлайн-консультация" },
    location_title: { uz: "Joylashuv", ru: "Местоположение" },
    city_label: { uz: "Viloyat", ru: "Область" },
    district_label: { uz: "Tuman", ru: "Район" },
    select_region: { uz: "— Viloyatni tanlang —", ru: "— Выберите область —" },
    select_district: { uz: "— Avval viloyatni tanlang —", ru: "— Сначала выберите область —" },
    address_label: { uz: "Manzil", ru: "Адрес" },
    address_ph: { uz: "Ko'cha, uy", ru: "Улица, дом" },
    geocode_btn: { uz: "🔍 Manzil bo'yicha qidirish", ru: "🔍 Искать по адресу" },
    map_hint: { uz: "Yoki xaritada joylashuvni bosib/tortib belgilang", ru: "Или отметьте местоположение на карте" },
    geo_btn: { uz: "📍 Joriy joylashuvni olish (GPS)", ru: "📍 Определить местоположение (GPS)" },
    services_title: { uz: "Xizmatlar", ru: "Услуги" },
    service_name_ph: { uz: "Xizmat nomi", ru: "Название услуги" },
    price_ph: { uz: "Narx", ru: "Цена" },
    verified: { uz: "✓ Tasdiqlangan", ru: "✓ Подтверждён" },
    unverified: { uz: "Tasdiqlanmagan", ru: "Не подтверждён" },
    license_title: { uz: "Diplom / litsenziya", ru: "Диплом / лицензия" },
    license_hint: { uz: "Admin tasdiqlashi uchun diplom yoki litsenziya nusxasini yuklang.", ru: "Загрузите копию диплома или лицензии для подтверждения администратором." },
    license_uploaded: { uz: "✅ Fayl yuklangan", ru: "✅ Файл загружен" },
    license_not_uploaded: { uz: "Hali yuklanmagan", ru: "Пока не загружено" },
    license_upload_btn: { uz: "📎 Fayl yuklash", ru: "📎 Загрузить файл" },
    license_change_btn: { uz: "📎 Faylni almashtirish", ru: "📎 Заменить файл" },
    settings_title: { uz: "Sozlamalar", ru: "Настройки" },
    language_title: { uz: "Til", ru: "Язык" },
    help_title: { uz: "Yordam markazi", ru: "Центр помощи" },
    help_sub: { uz: "Savol yoki muammo bo'lsa", ru: "Если есть вопрос или проблема" },
    privacy_title: { uz: "Maxfiylik siyosati", ru: "Политика конфиденциальности" },
    privacy_sub: { uz: "Qanday ma'lumot yig'amiz", ru: "Какие данные мы собираем" },
    oferta_title: { uz: "Ommaviy oferta", ru: "Публичная оферта" },
    oferta_sub: { uz: "Xizmat ko'rsatish shartlari", ru: "Условия оказания услуг" },
    privacy_body: {
      uz: `
        <p><strong>Qanday ma'lumot yig'amiz:</strong> Telegram profilingizdagi ism, username va rasm; telefon raqamingiz; profilingizga kiritgan bio, tajriba, xizmat va narxlar; xaritada belgilagan joylashuv; tasdiqlash uchun yuklagan diplom/litsenziya fayli.</p>
        <p><strong>Nima uchun:</strong> Sizni mos mijozlar bilan bog'lash, chaqiruv va tenderlarni yetkazish, profilingizni ko'rsatish, hisobingizni tasdiqlash uchun.</p>
        <p><strong>Kim ko'radi:</strong> Profilingiz (rasm, tajriba, narxlar, izohlar) barcha mijozlarga ochiq. Diplom/litsenziya faylini faqat administrator ko'radi. Chaqiruv yuborgan yoki tenderingizda g'olib bo'lgan mijozning ismi sizga ko'rinadi.</p>
        <p><strong>Uchinchi tomonlarga berish:</strong> Ma'lumotlaringiz sotilmaydi va reklama maqsadida berilmaydi.</p>
        <p><strong>Saqlash muddati:</strong> Hisobingiz faol ekan saqlanadi. O'chirishni so'rasangiz, Yordam markazi orqali murojaat qiling.</p>
        <p class="muted" style="font-size:12px;margin-top:14px">Bu qisqa va tushunarli tavsif, to'liq yuridik oferta emas.</p>
      `,
      ru: `
        <p><strong>Какие данные собираем:</strong> имя, username и фото из вашего профиля Telegram; номер телефона; введённые вами био, опыт, услуги и цены; местоположение на карте; загруженный файл диплома/лицензии.</p>
        <p><strong>Для чего:</strong> чтобы связать вас с подходящими клиентами, доставить заявки и тендеры, показать ваш профиль, подтвердить ваш аккаунт.</p>
        <p><strong>Кто видит:</strong> ваш профиль (фото, опыт, цены, отзывы) открыт для всех клиентов. Файл диплома/лицензии видит только администратор. Имя клиента, отправившего заявку или выбравшего вас в тендере, видно вам.</p>
        <p><strong>Передача третьим лицам:</strong> данные не продаются и не передаются для рекламы.</p>
        <p><strong>Срок хранения:</strong> пока ваш аккаунт активен. Для удаления обратитесь в Центр помощи.</p>
        <p class="muted" style="font-size:12px;margin-top:14px">Это краткое и понятное описание, а не полный юридический документ.</p>
      `,
    },

    // --- Status labels ---
    st_pending: { uz: "Kutilmoqda", ru: "Ожидание" },
    st_accepted: { uz: "Qabul qilindi", ru: "Принято" },
    st_on_way: { uz: "Yo'lda", ru: "В пути" },
    st_completed: { uz: "Yakunlandi", ru: "Завершено" },
    st_rejected: { uz: "Rad etildi", ru: "Отклонено" },
    st_cancelled: { uz: "Bekor qilindi", ru: "Отменено" },
    st_expired: { uz: "Muddati tugadi", ru: "Истёк срок" },

    // --- Common actions ---
    accept: { uz: "Qabul qilish", ru: "Принять" },
    reject: { uz: "Rad etish", ru: "Отклонить" },
    on_the_way: { uz: "Yo'ldaman", ru: "Уже еду" },
    greet_morning: { uz: "Xayrli tong", ru: "Доброе утро" },
    greet_day: { uz: "Xayrli kun", ru: "Добрый день" },
    greet_evening: { uz: "Xayrli kech", ru: "Добрый вечер" },
    finish: { uz: "Yakunlash", ru: "Завершить" },
    report: { uz: "⚠️ Shikoyat", ru: "⚠️ Пожаловаться" },
    report_reason_title: { uz: "Shikoyat sababi", ru: "Причина жалобы" },
    report_reason_no_show: { uz: "Kelmadi / javob bermadi", ru: "Не пришёл / не ответил" },
    report_reason_rude: { uz: "Muomalasi yomon", ru: "Плохое общение" },
    report_reason_fraud: { uz: "Firibgarlik / pul talab qildi", ru: "Мошенничество / вымогательство денег" },
    report_reason_quality: { uz: "Xizmat sifati past", ru: "Низкое качество услуги" },
    report_reason_other: { uz: "Boshqa", ru: "Другое" },
    report_comment_ph: { uz: "Batafsil yozing (ixtiyoriy)", ru: "Опишите подробнее (необязательно)" },
    report_send: { uz: "Yuborish", ru: "Отправить" },
    report_sent: { uz: "Shikoyat qabul qilindi", ru: "Жалоба принята" },
    report_confirm: { uz: "Shikoyatni yuborasizmi? Bu amalni qaytarib bo'lmaydi.", ru: "Отправить жалобу? Это действие нельзя отменить." },
  };

  let lang = "uz";

  function setLang(l) {
    lang = l === "ru" ? "ru" : "uz";
    document.documentElement.lang = lang;
  }

  function t(key, params) {
    const entry = DICT[key];
    let text = entry ? (entry[lang] || entry.uz) : key;
    if (params) {
      Object.keys(params).forEach((k) => { text = text.replace("{" + k + "}", params[k]); });
    }
    return text;
  }

  function applyStatic() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      el.innerHTML = t(key);
    });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      el.setAttribute("placeholder", t(el.dataset.i18nPh));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.setAttribute("title", t(el.dataset.i18nTitle));
    });
  }

  window.I18N = { setLang, t, applyStatic, get lang() { return lang; } };
})();
