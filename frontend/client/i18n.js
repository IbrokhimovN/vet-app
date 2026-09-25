/* Mijoz Mini App — til tizimi (uz/ru). Asosiy matnlar tarjima qilingan:
   navigatsiya, sarlavhalar, umumiy tugmalar, holat yorliqlari, bo'sh ekranlar. */
(function () {
  "use strict";

  const DICT = {
    // --- Bottom nav ---
    nav_home: { uz: "Bosh sahifa", ru: "Главная" },
    nav_vets: { uz: "Vetlar", ru: "Ветврачи" },
    nav_visits: { uz: "So'rovlar", ru: "Заявки" },
    nav_profile: { uz: "Profil", ru: "Профиль" },

    // --- Home ---
    hero_tag: { uz: "MENING YORDAMCHIM", ru: "МОЙ ПОМОЩНИК" },
    hero_title: { uz: "Sog'lom hayvon,<br />xotirjam kun.", ru: "Здоровое животное —<br />спокойный день." },
    hero_sub: { uz: "Ishonchli veterinarlarni toping va bir necha bosishda chaqiring.", ru: "Найдите надёжного ветеринара и вызовите в пару касаний." },
    home_help_title: { uz: "Kimga yordam kerak?", ru: "Кому нужна помощь?" },
    home_quick_title: { uz: "Tezkor xizmatlar", ru: "Быстрые действия" },
    qt_vet: { uz: "Vet topish", ru: "Найти врача" },
    qt_visits: { uz: "So'rovlarim", ru: "Мои заявки" },
    qt_pets: { uz: "Hayvonlarim", ru: "Мои питомцы" },
    qt_tender: { uz: "Ochiq so'rov", ru: "Открытая заявка" },
    active_request_title: { uz: "Faol so'rovingiz", ru: "Ваша активная заявка" },
    nearby_vets_title: { uz: "Yaqin atrofdagi veterinarlar", ru: "Ветврачи рядом" },
    link_all: { uz: "Barchasi", ru: "Все" },

    // --- Vets search ---
    vets_eyebrow: { uz: "Qidiruv", ru: "Поиск" },
    vets_title: { uz: "Veterinar toping", ru: "Найти ветеринара" },
    search_placeholder: { uz: "🔍 Ism yoki klinika...", ru: "🔍 Имя или клиника..." },
    type_all: { uz: "Barcha turlar", ru: "Все типы" },
    type_home: { uz: "🏠 Uyga boradi", ru: "🏠 Выезд на дом" },
    type_online: { uz: "💬 Online", ru: "💬 Онлайн" },
    sort_rating: { uz: "⭐ Reyting", ru: "⭐ Рейтинг" },
    sort_distance: { uz: "📍 Masofa", ru: "📍 Расстояние" },
    seg_list: { uz: "📋 Ro'yxat", ru: "📋 Список" },
    seg_map: { uz: "🗺️ Xarita", ru: "🗺️ Карта" },
    vets_count: { uz: "{n} ta veterinar", ru: "Ветеринаров: {n}" },
    vets_count_empty: { uz: "Veterinarlar", ru: "Ветеринары" },
    empty_vets: { uz: "Hech narsa topilmadi", ru: "Ничего не найдено" },
    empty_vets_cta: { uz: "📢 Ochiq so'rov joylashtiring", ru: "📢 Разместить открытую заявку" },
    load_more: { uz: "Yana yuklash", ru: "Загрузить ещё" },
    map_empty: { uz: "Joylashuvi ko'rsatilgan veterinar topilmadi", ru: "Ветврачи с указанной геолокацией не найдены" },
    map_loc_unknown: { uz: "Joylashuv aniqlanmagan", ru: "Локация не определена" },
    map_candidates: { uz: "Sizga mos <b>{n}</b> ta nomzod bor", ru: "Найдено подходящих: <b>{n}</b>" },
    map_candidates_empty: { uz: "Mos nomzod topilmadi", ru: "Подходящих не найдено" },
    map_view_btn: { uz: "Ko'rish →", ru: "Смотреть →" },
    map_to_list: { uz: "Ro'yxat", ru: "Список" },

    // --- Vet detail ---
    vd_eyebrow: { uz: "Profil", ru: "Профиль" },
    vd_verified: { uz: "✓ Tasdiqlangan veterinar", ru: "✓ Подтверждённый ветврач" },
    vd_reviews_stat: { uz: "izoh", ru: "отзывов" },
    vd_years_stat: { uz: "yil tajriba", ru: "лет опыта" },
    vd_distance_stat: { uz: "masofa", ru: "расстояние" },
    vd_about_title: { uz: "Haqida", ru: "О враче" },
    vd_spec_title: { uz: "Mutaxassislik", ru: "Специализация" },
    vd_services_title: { uz: "Xizmatlar", ru: "Услуги" },
    vd_services_hint: { uz: "Chaqirishda aynan shu xizmatni tanlash uchun bosing (ixtiyoriy)", ru: "Нажмите, чтобы выбрать эту услугу при вызове (необязательно)" },
    vd_services_empty: { uz: "Xizmatlar kiritilmagan", ru: "Услуги не указаны" },
    vd_from_price: { uz: "dan {n} so'm", ru: "от {n} сум" },
    vd_reviews_title: { uz: "Izohlar", ru: "Отзывы" },
    vd_reviews_empty: { uz: "Hali izoh yo'q", ru: "Отзывов пока нет" },
    loading: { uz: "Yuklanmoqda...", ru: "Загрузка..." },
    vd_pet_title: { uz: "Qaysi hayvon uchun?", ru: "Для какого питомца?" },
    vd_pet_none: { uz: "Tanlanmagan", ru: "Не выбрано" },
    vd_call_title: { uz: "📞 Chaqirish", ru: "📞 Вызов" },
    vd_scheduled_label: { uz: "Vaqtni belgilash (ixtiyoriy)", ru: "Назначить время (необязательно)" },
    vd_note_placeholder: { uz: "Muammoni qisqacha yozing...", ru: "Кратко опишите проблему..." },
    vd_address_placeholder: { uz: "Manzil (ko'cha, uy) — GPS bo'lmasa ham yordam beradi", ru: "Адрес (улица, дом) — поможет, даже если GPS недоступен" },
    vd_send: { uz: "Yuborish", ru: "Отправить" },
    type_home_short: { uz: "🏠 Uyga", ru: "🏠 На дом" },
    type_contact: { uz: "📞 Kontakt", ru: "📞 Контакт" },
    unnamed_vet: { uz: "Veterinar", ru: "Ветеринар" },

    // --- Tender ---
    tender_eyebrow: { uz: "Ochiq so'rov", ru: "Открытая заявка" },
    tender_new_title: { uz: "Yangi ochiq so'rov", ru: "Новая открытая заявка" },
    tender_city_placeholder: { uz: "Shahar", ru: "Город" },
    select_region: { uz: "— Viloyatni tanlang —", ru: "— Выберите область —" },
    select_district: { uz: "— Avval viloyatni tanlang —", ru: "— Сначала выберите область —" },
    location_title: { uz: "Joylashuv", ru: "Местоположение" },
    city_label: { uz: "Viloyat", ru: "Область" },
    district_label: { uz: "Tuman", ru: "Район" },
    geo_btn: { uz: "📍 Joriy joylashuvni olish (GPS)", ru: "📍 Определить местоположение (GPS)" },
    client_location_hint: { uz: "Yaqin atrofdagi veterinarlarni topish uchun kerak. Viloyat/tuman tanlansa, aniq joylashuv taxminan shu markazga qo'yiladi.", ru: "Нужно, чтобы находить ближайших ветеринаров. При выборе области/района местоположение устанавливается примерно в её центр." },
    geo_denied: { uz: "GPS ruxsat berilmadi. Iltimos, yuqorida viloyat/tumanni tanlang.", ru: "Доступ к GPS не разрешён. Пожалуйста, выберите область/район выше." },
    geo_saved: { uz: "✅ Joylashuv saqlandi", ru: "✅ Местоположение сохранено" },
    tender_note_placeholder: { uz: "Muammoni qisqacha yozing...", ru: "Кратко опишите проблему..." },
    tender_budget_placeholder: { uz: "Taxminiy byudjet (ixtiyoriy, so'm)", ru: "Примерный бюджет (необязательно, сум)" },
    tender_send: { uz: "Ochiq so'rov joylash", ru: "Разместить заявку" },
    tender_mine_title: { uz: "Mening ochiq so'rovlarim", ru: "Мои открытые заявки" },
    tender_empty: { uz: "Hali ochiq so'rov yo'q", ru: "Открытых заявок пока нет" },

    // --- Notifications ---
    notif_title: { uz: "Bildirishnomalar", ru: "Уведомления" },
    notif_empty: { uz: "Bildirishnoma yo'q", ru: "Уведомлений нет" },

    // --- Visits ---
    visits_eyebrow: { uz: "Mening rejam", ru: "Мой план" },
    visits_title: { uz: "So'rovlarim", ru: "Мои заявки" },
    seg_upcoming: { uz: "Faol", ru: "Активные" },
    seg_past: { uz: "Tugagan", ru: "Завершённые" },
    visits_empty: { uz: "Hozircha so'rov yo'q", ru: "Заявок пока нет" },

    // --- Profile ---
    profile_eyebrow: { uz: "Hisob", ru: "Аккаунт" },
    profile_title: { uz: "Profil", ru: "Профиль" },
    photo_hint: { uz: "Rasm qo'yish uchun bosing", ru: "Нажмите, чтобы добавить фото" },
    ph_first: { uz: "Ism", ru: "Имя" },
    ph_last: { uz: "Familiya", ru: "Фамилия" },
    save: { uz: "Saqlash", ru: "Сохранить" },
    identity_onboard_title: { uz: "Profilingizni to'ldiring", ru: "Заполните профиль" },
    identity_onboard_sub: { uz: "Veterinar siz bilan bog'lanishi uchun ism va telefon raqamingizni kiriting", ru: "Укажите имя и номер телефона, чтобы ветеринар мог связаться с вами" },
    identity_onboard_skip: { uz: "Keyinroq", ru: "Позже" },
    identity_first_required: { uz: "Ismingizni kiriting", ru: "Введите имя" },
    stat_pets: { uz: "Hayvon", ru: "Питомцы" },
    stat_active: { uz: "Faol so'rov", ru: "Активные заявки" },
    stat_total: { uz: "Jami so'rov", ru: "Всего заявок" },
    my_pets_title: { uz: "Mening hayvonlarim", ru: "Мои питомцы" },
    pets_empty: { uz: "Hali hayvon qo'shilmagan", ru: "Питомцы ещё не добавлены" },
    ph_pet_name: { uz: "Ism (mas. Bars)", ru: "Имя (напр. Барс)" },
    ph_pet_species: { uz: "Turi (mas. It)", ru: "Вид (напр. Собака)" },
    settings_title: { uz: "Sozlamalar", ru: "Настройки" },
    help_title: { uz: "Yordam markazi", ru: "Центр помощи" },
    help_sub: { uz: "Savol yoki muammo bo'lsa", ru: "Если есть вопрос или проблема" },
    privacy_title: { uz: "Maxfiylik siyosati", ru: "Политика конфиденциальности" },
    privacy_sub: { uz: "Qanday ma'lumot yig'amiz", ru: "Какие данные мы собираем" },
    oferta_title: { uz: "Ommaviy oferta", ru: "Публичная оферта" },
    oferta_sub: { uz: "Foydalanish shartlari", ru: "Условия использования" },
    privacy_body: {
      uz: `
        <p><strong>Qanday ma'lumot yig'amiz:</strong> Telegram profilingizdagi ism, username va rasm; siz kiritgan telefon raqami; hayvonlaringiz va so'rovlaringiz haqidagi ma'lumot; xaritada belgilagan joylashuv (agar bersangiz).</p>
        <p><strong>Nima uchun:</strong> Sizni mos veterinar bilan bog'lash, chaqiruvingizni yetkazish va holat haqida bildirishnoma yuborish uchun. Boshqa maqsadda ishlatilmaydi.</p>
        <p><strong>Kim ko'radi:</strong> Faqat siz tanlagan yoki so'rovingizga taklif yuborgan veterinar, va texnik xizmat ko'rsatish uchun administrator.</p>
        <p><strong>Uchinchi tomonlarga berish:</strong> Ma'lumotlaringiz sotilmaydi va reklama maqsadida berilmaydi.</p>
        <p><strong>Saqlash muddati:</strong> Hisobingiz faol ekan saqlanadi. O'chirishni so'rasangiz, Yordam markazi orqali murojaat qiling.</p>
        <p class="muted" style="font-size:12px;margin-top:14px">Bu qisqa va tushunarli tavsif, to'liq yuridik oferta emas.</p>
      `,
      ru: `
        <p><strong>Какие данные собираем:</strong> имя, username и фото из вашего профиля Telegram; введённый вами номер телефона; данные о питомцах и заявках; местоположение на карте (если вы его укажете).</p>
        <p><strong>Для чего:</strong> чтобы связать вас с подходящим ветеринаром, доставить заявку и присылать уведомления о статусе. Для других целей не используется.</p>
        <p><strong>Кто видит:</strong> только выбранный вами ветеринар (или тот, кто откликнулся на заявку), и администратор для технической поддержки.</p>
        <p><strong>Передача третьим лицам:</strong> данные не продаются и не передаются для рекламы.</p>
        <p><strong>Срок хранения:</strong> пока ваш аккаунт активен. Для удаления обратитесь в Центр помощи.</p>
        <p class="muted" style="font-size:12px;margin-top:14px">Это краткое и понятное описание, а не полный юридический документ.</p>
      `,
    },
    language_title: { uz: "Til", ru: "Язык" },
    language_sub: { uz: "Ilova tilini tanlang", ru: "Выберите язык приложения" },

    // --- Status labels ---
    st_pending: { uz: "Kutilmoqda", ru: "Ожидание" },
    st_accepted: { uz: "Qabul qilindi", ru: "Принято" },
    st_on_way: { uz: "Yo'lda", ru: "В пути" },
    st_completed: { uz: "Yakunlandi", ru: "Завершено" },
    st_rejected: { uz: "Rad etildi", ru: "Отклонено" },
    st_cancelled: { uz: "Bekor qilindi", ru: "Отменено" },
    st_expired: { uz: "Vet javob bermadi", ru: "Врач не ответил" },
    sr_st_open: { uz: "Ochiq", ru: "Открыто" },
    sr_st_assigned: { uz: "Vet tayinlandi", ru: "Врач назначен" },
    sr_st_completed: { uz: "Yakunlandi", ru: "Завершено" },
    sr_st_cancelled: { uz: "Bekor qilindi", ru: "Отменено" },
    sr_st_expired: { uz: "Muddati tugadi", ru: "Срок истёк" },

    // --- Common actions (JS-generated cards) ---
    review: { uz: "⭐ Baholash", ru: "⭐ Оценить" },
    review_edit: { uz: "✏️ Izohni tahrirlash", ru: "✏️ Редактировать отзыв" },
    delete: { uz: "O'chirish", ru: "Удалить" },
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
    cancel: { uz: "Bekor qilish", ru: "Отменить" },
    view_offers: { uz: "Takliflarni ko'rish", ru: "Смотреть предложения" },
    hide: { uz: "Yashirish", ru: "Скрыть" },
    accept: { uz: "Qabul qilish", ru: "Принять" },
    sent_ago: { uz: "yuborildi", ru: "отправлено" },
    greet_morning: { uz: "Xayrli tong", ru: "Доброе утро" },
    greet_day: { uz: "Xayrli kun", ru: "Добрый день" },
    greet_evening: { uz: "Xayrli kech", ru: "Добрый вечер" },
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
