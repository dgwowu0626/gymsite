# Gym Site

Учебный проект тренажёрного зала на `FastAPI + SQLite + HTML/CSS/JavaScript` с публичным сайтом, CRM и личными кабинетами.

## Что есть в проекте

- публичные страницы: главная, абонементы, тренеры, запись;
- старая форма обычной заявки без регистрации;
- регистрация и вход по телефону или email;
- хеширование паролей;
- авторизация через cookie-сессию;
- роли `client`, `trainer`, `admin`;
- кабинет клиента:
  - профиль;
  - мои записи;
  - отмена своей записи;
  - история тренировок;
  - мои абонементы;
  - покупка абонемента из сайта;
  - дата окончания;
  - остаток тренировок;
  - единая форма записи на тренировку на странице сайта и в кабинете;
- кабинет тренера:
  - записи к этому тренеру;
  - расписание на день и неделю;
  - список клиентов;
  - завершение тренировки;
  - комментарий по клиенту после тренировки;
- CRM / админка:
  - все записи и заявки;
  - статусы заявок;
  - удаление заявок;
  - список клиентов и заметки;
  - управление пользователями;
  - управление тренерами;
  - управление абонементами;
  - назначение абонемента клиенту;
  - статистика по заявкам, клиентам и абонементам.

## Стек

- `FastAPI`
- `SQLite`
- `SQLAlchemy`
- `Jinja2`
- `HTML / CSS / JavaScript`
- cookie sessions через `SessionMiddleware`

## Структура

```text
app/
  database.py
  main.py
  models.py
  schemas.py
  seed.py
static/
  css/styles.css
  js/main.js
  js/auth.js
  js/account.js
  js/admin.js
templates/
  base.html
  index.html
  memberships.html
  trainers.html
  booking.html
  login.html
  register.html
  account.html
  admin.html
requirements.txt
README.md
```

## База данных

Используются таблицы:

- `users`
- `user_profiles`
- `clients`
- `trainers`
- `subscriptions`
- `user_subscriptions`
- `bookings`
- `workout_history`

Файл базы создаётся автоматически: `gym.db`.

## Запуск

1. Создайте и активируйте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите сервер:

```bash
uvicorn app.main:app --reload
```

4. Откройте:

- сайт: `http://127.0.0.1:8000/`
- кабинет: `http://127.0.0.1:8000/cabinet`
- CRM: `http://127.0.0.1:8000/admin`
- Swagger API: `http://127.0.0.1:8000/docs`

## Тестовые учётные записи

Создаются автоматически при первом запуске:

- администратор:
  - `admin@northfit.local`
  - `admin123`
- тренер 1:
  - `trainer1@northfit.local`
  - `trainer123`
- тренер 2:
  - `trainer2@northfit.local`
  - `trainer123`
- тренер 3:
  - `trainer3@northfit.local`
  - `trainer123`

Клиентский аккаунт создаётся через страницу регистрации.

## Основные API

### Авторизация

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Публичная часть

- `GET /api/trainers`
- `GET /api/memberships`
- `POST /api/bookings`

### Кабинет клиента

- `GET /api/me/dashboard`
- `POST /api/me/bookings`
- `PATCH /api/me/bookings/{id}/cancel`

### Кабинет тренера

- `GET /api/trainer/dashboard`
- `PATCH /api/trainer/bookings/{id}/complete`

### CRM / админка

- `GET /api/bookings`
- `PATCH /api/bookings/{id}/status`
- `DELETE /api/bookings/{id}`
- `GET /api/clients`
- `PATCH /api/clients/{id}/note`
- `GET /api/stats`
- `GET /api/admin/users`
- `PATCH /api/admin/users/{id}`
- `GET /api/admin/trainers`
- `POST /api/admin/trainers`
- `PATCH /api/admin/trainers/{id}`
- `GET /api/admin/subscriptions`
- `POST /api/admin/subscriptions`
- `PATCH /api/admin/subscriptions/{id}`
- `GET /api/admin/user-subscriptions`
- `POST /api/admin/subscriptions/assign`

## Примечания

- проект рассчитан как учебный и остаётся простым без миграций и сложных frontend-фреймворков;
- старая форма заявки сохранена и работает параллельно с личными кабинетами;
- покупка абонемента начисляет клиенту количество посещений из настроек абонемента;
- запись из кабинета на персональные и групповые тренировки требует активный абонемент с доступными посещениями;
- тренера при записи можно не выбирать;
- обычный пользователь видит только свои данные, тренер — только свои тренировки, администратор — всю систему.
