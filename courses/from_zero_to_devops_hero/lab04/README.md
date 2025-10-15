# Lab-04: Мини‑сервис локально — веб + база, и как чинить типовые сетевые ошибки

## Зачем эта лаба
А если вот такая ситуейшен: один сервис говорит с другим, и вдруг «не стучится».  
Здесь соберём маленький стенд **без Docker**: `nginx` (веб-прокси) → `flask` (бэкенд на 5000) → `PostgreSQL` (база).  
А потом специально **сломаем** по одному симптому и починим.

## Что понадобится
- ВМ из lab01 (Ubuntu Server LTS) + права sudo.
- Пройдены lab02 и lab03 (процессы, systemctl, сеть).
- 60–90 минут.

## Что соберём
```
client (curl/браузер)
   ↓
nginx :80  → proxy_pass /api → 127.0.0.1:5000 (flask)
                         ↘   подключение к 127.0.0.1:5432 (PostgreSQL)
```

---

## Шаг 0. Подготовка
```bash
sudo apt update
sudo apt install -y nginx python3-venv python3-pip postgresql postgresql-contrib
```

Папки проекта:
```bash
mkdir -p ~/miniapp && cd ~/miniapp
mkdir -p logs
python3 -m venv .venv
source .venv/bin/activate
pip install flask psycopg2-binary
```

---

## Шаг 1. Настраиваем PostgreSQL

Создадим БД и пользователя:
```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE miniuser WITH LOGIN PASSWORD 'minipass';
CREATE DATABASE minidb OWNER miniuser;
GRANT ALL PRIVILEGES ON DATABASE minidb TO miniuser;
SQL
```

Проверка входа:
```bash
psql "postgresql://miniuser:minipass@127.0.0.1:5432/minidb" -c "select now();"
```

**Важно (по умолчанию ок):** в `/etc/postgresql/*/main/postgresql.conf` параметр `listen_addresses = 'localhost'`,  
в `/etc/postgresql/*/main/pg_hba.conf` есть правило `local/all` и `host  all  all  127.0.0.1/32  md5`.

Перезапуск, если меняли конфиг:
```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql --no-pager -l
```

---

## Шаг 2. Мини‑бэкенд на Flask (порт 5000)

Создадим `app.py`:
```bash
cat > ~/miniapp/app.py <<'PY'
from flask import Flask, jsonify
import os, psycopg2

DB_DSN = os.environ.get("DB_DSN", "postgresql://miniuser:minipass@127.0.0.1:5432/minidb")

app = Flask(__name__)

@app.route("/api/health")
def health():
    return jsonify(ok=True)

@app.route("/api/time")
def time():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    cur.execute("select now();")
    ts = cur.fetchone()[0]
    cur.close(); conn.close()
    return jsonify(time=str(ts))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
PY
```

Запуск в отдельном терминале:
```bash
cd ~/miniapp && source .venv/bin/activate
python app.py
# В другом терминале:
curl http://127.0.0.1:5000/api/health
```

> Остановить: `Ctrl+C` в окне с Flask.



**Опционально: systemd‑сервис**, чтобы бэкенд жил сам:
```bash
USER_NAME="$(whoami)"   # если другой пользователь — подставь вручную
sudo tee /etc/systemd/system/miniapp.service >/dev/null <<UNIT
[Unit]
Description=Mini Flask App (system unit)
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=/home/${USER_NAME}/miniapp
Environment=DB_DSN=postgresql://miniuser:minipass@127.0.0.1:5432/minidb
ExecStart=/home/${USER_NAME}/miniapp/.venv/bin/python /home/${USER_NAME}/miniapp/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT
```
```
# Включаем под текущим пользователем:
sudo systemctl enable miniapp.service
sudo systemctl start miniapp.service
sudo systemctl status miniapp.service --no-pager -l
```

(Если сервис отказывается стартовать — смотри `journalctl -u miniapp -f`.)

---

## Шаг 3. Настраиваем nginx как обратный прокси

Статическая страничка:
```bash
sudo bash -c 'cat > /var/www/html/index.html <<HTML
<!doctype html><html><body style="font-family:sans-serif">
<h1>miniapp</h1>
<p>Проверь API: <code>/api/health</code> и <code>/api/time</code></p>
</body></html>
HTML'
```

Конфиг сайта:
```bash
sudo tee /etc/nginx/sites-available/miniapp >/dev/null <<'NGINX'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/miniapp /etc/nginx/sites-enabled/miniapp
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl status nginx --no-pager -l
```

Проверка:
```bash
curl -I http://127.0.0.1/
curl    http://127.0.0.1/api/health
curl    http://127.0.0.1/api/time
```

---

## Шаг 4. Ломаем и чиним (типовые сетевые ошибки)

### 4.1 Бэкенд умер
**Симптом:** `/api/*` даёт 502/Bad Gateway.  
**Проверка:** `systemctl status miniapp` или процесс `python app.py` не запущен.  
**Чиним:** запусти бэкенд, смотри `journalctl -u miniapp -n 50`.

### 4.2 Бэкенд слушает не тот адрес
**Симптом:** nginx «Bad Gateway», а `curl 127.0.0.1:5000` — работает только локально/или наоборот.  
**Проверка:** `ss -tulnp | grep :5000` — слушает ли `127.0.0.1:5000`.  
**Чиним:** в `app.py` `host="127.0.0.1"`; прокси указывает `127.0.0.1`. Адреса должны совпасть.

### 4.3 Неправильные учётки БД
**Симптом:** `/api/time` отдаёт 500, в логах — auth failed.  
**Проверка:** `journalctl -u miniapp -n 100` и логи PostgreSQL.  
**Чиним:** проверь DSN, пароль пользователя, `psql` локально теми же данными.

### 4.4 БД не слушает TCP
**Симптом:** «connection refused» к 127.0.0.1:5432.  
**Проверка:** `ss -tulnp | grep :5432`.  
**Чиним:** `sudo systemctl start postgresql`; в `postgresql.conf` `listen_addresses='localhost'`; в `pg_hba.conf` есть `127.0.0.1/32 md5`; `sudo systemctl restart postgresql`.

### 4.5 UFW блокирует порт
**Симптом:** не достучаться с другой машины.  
**Проверка:** `sudo ufw status`.  
**Чиним:** `sudo ufw allow 80/tcp`. (Внутренние соединения localhost обычно не блокируются.)

### 4.6 Nginx не перезагрузился после правки
**Симптом:** конфиг изменили, а поведения нет.  
**Проверка:** `sudo nginx -t`.  
**Чиним:** `sudo systemctl reload nginx`.

---

## Шаг 5. Итоговая проверка
```bash
# Домашняя машина → ВМ (если проброшен порт/локальная сеть)
curl -I http://<IP_VM>/
curl    http://<IP_VM>/api/health
curl    http://<IP_VM>/api/time
```

Ожидаем: `200 OK` и JSON c временем.

---

## Чек‑лист
- [ ] `nginx` обслуживает `/` и проксирует `/api/*` на 127.0.0.1:5000.  
- [ ] `miniapp` работает как процесс/сервис.  
- [ ] PostgreSQL принимает локальные соединения, создан пользователь/БД.  
- [ ] `curl /api/time` возвращает время из БД.  
- [ ] Понимаю 6 типовых ошибок и как их диагностировать.

---

## Полезно
- Логи: `journalctl -u nginx -n 50`, `journalctl -u miniapp -n 50`, `/var/log/postgresql/*.log` (путь может отличаться).  
- Нагрузочный тест по‑простому: `ab -n 100 -c 10 http://127.0.0.1/api/health` (пакет `apache2-utils`).

---

## Уборка (по желанию)
```bash
sudo systemctl disable --now miniapp || true
sudo rm -f /etc/systemd/system/miniapp.service
sudo systemctl daemon-reload
sudo rm -f /etc/nginx/sites-enabled/miniapp /etc/nginx/sites-available/miniapp
sudo systemctl restart nginx

sudo -u postgres dropdb minidb
sudo -u postgres dropuser miniuser

rm -rf ~/miniapp
```
