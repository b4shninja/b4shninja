# 🚀 Quick Start Guide

## Задание 1: Простой веб + PostgreSQL

```bash
# 1. Перейди в директорию
cd examples/task1

# 2. Запусти
docker compose up -d

# 3. Проверь статус
docker compose ps

# 4. Посмотри логи
docker compose logs -f

# 5. Открой в браузере
curl http://localhost:5000

# 6. Останови
docker compose down
```

---

## Задание 2: Полный стек (Nginx + Flask + PostgreSQL + Redis)

```bash
# 1. Перейди в директорию
cd examples/task2

# 2. Создай .env файл
cp .env.example .env

# 3. Запусти всё
docker compose up -d --build

# 4. Проверь статус
docker compose ps

# Должно быть 4 контейнера в состоянии "Up":
# - lab07_nginx
# - lab07_web
# - lab07_postgres
# - lab07_redis

# 5. Тестируй API
curl http://localhost:8080/
curl http://localhost:8080/db
curl http://localhost:8080/cache
curl http://localhost:8080/health

# 6. Посмотри как растёт счётчик Redis
for i in {1..5}; do curl http://localhost:8080/cache; echo; done

# 7. Посмотри логи
docker compose logs -f web

# 8. Зайди в контейнер
docker compose exec web bash

# Внутри контейнера:
python --version
pip list
exit

# 9. Перезапусти один сервис
docker compose restart web

# 10. Останови всё
docker compose down

# 11. Останови и удали volumes (потеряешь данные БД!)
docker compose down -v
```

---

## Полезные команды для отладки

### Проверка сетей

```bash
# Список сетей
docker network ls

# Инспектирование сети
docker network inspect lab07_backend
docker network inspect lab07_frontend
```

### Проверка volumes

```bash
# Список volumes
docker volume ls

# Инспектирование volume
docker volume inspect lab07_pgdata

# Удаление неиспользуемых volumes
docker volume prune
```

### Логи

```bash
# Все логи
docker compose logs

# Логи конкретного сервиса
docker compose logs web

# Следить за логами в реальном времени
docker compose logs -f

# Последние 50 строк
docker compose logs --tail=50

# С временными метками
docker compose logs -t
```

### Выполнение команд в контейнере

```bash
# Bash
docker compose exec web bash

# Одна команда
docker compose exec postgres psql -U postgres -d appdb

# Redis CLI
docker compose exec redis redis-cli
```

### Мониторинг ресурсов

```bash
# Использование CPU/RAM контейнерами
docker stats

# Или только для compose проекта
docker compose top
```

---

## Тестирование масштабирования

```bash
# Запусти 3 реплики web
docker compose up -d --scale web=3

# Проверь что nginx балансирует
for i in {1..10}; do 
  curl -s http://localhost:8080/hostname | jq .hostname
done

# Ты увидишь разные hostname'ы!
```

---

## Troubleshooting

### Порт занят

```bash
# Узнай кто занимает порт
ss -tulnp | grep :8080

# Или
lsof -i :8080

# Останови конфликтующий контейнер
docker compose down
```

### База не подключается

```bash
# Проверь что postgres жив
docker compose exec postgres pg_isready -U postgres

# Посмотри логи postgres
docker compose logs postgres

# Подключись к БД вручную
docker compose exec postgres psql -U postgres -d appdb
```

### Redis не работает

```bash
# Проверь Redis
docker compose exec redis redis-cli ping
# Должно вернуть: PONG

# Посмотри ключи
docker compose exec redis redis-cli keys '*'

# Посмотри счётчик
docker compose exec redis redis-cli get visit_count
```

### Контейнеры не видят друг друга

```bash
# Проверь что контейнеры в одной сети
docker network inspect lab07_backend

# Проверь DNS резолвинг
docker compose exec web ping -c 2 postgres
docker compose exec web ping -c 2 redis
```

---

## Очистка после работы

```bash
# Остановить и удалить контейнеры
docker compose down

# Остановить и удалить контейнеры + volumes
docker compose down -v

# Удалить образы
docker rmi lab07-task2-web

# Полная очистка всего Docker (ОПАСНО!)
docker system prune -a --volumes
```

---

## 🎯 Следующие шаги

После того как разберёшься с Docker Compose:

1. **Production practices** — security, logging, monitoring
2. **Docker Swarm** — оркестрация в кластере
3. **Kubernetes** — следующий уровень оркестрации

Удачи! 🚀
