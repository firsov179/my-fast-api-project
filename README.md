# Итоговое домашнее задание по курсу Семинар наставника
# Разработка и деплой FastAPI-сервисов с использованием Docker
## Фирсов Федор Александрович

---

## Описание проекта

В рамках данной работы разработаны два микросервиса на FastAPI:

1. **TODO-сервис** — управление списком задач (CRUD)
2. **Сервис сокращения URL** — создание коротких ссылок

Оба сервиса используют SQLite для хранения данных и упакованы в Docker-контейнеры.

---

## TODO-сервис

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /items | Создание задачи |
| GET | /items | Список всех задач |
| GET | /items/{item_id} | Получение задачи по ID |
| PUT | /items/{item_id} | Обновление задачи |
| DELETE | /items/{item_id} | Удаление задачи |

### Дополнительный функционал

Помимо базовых требований реализовано:

- **Приоритеты задач** — поле `priority` с значениями `low`, `medium`, `high`
- **Теги** — поле `tags` для группировки задач по категориям

### Пример запроса

```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"title": "Найти крестраж", "description": "Медальон Слизерина в пещере", "priority": "high", "tags": ["крестражи", "Дамблдор"]}'
```

### Пример ответа

```json
{
  "id": 1,
  "title": "Найти крестраж",
  "description": "Медальон Слизерина в пещере",
  "completed": false,
  "priority": "high",
  "tags": ["крестражи", "Дамблдор"]
}
```

---

## Сервис сокращения URL

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /shorten | Создание короткой ссылки |
| GET | /{short_id} | Редирект на полный URL |
| GET | /stats/{short_id} | Информация о ссылке |
| DELETE | /{short_id} | Удаление ссылки |

### Дополнительный функционал

- **Срок действия ссылки** — поле `expires_at`, после указанной даты ссылка возвращает ошибку 410 Gone
- **Удаление ссылок** — возможность удалить созданную ссылку

### Пример создания ссылки

```bash
curl -X POST "http://localhost:8001/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://harrypotter.fandom.com/wiki/Hogwarts"}'
```

### Пример ответа

```json
{
  "short_id": "Ab3xK9",
  "short_url": "/Ab3xK9",
  "full_url": "https://harrypotter.fandom.com/wiki/Hogwarts",
  "expires_at": null
}
```

### Пример создания ссылки с истечением

```bash
curl -X POST "http://localhost:8001/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://harrypotter.fandom.com/wiki/Firebolt", "expires_at": "2025-12-25T00:00:00"}'
```

---

## Запуск через Docker

### 1. Создание томов

```bash
docker volume create todo_data
docker volume create shorturl_data
```

### 2. Запуск контейнеров

```bash
docker run -d -p 8000:80 -v todo_data:/app/data firsov179/todo-service:latest
docker run -d -p 8001:80 -v shorturl_data:/app/data firsov179/shorturl-service:latest
```

### 3. Проверка

- TODO-сервис: http://localhost:8000/docs
- Short URL сервис: http://localhost:8001/docs

---

## Локальный запуск (без Docker)

### TODO-сервис

```bash
cd todo_service
pip install -r requirements.txt
DATABASE_PATH=./data/todo.db uvicorn main:app --reload --port 8000
```

### Short URL сервис

```bash
cd shorturl_service
pip install -r requirements.txt
DATABASE_PATH=./data/shorturl.db uvicorn main:app --reload --port 8001
```

---

## Сборка и публикация образов

### Сборка

```bash
cd todo_service
docker build -t firsov179/todo-service:latest .

cd ../shorturl_service
docker build -t firsov179/shorturl-service:latest .
```

### Публикация на Docker Hub

```bash
docker login
docker push firsov179/todo-service:latest
docker push firsov179/shorturl-service:latest
```

---

## Тестирование

### TODO-сервис

```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"title": "Выучить Патронуса", "description": "Expecto Patronum!", "priority": "high", "tags": ["ЗОТИ", "заклинания"]}'

curl http://localhost:8000/items

curl -X PUT "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

curl -X DELETE http://localhost:8000/items/1
```

### Short URL сервис

```bash
curl -X POST "http://localhost:8001/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.wizardingworld.com"}'

curl http://localhost:8001/stats/<short_id>

curl -X DELETE http://localhost:8001/<short_id>
```
