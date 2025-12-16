# 📋 Docker Compose Cheat Sheet

## Основные команды

### Запуск и остановка

```bash
# Запустить все сервисы
docker compose up

# Запустить в фоне (detached mode)
docker compose up -d

# Пересобрать образы и запустить
docker compose up -d --build

# Запустить только определенные сервисы
docker compose up web postgres

# Остановить все сервисы
docker compose stop

# Остановить и удалить контейнеры
docker compose down

# Остановить и удалить контейнеры + volumes
docker compose down -v

# Остановить и удалить контейнеры + volumes + образы
docker compose down -v --rmi all

# Перезапустить сервисы
docker compose restart

# Перезапустить конкретный сервис
docker compose restart web
```

---

## Логи и мониторинг

```bash
# Посмотреть логи всех сервисов
docker compose logs

# Следить за логами в реальном времени
docker compose logs -f

# Логи конкретного сервиса
docker compose logs web
docker compose logs -f postgres

# Последние N строк
docker compose logs --tail=100

# С временными метками
docker compose logs -t

# Статус сервисов
docker compose ps

# Подробная информация
docker compose ps -a

# Процессы в контейнерах
docker compose top

# Статистика ресурсов
docker stats $(docker compose ps -q)
```

---

## Выполнение команд

```bash
# Зайти в контейнер (bash)
docker compose exec web bash

# Зайти в контейнер (sh для alpine)
docker compose exec web sh

# Выполнить команду без входа
docker compose exec web ls -la /app

# Выполнить команду от другого пользователя
docker compose exec -u root web apt update

# Подключиться к PostgreSQL
docker compose exec postgres psql -U postgres -d mydb

# Подключиться к Redis
docker compose exec redis redis-cli

# Запустить Python в контейнере
docker compose exec web python

# Посмотреть переменные окружения
docker compose exec web env
```

---

## Билд и образы

```bash
# Собрать образы
docker compose build

# Собрать без кэша
docker compose build --no-cache

# Собрать конкретный сервис
docker compose build web

# Собрать с параллелизмом
docker compose build --parallel

# Показать образы
docker compose images

# Удалить образы
docker compose down --rmi all
```

---

## Масштабирование

```bash
# Запустить N реплик сервиса
docker compose up -d --scale web=3

# Проверить
docker compose ps

# Вернуть к одной реплике
docker compose up -d --scale web=1
```

---

## Работа с volumes

```bash
# Список volumes
docker volume ls

# Инспектирование volume
docker volume inspect myproject_pgdata

# Удалить неиспользуемые volumes
docker volume prune

# Удалить конкретный volume
docker volume rm myproject_pgdata

# Backup volume
docker run --rm \
  -v myproject_pgdata:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/pgdata-backup.tar.gz /data

# Restore volume
docker run --rm \
  -v myproject_pgdata:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/pgdata-backup.tar.gz -C /
```

---

## Работа с сетями

```bash
# Список сетей
docker network ls

# Инспектирование сети
docker network inspect myproject_backend

# Удалить неиспользуемые сети
docker network prune

# Подключить контейнер к сети
docker network connect myproject_backend some-container

# Отключить контейнер от сети
docker network disconnect myproject_backend some-container
```

---

## Валидация и дебаг

```bash
# Проверить синтаксис docker-compose.yml
docker compose config

# Проверить и показать итоговый конфиг
docker compose config --services

# Показать порты
docker compose port web 5000

# Показать переменные окружения
docker compose config | grep environment -A 10

# Проверить что будет создано
docker compose config --quiet

# Показать зависимости
docker compose config --services
```

---

## Очистка

```bash
# Остановить все контейнеры
docker compose down

# Удалить volumes
docker compose down -v

# Удалить образы
docker compose down --rmi all

# Полная очистка проекта
docker compose down -v --rmi all --remove-orphans

# Очистить всё в Docker (все проекты!)
docker system prune -a --volumes
```

---

## Переменные окружения

```bash
# Использовать другой .env файл
docker compose --env-file .env.production up -d

# Переопределить переменную
DB_PASSWORD=newsecret docker compose up -d

# Посмотреть итоговые переменные
docker compose config
```

---

## Работа с несколькими файлами

```bash
# Использовать несколько compose файлов
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Базовый + оверрайд
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

---

## Профили (Docker Compose v2.x)

```yaml
# docker-compose.yml
services:
  web:
    image: nginx
    profiles: ["frontend"]
  
  db:
    image: postgres
    profiles: ["backend"]
```

```bash
# Запустить только frontend
docker compose --profile frontend up -d

# Запустить frontend + backend
docker compose --profile frontend --profile backend up -d
```

---

## Полезные однострочники

```bash
# Перезапустить один сервис без downtime других
docker compose up -d --no-deps --build web

# Посмотреть IP адреса контейнеров
docker compose ps -q | xargs docker inspect --format='{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Количество запущенных контейнеров
docker compose ps | grep Up | wc -l

# Удалить все stopped контейнеры
docker compose ps -a | grep Exited | awk '{print $1}' | xargs docker rm

# Посмотреть размер volumes
docker system df -v | grep myproject

# Следить за логами нескольких сервисов
docker compose logs -f web postgres redis
```

---

## Troubleshooting

```bash
# Проверить здоровье контейнера
docker compose ps
docker inspect --format='{{.State.Health.Status}}' container_name

# Проверить DNS резолвинг между контейнерами
docker compose exec web ping postgres

# Проверить что порт слушается
docker compose exec web netstat -tulnp

# Проверить переменные окружения в контейнере
docker compose exec web printenv

# Проверить подключение к БД
docker compose exec postgres pg_isready -U postgres

# Проверить подключение к Redis
docker compose exec redis redis-cli ping

# Посмотреть процессы внутри контейнера
docker compose exec web ps aux

# Статистика I/O
docker compose exec web iostat
```

---

## Мониторинг в реальном времени

```bash
# CPU и память всех контейнеров
watch -n 1 'docker stats --no-stream $(docker compose ps -q)'

# Логи с фильтром
docker compose logs -f | grep ERROR

# Количество запросов к веб-сервису
docker compose logs web | grep GET | wc -l
```

---

## Шпаргалка по docker-compose.yml

### Минимальный файл
```yaml
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```

### Со всеми опциями
```yaml
version: '3.8'

services:
  web:
    build:
      context: ./app
      dockerfile: Dockerfile
      args:
        VERSION: "1.0"
    image: myapp:latest
    container_name: myapp_web
    hostname: web-server
    ports:
      - "8080:80"
    expose:
      - "3000"
    environment:
      - ENV=production
      - DEBUG=false
    env_file:
      - .env
    volumes:
      - ./app:/app
      - data:/data
    networks:
      - frontend
      - backend
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`example.com`)"

volumes:
  data:

networks:
  frontend:
  backend:
```

---

Сохрани эту шпаргалку и используй при работе с Docker Compose! 🚀
