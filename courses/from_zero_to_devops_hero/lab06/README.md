# Lab-06: Свой первый Dockerfile — кэш, размер и отладка

> S02E02. Задача — написать **рабочий Dockerfile** для мини‑веб‑сервиса, понять **как работает кэш слоёв**, и **сжать образ** с помощью multi‑stage. Всё — простыми шагами.

## Что будет в конце
- Запускается контейнер с нашим веб‑сервисом.
- Ты понимаешь, почему порядок инструкций влияет на скорость сборки.
- Размер образа стал меньше, а старт — быстрее.
- Есть чек‑лист: что проверить, если «не собирается/не стартует».

---

## Требования
- Ubuntu‑машина с Docker (см. lab05) и доступом в интернет.
- 30–60 минут.

---

## Структура каталога (предложение)
```
courses/from_zero_to_devops_hero/lab06/
├─ app/
│  ├─ app.py
│  ├─ requirements.txt
├─ Dockerfile           # «наивная» версия (базовая)
├─ Dockerfile.cache     # версия с кэшем слоёв
├─ Dockerfile.multi     # multi-stage, меньше размер
├─ .dockerignore
└─ README.md            # этот файл
```

> Папку можешь назвать как удобно. В примерах ниже я исхожу из `lab06/` как корня.

---

## Шаг 0. Мини‑приложение (Flask)

Создай папку `app/` и положи туда два файла:

**`app/requirements.txt`**
```
flask==3.0.3
gunicorn==22.0.0
```

**`app/app.py`**
```python
from flask import Flask, jsonify
import os

PORT = int(os.environ.get("PORT", "8080"))

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify(ok=True, msg="hello from container")

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    # dev‑режим (в проде будем запускать через gunicorn)
    app.run(host="0.0.0.0", port=PORT)
```

Быстрая локальная проверка (необязательно):
```bash
# только чтобы убедиться, что код жив
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
python app/app.py
# в другом окне: curl -s http://127.0.0.1:8080/ | jq .
deactivate && rm -rf .venv
```

---

## Шаг 1. Базовый Dockerfile (наивный)

**`Dockerfile`**
```Dockerfile
FROM python:3.12-slim

WORKDIR /app
# Кладём ВСЁ сразу (это намеренно «наивно» — чтобы увидеть эффект на кэше)
COPY . /app

# Установка зависимостей (будет сбрасываться при любой правке кода)
RUN pip install --no-cache-dir -r app/requirements.txt

# Открываем порт и команда запуска
EXPOSE 8080
CMD ["python", "app/app.py"]
```

Сборка и запуск:
```bash
# из корня lab06/
docker build -t lab06:naive .
docker run -d --name lab06_naive -p 8080:8080 lab06:naive

curl -I http://127.0.0.1:8080/    # ждём 200 OK
docker logs -n 20 lab06_naive
docker image ls | grep lab06
```

Остановить и убрать:
```bash
docker rm -f lab06_naive
```

**Что заметить:** любая правка в `app/app.py` ломает кэш и заново ставит зависимости. Долго и шумно.

---

## Шаг 2. Ускоряем сборку кэшем слоёв

**Идея:** сначала копируем **манифесты зависимостей**, ставим их, а уже потом кладём остальной код. Тогда при мелких правках кода слои с зависимостями останутся в кэше.

**`.dockerignore`** (в корне lab06):
```
.venv
__pycache__
*.pyc
.git
node_modules
dist
build
.DS_Store
```

**`Dockerfile.cache`**
```Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 1) Только манифесты зависимостей
COPY app/requirements.txt /app/app/requirements.txt

# 2) Ставим зависимости (слой хорошо кэшируется)
RUN pip install --no-cache-dir -r /app/app/requirements.txt

# 3) Теперь кладём остальной код
COPY app /app/app

EXPOSE 8080
# Используем gunicorn как «более продовый» сервер
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app.app:app"]
```

**Замеряем эффект кэша:**

1) «Холодная» сборка (без кэша)
```bash
docker builder prune -af   # очистить кэш сборки (необязательно, но наглядно)
/usr/bin/time -f "build=%E size(KB)=%k" docker build -f Dockerfile.cache -t lab06:cache .
```

2) Правим одну строку в `app/app.py`, например текст ответа. И снова:
```bash
/usr/bin/time -f "build=%E size(KB)=%k" docker build -f Dockerfile.cache -t lab06:cache .
```
**Ожидаем:** вторая сборка заметно быстрее — зависимости взялись из кэша.

Запуск для проверки:
```bash
docker run -d --name lab06_cache -p 8080:8080 lab06:cache
curl -s http://127.0.0.1:8080/ | jq .
docker rm -f lab06_cache
```

---

## Шаг 3. Делаем образ меньше (multi‑stage)

**Идея:** в «builder» ставим всё, что нужно для сборки, а в «runtime» берём только готовые файлы и минимум утилит.

**`Dockerfile.multi`**
```Dockerfile
### Stage 1: builder — собираем зависимости в отдельную «виртуальную среду»
FROM python:3.12-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir -r /build/requirements.txt

COPY app /build/app

### Stage 2: runtime — лёгкий рантайм
FROM python:3.12-slim AS runtime

# Не root, меньше рисков
RUN useradd -m appuser
USER appuser

WORKDIR /app
# Подсовываем готовую виртуальную среду и код
COPY --from=builder /opt/venv /app/venv
COPY --from=builder /build/app /app/app

ENV PATH="/app/venv/bin:$PATH"
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app.app:app"]
```

Сборка и сравнение размеров:
```bash
docker build -f Dockerfile.multi -t lab06:multi .
docker image ls | grep lab06
docker history lab06:multi
```

Обычно `:multi` получается **меньше** и стартует быстрее, чем «наивный» `:naive`.

Запуск:
```bash
docker run -d --name lab06_multi -p 8080:8080 lab06:multi
curl -s http://127.0.0.1:8080/ | jq .
docker rm -f lab06_multi
```

---

## Шаг 4. Частые ошибки и быстрые проверки

- «**Файл не найден при COPY**» — путь считается от **контекста сборки** (папка, где запускаешь `docker build`).  
- «**Команда не находится**» — ставили её в builder‑стейдже, а запускаете в runtime; в runtime её нет.  
- «**Сервис не отвечает**» — слушает `127.0.0.1`, а не `0.0.0.0`; проверь `EXPOSE` и проброс порта.  
- «**Образ раздулся**» — не хватает `.dockerignore`, кеши пакетов, тяжёлая база; проверь `docker history`.  
- «**Permission denied к Docker**» — нет группы `docker` в сессии; перезайди/`newgrp docker`.  
- «**Port already in use**» — кто-то держит порт на хосте: `ss -tulnp | grep :8080`.

---

## Шаг 5. Чистка
```bash
docker rm -f lab06_naive lab06_cache lab06_multi 2>/dev/null || true
docker image prune -f
docker builder prune -f
```

---

## Что сдать в репозиторий
В `courses/from_zero_to_devops_hero/lab06/`:
- `app/app.py`, `app/requirements.txt`
- `Dockerfile`, `Dockerfile.cache`, `Dockerfile.multi`
- `.dockerignore`
- `notes.md` — **3–10 строк**: время сборки «до/после», размеры образов, что сломалось и как чинил.

**Мини‑шаблон `notes.md`:**
```
Время сборки (первый/второй раз):
- Dockerfile.cache: 00:45 / 00:08

Размеры:
- lab06:naive  133 MB
- lab06:cache  133 MB
- lab06:multi  136 MB   ← почему больше? см. ниже

Пояснение по размеру:
- В multi я копировал venv из builder → дублирование библиотек.
- Оба стейджа на python:3.12-slim, поэтому выгоды нет.
- После перехода на схему “wheels в builder → pip install в runtime” размер уменьшился до: ___ MB.

Баги и решения:
- container exited (код 3) — забыл слушать 0.0.0.0 → поправил CMD/порт
- порт 8080 занят — сменил на 8081
```
```
Почему multi-stage может быть больше:
— Мы копируем целую venv → дублируем часть стандартной библиотеки Python.
— Оба стейджа на python:3.12-slim → база одинаковая, профит маленький.
— Слои “не ноль”: useradd, ENV и пр. добавляют мегабайты.

Как уменьшить:
— В builder собирать wheels и ставить их в runtime (без venv).
— Держать .dockerignore в порядке.
— Проверять docker history и удалять лишнее.

```
