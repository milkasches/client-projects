# Møbelsnekker I&W — сайт на Django

Лендинг, калькулятор цен, форма заказа (с фото), всплывающая форма консультации, админка для заявок и письма на почту.

```
iw-site/
├── manage.py
├── requirements.txt
├── .env.example          ← скопировать в .env
├── config/               ← настройки Django
└── core/
    ├── pricing.py        ← ВСЕ ЦЕНЫ КАЛЬКУЛЯТОРА (менять тут)
    ├── models.py         ← Order, Attachment, ConsultationRequest
    ├── views.py          ← страницы + API (/api/estimate, /api/order, /api/consultation)
    ├── forms.py, emails.py, admin.py, tests.py
    ├── templates/core/   ← base, index, calculator, privacy, модалка, письма
    └── static/core/      ← css, js (main.js, calculator.js), img
```

## Запуск на Mac

```bash
cd ~/uio/job/møbelsneaker/iw-site
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser     # логин для /admin
python manage.py test core           # автотесты (16 шт.)
python manage.py runserver
```

Откройте http://127.0.0.1:8000. Калькулятор: http://127.0.0.1:8000/price-calculator/, админка: http://127.0.0.1:8000/admin/.

## Письма на milkaolder@gmail.com

Пока в `.env` пустой `EMAIL_HOST_PASSWORD`, письма **не отправляются**, а печатаются в терминале, где запущен `runserver`. Так удобно проверять.

Чтобы письма реально приходили в Gmail:

1. Включите двухэтапную аутентификацию в аккаунте Google.
2. Создайте пароль приложения: https://myaccount.google.com/apppasswords
3. В `.env`:
   ```
   EMAIL_HOST_USER=milkaolder@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   NOTIFY_EMAIL=milkaolder@gmail.com
   ```
4. Перезапустите `runserver` и отправьте заявку с сайта.

На каждую заявку уходят 2 письма: владельцу (с данными, расчётом, фото во вложении и кнопкой «Open in admin»; «Ответить» сразу пишет клиенту) и клиенту (подтверждение). Когда сайт передадите мастеру, поменяйте `NOTIFY_EMAIL` и `CONTACT_EMAIL` на его почту.

## Цены

Все цены — **примерные**, в `core/pricing.py`, в NOK без НДС (на сайте показываются с 25 % MVA):

- `TYPES`: ставка за м² фасада (Ш×В) или столешницы (Ш×Г) + минимальная цена,
- `MATERIALS`: коэффициенты (ДСП 0.75 … орех 2.2),
- `FINISHES`, `COMPLEXITY`: коэффициенты,
- `EXTRAS`: ящики, двери, стеклянные двери, LED — цена за штуку,
- монтаж 12 % (мин. 2 500), доставка по зонам, этаж без лифта, срочность +20 %.

Диапазон «от–до» = расчёт −10 % / +15 %. Цены пересчитываются на сервере: подменить цену из браузера нельзя.

## Безопасность форм

CSRF-токен, скрытое поле-ловушка для ботов, лимит 8 заявок в час с одного IP, проверка файлов (до 5 шт., по 10 МБ, только фото и PDF), согласие на обработку данных.

## Перед публикацией

- `DJANGO_DEBUG=false`, длинный `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=вашдомен.no`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://вашдомен.no`
- `python manage.py collectstatic`
- запуск через `gunicorn config.wsgi`
- проверить текст на странице Privacy вместе с клиентом

## Как это работает «в реальности» (оптимизации)

**Отправка формы.** Заявка и файлы сохраняются в базу → клиент *сразу* видит «Спасибо» → письма уходят уже *после* ответа браузеру (`core/deferred.py`). Медленный Gmail больше не тормозит форму.

**Фото.** При загрузке фото уменьшаются до 2000 px и сжимаются в JPEG (10 МБ → ~300 КБ), HEIC с iPhone конвертируется, поворот исправляется, GPS-данные удаляются (`core/images.py`, нужен `Pillow`, для HEIC — `pillow-heif`). PDF хранятся как есть.

**Если письмо не ушло.** Заявка всё равно в базе. В админке колонка **Email**: ✔ отправлено / ✖ не доставлено (с причиной). Фильтр «owner email → Not delivered», действие «Resend email notification». Неотправленные письма автоматически повторяются (до 6 попыток).

**Резервные копии.** Раз в сутки (после первой заявки или захода в админку за день) создаётся `backups/backup-ДАТА/` с копией базы и архивом фото; хранятся последние 14. Время от времени скачивайте папку `backups` к себе — копия на том же сервере не спасёт, если пропадёт весь аккаунт.

**GDPR.** Заявки со статусом Done / Lost старше 365 дней удаляются вместе с файлами.

**Вручную или по расписанию:**
```bash
python manage.py maintenance            # всё сразу
python manage.py maintenance --backup   # только копия
python manage.py maintenance --retry    # только повтор писем
```
