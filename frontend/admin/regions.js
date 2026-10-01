/* O'zbekiston viloyatlari/respublikasi va ularning tumanlari.
   Manba: Vikipediya (2026-y. holatiga yaqin). Ma'muriy chegaralar vaqti-vaqti
   bilan o'zgaradi (yangi tumanlar tashkil topadi) — ro'yxatni davriy tekshirib
   turish tavsiya etiladi. Qiymatlar (value) backendga aynan shu satr sifatida
   yuboriladi (VetProfile.city/district — oddiy matn maydoni). */
(function () {
  "use strict";

  const REGIONS = [
    {
      name: "Toshkent shahri",
      center: [41.3111, 69.2797],
      districts: ["Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek", "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yangihayot", "Yashnobod", "Yunusobod"],
    },
    {
      name: "Toshkent viloyati",
      center: [40.9167, 69.3417],
      districts: ["Bekobod", "Bo'ka", "Bo'stonliq", "Chinoz", "Qibray", "Ohangaron", "Oqqo'rg'on", "O'rtachirchiq", "Parkent", "Piskent", "Quyichirchiq", "Toshkent tumani", "Yangiyo'l", "Yuqorichirchiq", "Zangiota"],
    },
    {
      name: "Andijon viloyati",
      center: [40.7833, 72.3333],
      districts: ["Andijon tumani", "Asaka", "Baliqchi", "Bo'ston", "Buloqboshi", "Izboskan", "Jalaquduq", "Xo'jaobod", "Qo'rg'ontepa", "Marhamat", "Oltinko'l", "Paxtaobod", "Shahrixon", "Ulug'nor"],
    },
    {
      name: "Buxoro viloyati",
      center: [39.7747, 64.4286],
      districts: ["Buxoro tumani", "G'ijduvon", "Jondor", "Kogon", "Olot", "Peshku", "Qorako'l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent"],
    },
    {
      name: "Farg'ona viloyati",
      center: [40.3842, 71.7843],
      districts: ["Bog'dod", "Beshariq", "Buvayda", "Dang'ara", "Farg'ona tumani", "Furqat", "Oltiariq", "Qo'shtepa", "Quva", "Rishton", "So'x", "Toshloq", "Uchko'prik", "Yozyovon"],
    },
    {
      name: "Jizzax viloyati",
      center: [40.1158, 67.8422],
      districts: ["Arnasoy", "Baxmal", "Do'stlik", "Forish", "G'allaorol", "Mirzacho'l", "Paxtakor", "Sharof Rashidov", "Yangiobod", "Zafarobod", "Zarbdor", "Zomin"],
    },
    {
      name: "Xorazm viloyati",
      center: [41.55, 60.6333],
      districts: ["Bog'ot", "Gurlan", "Hazorasp", "Xonqa", "Xiva", "Qo'shko'pir", "Shovot", "Tuproqqal'a", "Urganch tumani", "Yangiariq", "Yangibozor"],
    },
    {
      name: "Namangan viloyati",
      center: [40.9983, 71.6726],
      districts: ["Chortoq", "Chust", "Kosonsoy", "Mingbuloq", "Namangan tumani", "Norin", "Pop", "To'raqo'rg'on", "Uchqo'rg'on", "Uychi", "Yangiqo'rg'on"],
    },
    {
      name: "Navoiy viloyati",
      center: [40.0844, 65.3792],
      districts: ["Karmana", "Konimex", "Navbahor", "Nurota", "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi"],
    },
    {
      name: "Qashqadaryo viloyati",
      center: [38.8606, 65.7891],
      districts: ["Chiroqchi", "Dehqonobod", "G'uzor", "Kasbi", "Kitob", "Ko'kdala", "Koson", "Mirishkor", "Muborak", "Nishon", "Qamashi", "Qarshi tumani", "Shahrisabz", "Yakkabog'"],
    },
    {
      name: "Qoraqalpog'iston Respublikasi",
      center: [42.4531, 59.6103],
      districts: ["Amudaryo", "Beruniy", "Bo'zatov", "Chimboy", "Ellikqal'a", "Kegeyli", "Mo'ynoq", "Nukus tumani", "Qanliko'l", "Qorao'zak", "Qo'ng'irot", "Shumanay", "Taxiatosh", "Taxtako'pir", "To'rtko'l", "Xo'jayli"],
    },
    {
      name: "Samarqand viloyati",
      center: [39.6542, 66.9597],
      districts: ["Bulung'ur", "Ishtixon", "Jomboy", "Kattaqo'rg'on", "Narpay", "Nurobod", "Oqdaryo", "Pastdarg'om", "Paxtachi", "Payariq", "Qo'shrabot", "Samarqand tumani", "Toyloq", "Urgut"],
    },
    {
      name: "Sirdaryo viloyati",
      center: [40.4897, 68.7842],
      districts: ["Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod", "Sirdaryo tumani", "Xovos"],
    },
    {
      name: "Surxondaryo viloyati",
      center: [37.2242, 67.2783],
      districts: ["Angor", "Bandixon", "Boysun", "Denov", "Jarqo'rg'on", "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo'rg'on", "Sariosiyo", "Sherobod", "Sho'rchi", "Termiz tumani", "Uzun"],
    },
  ];

  window.UZ_REGIONS = REGIONS;
})();
