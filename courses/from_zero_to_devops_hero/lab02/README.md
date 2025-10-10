# Lab-02: Практика Linux — процессы, права, пакеты, сервисы и логи

## Зачем эта лаба
Вот как это работает: когда сервис не запускается, ты не гадаешь.  
Ты смотришь процессы, права, пакеты, статус сервиса и логи.  
Эта лаба закрепляет базу, которая нужна джуну каждый день.

## Что понадобится
- Домашняя лаборатория из lab01 (VM с Ubuntu Server LTS).
- Доступ по SSH к VM (user: `student`, как в lab01).
- 20–40 минут времени.

Подсказка: если VM «поплыла», откати снапшот `clean-base` из lab01.

---

## Что делаем в lab02
1. Разбираемся с процессами и портами.
2. Тренируем права и владельцев.
3. Работаем с пакетами через `apt`.
4. Управляем сервисом через `systemd`.
5. Ищем правду в логах: `journalctl` и `/var/log`.

Каждый блок: задача → команды → как себя проверить.

---

## 1) Процессы и порты

**Задача:** найти, кто слушает порт, и аккуратно остановить лишний процесс.

Команды:
```bash
# Все процессы «снимком»
ps aux | head

# Текущее потребление ресурсов (выход из top: q)
top

# Дерево процессов (если нет — поставим psmisc)
sudo apt update && sudo apt install -y psmisc  # Пакет psmisc содержит pstree на Ubuntu
pstree -p | head

# Кто слушает порты (tcp/udp)
ss -tulnp | head  # На Ubuntu это стандартная команда (вместо старого netstat)

# Пример: найти, кто слушает 80-й порт
sudo ss -tulnp | grep ':80' || echo 'Никто не слушает 80'
```

Проверь себя:
- Видишь хотя бы один процесс в `ps aux`.
- Понимаешь, какой процесс «родитель», а какой «дочерний» (по `pstree`).
- Можешь назвать PID процесса, который держит порт.

Если нужно «убить» зависший процесс:
```bash
# Мягко
sudo kill <PID>

# Если не помогло (последний аргумент)
sudo kill -9 <PID>
```

---

## 2) Права и владельцы

**Задача:** создать файл-скрипт, выдать права на запуск, поменять владельца.

Команды:
```bash
# Песочница
mkdir -p ~/playground && cd ~/playground

# Простой скрипт
cat > hello.sh <<'EOF'
#!/usr/bin/env bash
echo "Hello from lab02"
EOF

# Посмотреть права и владельца
ls -l hello.sh

# Сделать исполняемым
chmod +x hello.sh
ls -l hello.sh

# Запустить
./hello.sh

# Поменять владельца на текущего пользователя и группу (пример)
sudo chown "$(whoami)":"$(id -gn)" hello.sh
ls -l hello.sh
```

Проверь себя:
- Без `chmod +x` скрипт не запускается (будет Permission denied).
- После `chmod +x` скрипт запускается.
- Понимаешь, что показывают поля `-rwxr-xr-x` в `ls -l`.

Не делай `chmod 777`. Это плохая привычка. Давай только нужные права.

---

## 3) Пакеты: установка и удаление

**Задача:** поставить `nginx`, посмотреть информацию о пакете и удалить его без конфигов и с конфигами.

Команды:
```bash
# Обновить индексы пакетов
sudo apt update

# Найти пакет
apt search nginx | head

# Посмотреть описание пакета
apt show nginx | sed -n '1,20p'

# Установить
sudo apt install -y nginx
```

Проверь себя:
```bash
# Файл юнита сервиса должен появиться
systemctl status nginx | head

# Порт 80 должен слушаться
sudo ss -tulnp | grep ':80' || echo '80-й порт пока не слушается'
```

Удаление:
```bash
# Удалить бинарники, оставить конфиги
sudo apt remove -y nginx

# Полное удаление с конфигами
sudo apt purge -y nginx

# Чистка хвостов
sudo apt autoremove -y
```

---

## 4) Сервисы (systemd): запуск, автозапуск, статус

**Задача:** поставить `nginx`, включить автозапуск, перезапустить, посмотреть статус.

Команды:
```bash
sudo apt update && sudo apt install -y nginx

# Статус
sudo systemctl status nginx | sed -n '1,12p'

# Запуск/остановка/перезапуск
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx

# Автозапуск
sudo systemctl enable nginx
sudo systemctl disable nginx
```

Проверь себя:
```bash
# Наличие процесса
ps aux | grep [n]ginx

# Порт
sudo ss -tulnp | grep ':80' || echo '80-й порт не слушается'

# Страница по HTTP c самой VM
curl -I http://127.0.0.1 | head -n 1
```

Если порт 80 занят, найди «виновника»:
```bash
sudo ss -tulnp | grep ':80' || true
```

---

## 5) Логи на Ubuntu: journalctl и /var/log/syslog

На Ubuntu главный источник правды — systemd-журнал. Его читает команда `journalctl`.  
Файл `/var/log/syslog` тоже часто есть (через rsyslog), но не всегда. Делаем так:

### Универсально (рекомендуется)
```bash
# Последние 50 строк общего журнала
sudo journalctl -n 50 --no-pager

# Логи конкретного сервиса (пример: nginx)
sudo journalctl -u nginx -n 50 --no-pager

# Онлайн-хвост логов сервиса (выход: Ctrl+C)
sudo journalctl -u nginx -f

# Логи с момента последней загрузки
sudo journalctl -b -n 200 --no-pager

# Сообщения ядра (полезно при сетевых/дисковых проблемах)
sudo journalctl -k -n 50 --no-pager
```

Проверь себя:
- Видишь свежие записи без ошибок в `journalctl -u nginx -n 50`.
- При `-f` видишь новые строки, когда делаешь запросы к nginx.

### Если нужен именно файл syslog
На многих установках Ubuntu есть `/var/log/syslog`. Просто посмотри его напрямую:
```bash
sudo tail -n 50 /var/log/syslog
```

Если файла нет — значит rsyslog не установлен. Его можно добавить (по желанию):
```bash
sudo apt update && sudo apt install -y rsyslog
sudo systemctl enable --now rsyslog
# После этого появится /var/log/syslog
sudo tail -n 50 /var/log/syslog
```

Итог:
- Для диагностики хватит `journalctl` — он есть «из коробки».
- `/var/log/syslog` — опционально. Удобен, если любишь классические текстовые логи.
---

## Мини-кейс: «сломай и почини»

**Задача:** сделать ошибку в конфиге nginx и починить её.

Шаги:
```bash
# Сделаем бэкап и внесём ошибку
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
echo "}" | sudo tee -a /etc/nginx/nginx.conf

# Проверка конфигурации
sudo nginx -t || echo 'Конфиг сломан — хорошо, это то, что нам нужно для тренировки'

# Попробуем перезапустить (должен упасть)
sudo systemctl restart nginx || echo 'Перезапуск не удался — ищем причину'

# Логи подскажут
sudo journalctl -u nginx -n 30 --no-pager
sudo tail -n 30 /var/log/nginx/error.log 2>/dev/null || true

# Откат
sudo mv /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
sudo nginx -t && sudo systemctl restart nginx
```

Проверь себя:
- `nginx -t` ругался, потом перестал.
- Сервис перезапустился, порт 80 слушается.
- В логах видны понятные ошибки и «зелёный» запуск после фикса.

---

## Итоговый чек-лист lab02

- [ ] Умею найти процесс и его PID (`ps`, `top`, `pstree`).  
- [ ] Понимаю, кто держит порт (`ss -tulnp`).  
- [ ] Управляю правами и владельцами (`chmod`, `chown`), не ставлю `777`.  
- [ ] Ставлю и удаляю пакеты (`apt install/remove/purge`, `apt show`).  
- [ ] Управляю сервисами (`systemctl status/start/enable`).  
- [ ] Читаю логи (`journalctl`, `/var/log/*`, `tail -f`).  
- [ ] Сломал конфиг nginx → нашёл ошибку в логах → починил.

---

## Как оформить результат в репозитории

Создай папку `lab02` рядом с `lab01`:

```
courses/from_zero_to_devops_hero/lab02/
├─ README.md              # этот файл с твоими пометками
├─ notes.md               # короткие заметки: что понравилось, что не понял
```
Пиши вопросы и общайся с другими в комментариях к статье на [dzen.ru/devops](https://dzen.ru/devops) или в нашем уютном телеграмм чате - [t.me/dev0pschat](https://t.me/dev0pschat)


В `README.md` добавь:
- команды, которые ты запускал;
- 2–3 строки «что было новым»;


---

## Типичные проблемы и короткие решения

- **Нет сети в VM.**  
  Проверь NAT. Посмотри `ip a`. Пингуй `8.8.8.8`. Если пингуется IP, но не домены — это DNS.
Проверь резолв: `resolvectl status`.
Перезапусти резолвер: `sudo systemctl restart systemd-resolved`.
Если используешь NetworkManager — `nmcli general status` и перезапусти сеть через GUI/`nmcli`.

- **Порт 80 занят.**  
  `sudo ss -tulnp | grep ':80'` → найди PID → `ps aux | grep <PID>` → решай: остановить или сменить порт.

- **Сервис не стартует.**  
  `sudo systemctl status <service>` → `sudo journalctl -u <service> -n 50`.  
  Часто причина: опечатка в конфиге или нехватка прав.

- **Permission denied при запуске скрипта.**  
  Выдай `chmod +x script.sh`. Проверь владельца `ls -l`.  
  Если скрипт в системном пути — запускай через `sudo` только когда это действительно нужно.

---

## Что дальше
Следующая лаба — **lab03 (сеть)**: IP, DNS, `ping`, `curl`, открытые порты и поиск «почему не стучится до базы».  
А в сериале это будет **S01E09**.

Это может помочь так : делаешь lab02 → закрепляешь мышечную память → на собесе уверенно отвечаешь и не паникуешь на инцидентах.
