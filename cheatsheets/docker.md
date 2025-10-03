# Docker — шпаргалка для SRE/DevOps

---

## Установка и версии
**Linux (Debian/Ubuntu):**
```
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")   $(. /etc/os-release; echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
**macOS/Windows:** установите **Docker Desktop**.  
Проверка:
```
docker version
docker info
```

---

## Базовая модель
- **Image** — шаблон ФС + метаданные. Строим: `docker build`. Храним: Registry.  
- **Container** — запущенный (или остановленный) инстанс образа. Запускаем: `docker run`.  
- **Registry** — репозиторий (Docker Hub/Harbor/Artifactory/GHCR).  
- **Network/Volume** — изоляция сети и персистентные данные.

---

## Быстрый старт: Топ‑20 команд
```
# 1) Список образов / контейнеров / сетей / томов
docker images
docker ps            # работающие
docker ps -a         # все
docker network ls
docker volume ls

# 2) Запуск контейнера
docker run --name web -d -p 8080:80 nginx:alpine

# 3) Войти внутрь
docker exec -it web sh            # или bash, если есть

# 4) Логи
docker logs -f --tail=100 web

# 5) Копирование файлов
docker cp file.txt web:/usr/share/nginx/html/
docker cp web:/etc/nginx/nginx.conf ./

# 6) Остановка/старт/удаление
docker stop web && docker rm web
docker rm -f web                  # принудительно

# 7) Построить образ из Dockerfile
docker build -t myapp:1.0 .

# 8) Тег + пуш в реестр
docker tag myapp:1.0 registry.example.com/team/myapp:1.0
docker push registry.example.com/team/myapp:1.0

# 9) Пул образа
docker pull nginx:1.27-alpine

# 10) Инспект (метаданные)
docker inspect web | less

# 11) Статистика ресурсов
docker stats
docker top web

# 12) Сетевой проброс
docker run -d --name api -p 127.0.0.1:9000:8080 myapi:latest

# 13) Переменные окружения и env‑file
docker run -d --env FOO=bar --env-file .env myapp:latest

# 14) Тома
docker volume create mydata
docker run -d -v mydata:/var/lib/postgresql/data postgres:16

# 15) Монтирование каталога (bind)
docker run -d -v $(pwd)/cfg:/app/cfg:ro myapp

# 16) Healthcheck ручной проверкой
docker inspect --format='{{.State.Health.Status}}' web

# 17) Очистка мусора
docker system df
docker system prune -f
docker image prune -f
docker volume prune -f

# 18) Экспорт/импорт контейнера
docker export web > web.tar
cat web.tar | docker import - web:imported

# 19) Сохранить/загрузить образ (tar)
docker save myapp:1.0 > myapp_1.0.tar
docker load < myapp_1.0.tar

# 20) Лимиты ресурсов
docker run -d --cpus=1.5 --memory=512m myapp
```

---

## Частые сценарии

### «Кто держит порт 80?»
```
docker ps --format 'table {{.ID}}	{{.Names}}	{{.Ports}}' | grep ':80->'
```

### Запуск локальной БД (PostgreSQL)
```
docker run -d --name pg -e POSTGRES_PASSWORD=secret -p 5432:5432   -v pgdata:/var/lib/postgresql/data postgres:16
```

### Дебаг сети контейнера
```
docker exec -it web sh
apk add --no-cache curl  # для alpine
curl -v http://127.0.0.1
```

### Подключиться к сети другого контейнера
```
docker network create appnet
docker network connect appnet web
docker network connect appnet api
docker network inspect appnet
```

### Трассировка проблем запуска
```
docker logs -n 200 web
docker inspect --format='{{json .State}}' web | jq
```

---

## Dockerfile — основы (пример)
```Dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3   CMD curl -fsS http://localhost:8080/health || exit 1
CMD ["python","app.py"]
```

### Мультистейдж для Node/Go/Python (пример Node)
```Dockerfile
# build stage
FROM node:22-alpine AS build
WORKDIR /src
COPY package*.json ./
RUN npm ci --omit=dev=false
COPY . .
RUN npm run build

# runtime stage
FROM nginx:alpine
COPY --from=build /src/dist/ /usr/share/nginx/html/
```

### Лучшие практики Dockerfile
- Фиксируйте версии базовых образов: `python:3.12-slim@sha256:...`
- Минимизируйте слои (`RUN` объединять, чистить кеши).  
- `USER` ≠ root.  
- `.dockerignore` обязателен (исключить `.git`, `node_modules`, артефакты).  
- Используйте **multi-stage** для сборки и минимального рантайма.  
- HEALTHCHECK для критичных сервисов.  
- Не храните секреты в образе — используйте env/секрет‑менеджер/BuildKit secrets.

---

## docker compose (v2) — кратко
`docker compose` идёт как плагин. Пример `compose.yaml`:
```yaml
services:
  api:
    image: registry.example.com/team/api:1.0
    ports: ["8080:8080"]
    env_file: .env
    depends_on: [db]
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: secret
volumes:
  pgdata: {}
```
Команды:
```
docker compose up -d
docker compose ps
docker compose logs -f api
docker compose exec api sh
docker compose down -v         # убрать и тома
```

---

## Сети и тома — нюансы
- **Bridge (по умолчанию)**: контейнеры в одной бридж‑сети видят друг друга по имени сервиса.  
- **Host**: без NAT, шарит сеть хоста (Linux‑только).  
- **None**: без сети.  
```
docker network create --driver bridge appnet
docker run -d --network appnet --name a alpine sleep 1d
docker run -d --network appnet --name b alpine sleep 1d
docker exec -it a ping -c1 b
```
- **Volumes** живут вне жизненного цикла контейнера: безопасно пересоздавать контейнер, данные сохранятся.

---

## Безопасность
- Запускайте **под непривилегированным USER**.  
- Чётко ограничивайте ресурсы: `--cpus`, `--memory`, `--pids-limit`.  
- `--read-only` rootfs + tmpfs для временных каталогов:  
```
docker run -d --read-only --tmpfs /tmp --tmpfs /run myapp
```
- Сканируйте образы: `docker scout cves <image>` (или trivy/grype).  
- Подписывайте и проверяйте образы (cosign/notation).  
- Не экспонируйте Docker сокет в контейнер.

---

## Работа с реестрами
```
docker login registry.example.com
docker tag myapp:1.0 registry.example.com/proj/myapp:1.0
docker push registry.example.com/proj/myapp:1.0
docker pull registry.example.com/proj/myapp:1.0
```
Прокси‑кэш и mirroring ускоряют CI.

---

## Диагностика и очистка
```
docker events
docker system df
docker system prune -af --volumes   # опасно, удалит всё неиспользуемое
docker image ls --digests
docker inspect <obj>
docker logs -f <name>
docker exec -it <name> sh
```

---

## BuildKit и buildx
```
export DOCKER_BUILDKIT=1
docker buildx create --use --name mybuilder
docker buildx build --platform linux/amd64,linux/arm64 -t repo/app:1.0 --push .
```
Кеширование:
```
docker buildx build   --cache-from=type=registry,ref=repo/app:cache   --cache-to=type=registry,ref=repo/app:cache,mode=max   -t repo/app:1.0 .
```

---

## Полезные one‑liners
```
# Топ по использованию CPU/Memory контейнерами
docker stats --no-stream | sort -k3 -h

# Удалить висящие образы <none>
docker images -f "dangling=true" -q | xargs -r docker rmi

# Найти контейнер по открытому порту
docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' | grep '0.0.0.0:8080->'

# Все контейнеры с рестарт‑политикой
docker ps -a --format 'table {{.Names}}	{{.Status}}	{{.RunningFor}}	{{.Command}}	{{.Ports}}	{{.ID}}	{{.Label "restart"}}'

# Экспорт переменных из контейнера
docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' <name>
```

---

## Частые вопросы (FAQ)
**Почему контейнер сразу завершается?**  
Команда/процесс завершился. Запускайте «foreground» процесс или `tail -f` для теста.  
**Как автоматически перезапускать сервис?**  
`--restart unless-stopped` или в compose: `restart: unless-stopped`.  
**Как пробросить время/таймзону?**  
`-v /etc/localtime:/etc/localtime:ro -v /etc/timezone:/etc/timezone:ro` (Linux).  
**Где логи?**  
По умолчанию `json-file` драйвер: `docker logs`. Для продакшна используйте `gelf`, `syslog`, `fluentd`, `journald`.  
**Как ограничить диск?**  
`--storage-opt` зависит от драйвера. Лучше собирать минимальные образы и чистить кеши.

---

## .dockerignore (минимум)
```
.git
.gitignore
node_modules
__pycache__/
*.pyc
dist
build
.env
*.log
```
---

