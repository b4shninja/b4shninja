# Lab 07 — Docker Compose: оркестрация микросервисов

## 🎯 Цель лабораторной работы

Научиться запускать и управлять мультиконтейнерными приложениями с помощью Docker Compose. Понять как работают сети, volumes и зависимости между сервисами.

---

## 📚 Теория

### Зачем нужен Docker Compose?

Представь: у тебя веб-приложение + PostgreSQL + Redis + Nginx. Без Compose нужно:

```bash
docker run -d --name postgres -e POSTGRES_PASSWORD=secret postgres:15
docker run -d --name redis redis:7
docker run -d --name web --link postgres --link redis -p 8080:8080 myapp:latest
docker run -d --name nginx --link web -p 80:80 nginx:latest
```

**Проблемы:**
- Куча команд, легко ошибиться
- Сложно воспроизвести окружение
- Нет управления зависимостями
- Порты и переменные окружения в разных местах

**С Compose:**
```bash
docker compose up -d
```

Всё описано в одном файле `docker-compose.yml`, версионируется в git, воспроизводимо.

---

### Структура docker-compose.yml

```yaml
version: '3.8'  # Версия формата (необязательно в новых версиях)

services:       # Список контейнеров
  service_name:
    image: или build:
    ports:      # Проброс портов host:container
    environment:  # Переменные окружения
    volumes:    # Монтирование данных
    networks:   # Подключение к сетям
    depends_on: # Зависимости от других сервисов

volumes:        # Определение named volumes
  volume_name:

networks:       # Определение сетей
  network_name:
```

---

### Основные команды Docker Compose

```bash
# Поднять все сервисы
docker compose up -d

# Посмотреть статус
docker compose ps

# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f web

# Зайти в контейнер
docker compose exec web bash

# Перезапустить сервис
docker compose restart web

# Остановить все сервисы
docker compose stop

# Остановить и удалить контейнеры
docker compose down

# Остановить и удалить контейнеры + volumes
docker compose down -v

# Пересобрать образы и запустить
docker compose up -d --build

# Масштабирование (запуск N реплик)
docker compose up -d --scale web=3
```

---

### Networks: как контейнеры общаются

По умолчанию Docker Compose создаёт bridge-сеть для всех сервисов:

```yaml
services:
  web:
    image: myapp:latest
    networks:
      - backend

  postgres:
    image: postgres:15
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

**Важно:**
- Контейнеры видят друг друга по имени сервиса
- `web` может подключиться к `postgres:5432`
- Разные Compose-проекты изолированы друг от друга

---

### Volumes: персистентность данных

#### Named Volumes (рекомендуется для баз данных)

```yaml
services:
  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:  # Docker управляет этим volume
```

#### Bind Mounts (для разработки)

```yaml
services:
  web:
    image: nginx
    volumes:
      - ./html:/usr/share/nginx/html  # Локальная папка → контейнер
```

#### tmpfs (в оперативной памяти)

```yaml
services:
  cache:
    image: redis
    tmpfs:
      - /data  # Данные в RAM, исчезнут при остановке
```

---

### Environment Variables

#### Прямо в docker-compose.yml

```yaml
services:
  web:
    image: myapp
    environment:
      DB_HOST: postgres
      DB_PASSWORD: secret123
```

#### Через .env файл (рекомендуется)

`.env`:
```bash
DB_PASSWORD=secret123
REDIS_PORT=6379
APP_ENV=production
```

`docker-compose.yml`:
```yaml
services:
  web:
    image: myapp
    environment:
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_PORT: ${REDIS_PORT}
      APP_ENV: ${APP_ENV}
```

**⚠️ Важно:** Не коммить `.env` в git! Добавь в `.gitignore`.

---

### depends_on и healthcheck

#### Проблема

`depends_on` запускает контейнеры в порядке, но НЕ ждёт готовности сервиса:

```yaml
services:
  web:
    depends_on:
      - postgres  # web запустится ПОСЛЕ postgres, но postgres может быть не готов!
```

#### Решение: healthcheck

```yaml
services:
  postgres:
    image: postgres:15
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    depends_on:
      postgres:
        condition: service_healthy  # Ждём пока postgres пройдёт healthcheck
```

Теперь `web` стартует только когда `postgres` реально готов принимать подключения.

---

## 🛠️ Практика

### Задание 1: Простой веб + PostgreSQL

**Цель:** Поднять Flask-приложение с базой данных PostgreSQL.

1. Создай директорию проекта:
```bash
mkdir lab07-task1 && cd lab07-task1
```

2. Создай простое Flask-приложение `app.py`:

```python
from flask import Flask
import psycopg2
import os

app = Flask(__name__)

@app.route('/')
def hello():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            database=os.getenv('DB_NAME', 'testdb'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'secret')
        )
        return "Connected to database successfully!"
    except Exception as e:
        return f"Failed to connect: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

3. Создай `requirements.txt`:
```
flask==3.0.0
psycopg2-binary==2.9.9
```

4. Создай `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

5. Создай `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      DB_HOST: postgres
      DB_NAME: testdb
      DB_USER: postgres
      DB_PASSWORD: secret
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - app-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - app-network

volumes:
  pgdata:

networks:
  app-network:
    driver: bridge
```

6. Запусти:
```bash
docker compose up -d
```

7. Проверь:
```bash
# Статус
docker compose ps

# Логи
docker compose logs -f

# Открой в браузере
curl http://localhost:5000
```

**Ожидаемый результат:** `Connected to database successfully!`

---

### Задание 2: Полный стек (Web + DB + Cache + Proxy)

**Цель:** Поднять полноценное приложение с Nginx, Flask, PostgreSQL и Redis.

1. Создай структуру проекта:

```bash
mkdir lab07-task2 && cd lab07-task2
mkdir app nginx
```

2. Создай `app/app.py`:

```python
from flask import Flask, jsonify
import psycopg2
import redis
import os

app = Flask(__name__)

# Redis connection
cache = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=6379,
    decode_responses=True
)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        database=os.getenv('DB_NAME', 'appdb'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'secret')
    )

@app.route('/')
def index():
    return jsonify({
        "message": "API is running",
        "endpoints": ["/db", "/cache", "/health"]
    })

@app.route('/db')
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({"database": "connected", "version": version})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cache')
def test_cache():
    try:
        # Increment counter
        count = cache.incr('visit_count')
        return jsonify({
            "cache": "connected",
            "visit_count": count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

3. Создай `app/requirements.txt`:
```
flask==3.0.0
psycopg2-binary==2.9.9
redis==5.0.1
```

4. Создай `app/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

5. Создай `nginx/nginx.conf`:

```nginx
upstream flask_app {
    server web:5000;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

6. Создай `.env`:
```bash
DB_PASSWORD=supersecret123
DB_NAME=appdb
DB_USER=postgres
REDIS_HOST=redis
```

7. Создай `docker-compose.yml`:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - web
    networks:
      - frontend

  web:
    build: ./app
    environment:
      DB_HOST: postgres
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: ${REDIS_HOST}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - frontend
      - backend

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    networks:
      - backend

volumes:
  pgdata:

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

8. Запусти:
```bash
docker compose up -d --build
```

9. Проверь:
```bash
# API endpoints
curl http://localhost:8080/
curl http://localhost:8080/db
curl http://localhost:8080/cache
curl http://localhost:8080/health

# Несколько раз запроси /cache и смотри как растёт счётчик
curl http://localhost:8080/cache
curl http://localhost:8080/cache
```

10. Посмотри логи:
```bash
docker compose logs -f web
```

---

### Задание 3: Дебаг типичных проблем

**Сценарий 1: База не готова**

Убери `healthcheck` из postgres и `condition: service_healthy` из web. Запусти:

```bash
docker compose up -d
```

**Что увидишь:** Web пытается подключиться к postgres, но получает `Connection refused`.

**Как починить:** Верни healthcheck.

---

**Сценарий 2: Volumes не сохраняются**

Останови контейнеры и удали volumes:
```bash
docker compose down -v
```

Запусти снова и проверь счётчик `/cache` — он сброшен в 0.

**Как сохранить:** Named volumes сохраняются между запусками если не использовать `-v`.

---

**Сценарий 3: Порт занят**

Попробуй запустить два раза `docker compose up -d`.

**Ошибка:**
```
Error response from daemon: driver failed programming external connectivity on endpoint: 
Bind for 0.0.0.0:8080 failed: port is already allocated.
```

**Как починить:**
```bash
# Найди что занимает порт
ss -tulnp | grep :8080

# Или останови старый compose
docker compose down
```

---

**Сценарий 4: Переменные не подтягиваются**

Удали `.env` файл и запусти `docker compose up -d`.

**Что увидишь:** Контейнер не стартует или используются дефолтные значения.

**Как починить:** Создай `.env` обратно.

---

## 🎯 Мини-челленджи

### Челлендж 1: Добавь Adminer для управления БД

Добавь в `docker-compose.yml`:

```yaml
  adminer:
    image: adminer:latest
    ports:
      - "8081:8080"
    depends_on:
      - postgres
    networks:
      - backend
```

Открой http://localhost:8081 и подключись к postgres.

---

### Челлендж 2: Масштабируй web

```bash
docker compose up -d --scale web=3
```

Посмотри как Nginx будет балансировать между тремя репликами.

**Подсказка:** Добавь в app.py вывод hostname:
```python
import socket

@app.route('/hostname')
def hostname():
    return jsonify({"hostname": socket.gethostname()})
```

Запрашивай `/hostname` несколько раз и смотри разные hostname'ы.

---

### Челлендж 3: Hot reload для разработки

Добавь bind mount для кода:

```yaml
  web:
    build: ./app
    volumes:
      - ./app:/app  # Изменения в коде сразу видны в контейнере
```

Измени текст в `app.py` и проверь без пересборки образа.

---

## 🛑 Типичные грабли и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| "Connection refused" к базе | База ещё не готова | Добавь healthcheck |
| Volumes не сохраняются | Anonymous volume | Используй named volumes |
| Порт конфликтует | Уже занят | Проверь `ss -tulnp` или измени порт |
| Переменные не работают | Нет .env файла | Создай .env в директории с compose |
| depends_on не работает | Без healthcheck | Добавь condition: service_healthy |
| Контейнеры не видят друг друга | Не в одной сети | Проверь networks |
| Permission denied на volume | Права доступа | Используй chown или правильный USER в Dockerfile |

---

## ✅ Чек-лист качества docker-compose.yml

- [ ] Используются named volumes для данных БД
- [ ] Есть healthcheck для критичных сервисов
- [ ] depends_on с condition: service_healthy
- [ ] Переменные окружения в .env (не в compose)
- [ ] .env в .gitignore
- [ ] Сети разделены (frontend/backend)
- [ ] Порты не конфликтуют
- [ ] Логи доступны через `docker compose logs`
- [ ] Есть restart: unless-stopped для production

---

## 📚 Полезные ссылки

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Compose file reference](https://docs.docker.com/compose/compose-file/)
- [Best practices for writing Compose files](https://docs.docker.com/compose/production/)

---

## 🎓 Что ты теперь умеешь

✅ Запускать мультиконтейнерные приложения одной командой  
✅ Настраивать сети между контейнерами  
✅ Использовать volumes для персистентности  
✅ Работать с переменными окружения  
✅ Настраивать зависимости и healthcheck  
✅ Дебажить типичные проблемы Compose  

**Следующий шаг:** Production best practices и переход к Kubernetes!

---

**Автор:** bashninja  
**Курс:** From Zero to DevOps Hero  
**Telegram:** [@b4shninja](https://t.me/b4shninja)  
**GitHub:** [github.com/b4shninja](https://github.com/b4shninja)
