# Open Hearts — сайт

Готовый статический сайт: 18 страниц, без cookies, без аналитики и без запросов к чужим серверам.

## 1. Скачать фото, шрифты и анимации (один раз)

Дважды щёлкните **`hent-filer.command`**. Откроется Терминал и скачает всё в папку `assets/`: 20 фото, шрифты и 3 библиотеки анимаций. Нужен интернет. Когда появится «Ferdig!», окно можно закрыть.

Если macOS не даёт запустить файл: правый клик → «Открыть» → «Открыть».

После этого сайт берёт всё только из своей папки: ни Google, ни Unsplash, ни Wix не видят посетителей.

## 2. Посмотреть локально

Откройте `index.html` двойным щелчком. Локально форма не отправляет заявку, а открывает письмо в почтовой программе. Настоящая отправка заработает после публикации (шаг 3).

## 3. Опубликовать на Netlify

1. Зарегистрируйтесь на <https://app.netlify.com> (бесплатно).
2. **Add new site → Deploy manually** и перетащите **всю папку** `openhearts` (после шага 1).
3. Через минуту сайт будет доступен по ссылке вида `xxx.netlify.app`.
4. **Формы:** Site configuration → Forms → **Enable form detection**, затем загрузите папку ещё раз. Появятся три формы: `pamelding`, `medlemskap`, `kontakt`.
5. **Уведомления на почту:** Forms → Form notifications → Add notification → Email → `post@openhearts.no`.
6. **Домен:** Domain management → Add a domain → `www.openhearts.no`. Netlify покажет, какие DNS-записи поменять у регистратора домена.

## 4. GDPR: что уже сделано и что сделать организации

Уже сделано:
- нет cookies, трекеров и аналитики, поэтому cookie-баннер не нужен;
- шрифты, фото и скрипты лежат на своём сервере (локальные Google Fonts);
- в каждой форме обязательная галочка согласия со ссылкой на политику конфиденциальности;
- защита от спама без reCAPTCHA (скрытое поле honeypot);
- в политике конфиденциальности добавлены Netlify как обработчик данных, передача в США, права пользователя, жалоба в Datatilsynet и фраза об отсутствии cookies;
- заголовки безопасности в `netlify.toml`: CSP запрещает загрузку чего-либо с чужих доменов.

Нужно сделать организации:
- [ ] Принять **DPA** Netlify (Data Processing Agreement): https://www.netlify.com/gdpr-ccpa/
- [ ] Регулярно удалять заявки из Netlify (Forms → удалить) после того, как перенесли их к себе. Так написано в политике.
- [ ] Показать обновлённую политику конфиденциальности руководителю (Markus Ribe) и при желании юристу. Это не юридическая консультация.
- [ ] Если выберете не Netlify, а другой хостинг или сервис форм, поправить пункты 8 и 9 в `personvern.html`.

## 5. Проверить перед запуском

- [ ] Пролистать все страницы на iPhone (Safari) и на Android.
- [ ] Отправить тестовую заявку из каждой из трёх форм и проверить, что письмо пришло.
- [ ] Уточнить у организации устаревшие тексты: время языкового кафе («ikke bestemt»), статус проекта про дейтинг (окт.–нояб. 2026), даты курсов.
- [ ] Если домен не `www.openhearts.no`, заменить его в `sitemap.xml`, `robots.txt` и в теге `<link rel="canonical">` / `og:` в начале каждой страницы.

## Структура

```
index.html            главная
kurs.html             курсы, подбор курса, расписание, лист ожидания
pamelding.html        запись на курс (форма)
prosjekter.html       проекты
sprakkafe.html, trygge-relasjoner.html, dating.html, juridisk.html, puzik.html
om-oss.html, pris.html, medlem.html (форма), frivillig.html, stott-oss.html
kontakt.html          контакты (форма)
personvern.html       политика конфиденциальности
donasjonsvilkar.html  условия пожертвований
404.html
assets/css/style.css  стили
assets/js/site.js     меню, формы, подбор курса
assets/js/motion.js   анимации (GSAP, ScrollTrigger, Lenis)
assets/img, assets/fonts   наполняются скриптом hent-filer.command
netlify.toml, robots.txt, sitemap.xml
```

Фото: Open Hearts, Unsplash (лицензия Unsplash), Wikimedia Commons (норвежский паспорт, public domain).
