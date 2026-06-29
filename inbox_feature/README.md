# "Kelgan to'lovlar" (Bank webhook inbox) — joylashtirish

## 1. Yangi app — to'liq papka
`notebook_inbox/` papkasini butunligicha loyihaga **`notebook/inbox/`** nomi
bilan ko'chiring (papka nomini `inbox` qilib o'zgartiring).

## 2. Mavjud fayllarni yangilash
| Shu yerdagi fayl        | Loyihadagi joyi                         |
|--------------------------|------------------------------------------|
| business_models.py       | notebook/business/models.py (almashtir) |
| business_migrations/*    | notebook/business/migrations/ ga qo'shing (0005, 0006, 0007 — yangi fayllar, eskilarini o'chirmang) |
| settings.py               | config/settings.py (almashtir)          |
| config_urls.py             | config/urls.py (almashtir)              |
| transaction_list.html       | templates/inbox/transaction_list.html (YANGI papka) |
| launcher.html                | templates/launcher.html (almashtir)     |
| inbox.css                     | static/css/inbox.css (YANGI)            |
| inbox.js                       | static/script/inbox.js (YANGI)          |

## 3. Migratsiya
```
python manage.py migrate
```
Bu safar **haqiqiy schema o'zgarishi bor** — `Business.webhook_token` maydoni
qo'shiladi (har bir biznes uchun avtomatik, noyob token yaratiladi) va yangi
`IncomingTransaction` jadvali yaratiladi. Hech qanday mavjud ma'lumot
o'zgarmaydi/yo'qolmaydi — backfill xavfsiz yozilgan (sinab ko'rilgan).

## 4. Webhook manzilini olish
"Kelgan to'lovlar" sahifasiga kirib (launcher menyusida), yuqori o'ngdagi
🔗 tugmasini bosing — manzil shu yerda ko'rinadi, nusxalash mumkin.

## 5. MacroDroid sozlash (telefonda)
1. MacroDroid'ni o'rnating, yangi makro yarating.
2. **Trigger**: "SMS Received" (yoki "Notification Received" — bank ilovasi
   bildirishnomasi uchun). Xohlasangiz faqat bank raqamidan kelgan SMS bilan
   cheklang.
3. **Action**: "HTTP Request" → Method: POST → URL: yuqorida nusxalangan
   webhook manzili → Body parametri: `text` = SMS/bildirishnoma matni
   (MacroDroid'ning "SMS Body"/"Notification Text" magic text'idan oling).
4. Saqlang, makroni yoqing.

## Eslatma — aniqlangan va tuzatilgan bug
Test paytida bitta muhim bug topildi va tuzatildi: O'zbek tili formatlash
sozlamasi (`USE_L10N=True`, `LANGUAGE_CODE='uz'`) sabab, summalar shablonda
vergul bilan (`200000,00`) chiqib, "raqam" turidagi input maydoniga kira
olmay, bo'sh qolardi. **Bu — butun loyihada boshqa joylarda ham (masalan,
mijoz/mahsulot tahrirlash formalarida) uchrashi mumkin bo'lgan umumiy
xavf** — agar shunday joylarni payqasangiz (raqam input'i tahrirlashda
bo'sh chiqsa), ayni shu sababdan bo'lishi mumkin, xabar bering, tekshirib
beraman.
