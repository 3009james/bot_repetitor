# Telegram Mini App для репетитора

Проект подготовлен как полноценное Telegram Mini App:

- ученик открывает бота и попадает в мини-приложение;
- видит приветствие, свою аватарку из Telegram, информацию о вас и кнопку записи;
- выбирает свободный день и время;
- после записи видит подтверждение на главном экране;
- вам приходит уведомление в Telegram;
- в админ-панели можно менять описание, загружать фото, добавлять свободные слоты и смотреть записи.

## Что внутри

- `backend` - FastAPI API, Telegram-бот на aiogram, работа с PostgreSQL;
- `backend/app/static` - интерфейс Mini App;
- `docker-compose.yml` - база, приложение и HTTPS-прокси через Caddy;
- `Caddyfile` - автоматический HTTPS для домена;
- `.env.example` - шаблон переменных окружения.

## Быстрый старт

1. Создайте бота через `@BotFather` и сохраните токен.
2. Скопируйте `.env.example` в `.env`.
3. Заполните:
   - `BOT_TOKEN`
   - `ADMIN_TELEGRAM_ID`
   - `APP_DOMAIN`
   - `APP_URL`
4. Запустите:

```bash
docker compose up --build
```

5. Откройте бота в Telegram и отправьте `/start`.

## Продакшен на VPS

Telegram Mini App в продакшене должен открываться по HTTPS. В этом проекте HTTPS уже настроен через Caddy.

Перед запуском на VPS нужно:

1. Добавить `A`-запись домена на IP вашего VPS.
2. Открыть на сервере порты `80` и `443`.
3. В `.env` прописать:

```env
APP_DOMAIN=ваш-домен.ru
APP_URL=https://ваш-домен.ru
```

## Пошагово: Git + VPS + Docker

### 1. Локально

```bash
git init
git add .
git commit -m "Initial tutor bot"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

### 2. На VPS

Установите:

- Docker
- Docker Compose plugin
- Git

Дальше:

```bash
git clone https://github.com/USERNAME/REPO.git
cd REPO
cp .env.example .env
docker compose up -d --build
```

Проверка логов:

```bash
docker compose logs -f app
```

### 3. Как обновлять бота

Локально:

```bash
git add .
git commit -m "Update booking flow"
git push
```

На VPS:

```bash
cd REPO
git pull
docker compose up -d --build
```

## Как привязать Mini App к боту

1. Откройте `@BotFather`.
2. Выполните `/mybots`.
3. Выберите бота.
4. Настройте `Menu Button` или используйте `/start`.
5. Укажите URL: `https://ваш-домен.ru`.

## Где что редактировать

- логика API: `backend/app/routers`
- модели БД: `backend/app/models.py`
- Telegram-бот: `backend/app/bot.py`
- интерфейс: `backend/app/static`

## Что можно улучшить дальше

- отмена записи учеником;
- подтверждение/перенос записи администратором;
- фильтр слотов по предметам;
- автоматическое напоминание перед занятием.
