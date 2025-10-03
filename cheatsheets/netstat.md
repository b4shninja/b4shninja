# Netstat — шпаргалка для SRE/DevOps

> Быстрые команды, типовые разборы, фильтры и эквиваленты на `ss`.

## Что это и когда применять
`netstat` — инструмент из пакета **net-tools** для просмотра сетевых соединений, слушающих портов, статистики протоколов и маршрутов. Полезен для:
- поиска «кто слушает порт?» и «что заняло порт»;
- диагностики зависших/массовых TCP-соединений (SYN_SENT, TIME_WAIT);
- быстрой сетевой телеметрии на хосте (Rx/Tx, ошибки);
- экспресс-аудита открытых портов.

> ℹ️ На современных Linux дистрибутивах рекомендуется **`ss`** (быстрее, точнее). В шпаргалке даны эквиваленты.

---

## Установка
**Linux (Debian/Ubuntu):**
```
sudo apt update && sudo apt install -y net-tools
```
**Linux (RHEL/CentOS/Rocky/Alma):**
```
sudo yum install -y net-tools
```
**macOS (встроен в `/usr/sbin/netstat`)**  
**Windows (встроен):** `netstat` в cmd/PowerShell.

---

## Быстрый старт — топ-12 команд

1) Все TCP/UDP + процессы (Linux/macOS):
```
sudo netstat -tulpen
```
Эквивалент `ss`:
```
sudo ss -tulpen
```

2) Только слушающие порты TCP/UDP:
```
sudo netstat -tuln
```
Эквивалент `ss`:
```
sudo ss -tuln
```

3) Кто слушает конкретный порт (например, 8080):
```
sudo netstat -tulpen | grep :8080
```
Эквивалент `ss`:
```
sudo ss -tulpen | grep :8080
```

4) Активные TCP-соединения с процессами:
```
sudo netstat -tpn
```
Эквивалент `ss`:
```
sudo ss -tpn
```

5) Подсчитать установленные TCP-сессии (ESTABLISHED):
```
netstat -tan | awk '$6=="ESTABLISHED"{c++} END{print c+0}'
```
Эквивалент `ss`:
```
ss -tan state established | wc -l
```

6) Найти «висящие» соединения в `SYN_SENT`/`TIME_WAIT`:
```
netstat -tan | awk '$6=="SYN_SENT"||$6=="TIME_WAIT"{print}' | head
```
Эквивалент `ss`:
```
ss -tan state syn-sent,time-wait | head
```

7) Статистика протоколов (ошибки, сбросы):
```
netstat -s
```
Эквивалент `ss`:
```
ss -s
```

8) Маршрутная таблица:
```
netstat -rn
```
Эквивалент `ip route`:
```
ip route
```

9) Интерфейсы и счётчики:
```
netstat -i
```
Эквивалент `ip -s link`:
```
ip -s link
```

10) Соединения с конкретным хостом/подсетью:
```
netstat -tan | grep 10.0.0.
```
Эквивалент `ss`:
```
ss -tan dst 10.0.0.0/24
```

11) Топ «самых болтливых» удалённых адресов:
```
netstat -tan | awk '$6=="ESTABLISHED"{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head
```
Эквивалент `ss`:
```
ss -tan state established | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head
```

12) Windows: кто слушает и какой PID:
```
netstat -ano | findstr LISTENING
```
Потом сопоставить PID:
```
tasklist | findstr <PID>
```

---

## Ключи (Linux/macOS)
- `-t` TCP, `-u` UDP, `-l` только LISTEN, `-p` процесс, `-n` не резолвить DNS/сервисы (быстрее)
- `-a` все сокеты, `-e` расширенный вывод, `-s` статистика, `-r` маршруты, `-i` интерфейсы
- Комбинируются: `-tulpen` = TCP+UDP, LISTEN, PID/имя, numeric, extended

**Состояния TCP (полезные):**
- `LISTEN`, `ESTABLISHED` — норм
- `SYN_SENT` — проблемы с установкой соединения (часто сетевые/файрвол)
- `TIME_WAIT` — массовое накопление = возможны утечки/неоптимальные таймауты

---

## Частые задачи и рецепты

### 1) «Кто занял порт 80/443/5432?»
```
sudo netstat -tulpen | egrep ':80 |:443 |:5432 '
```
Альтернатива:
```
sudo lsof -i :80
```

### 2) «Почему сервис не принимает соединения?»
- Проверить слушает ли порт:
```
sudo netstat -tuln | grep :8080 || echo "Порт 8080 не слушается"
```
- Есть ли файрвол/политики:
```
sudo iptables -S | grep 8080
sudo ufw status | grep 8080
```
- Маршруты/ARP:
```
netstat -rn
ip neigh
```

### 3) «Много TIME_WAIT — это плохо?»
Подсчёт и топ:
```
netstat -tan | awk '$6=="TIME_WAIT"{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head
```
Рекомендации: проверить keep-alive, reuseport, балансер, таймауты приложения/прокси.

### 4) «Шипят SYN_SENT — соединение не устанавливается»
Смотрим, куда именно:
```
netstat -tan | awk '$6=="SYN_SENT"{print $4,"->",$5}' | sort | uniq -c | sort -nr | head
```
Дальше: трассировка `mtr`, проверка ACL/NAT/SG, security-группы.

### 5) «Кто держит слишком много коннектов к БД?»
```
netstat -tan | grep ':5432 ' | awk '$6=="ESTABLISHED"{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head
```

### 6) IPv6 только:
```
netstat -tan | grep '::'
```

### 7) Фильтр по локальному/удалённому порту
```
netstat -tan | awk '$4 ~ /:8080$/ || $5 ~ /:8080$/'
```

---

## Разбор столбцов (типичный вывод `-tan`)
- `Proto` — tcp/udp
- `Recv-Q`/`Send-Q` — очереди (большие цифры = упрётся/подвисает)
- `Local Address` / `Foreign Address` — кто с кем
- `State` — состояние TCP

---

## Мини-аудит безопасности (хост)
1) Показать все слушающие сокеты с процессами:
```
sudo netstat -tulpen | sort
```
2) Проверить неожиданные привилегированные порты (<1024).  
3) Сопоставить с политикой файрвола/SG.  
4) Глянуть UDP сервисы (часто забывают закрыть):
```
sudo netstat -uln
```

---

## Производительность и нагрузка
- «Горячие» направления трафика:
```
netstat -i
```
- Скорости/ошибки по интерфейсам смотрите в `ip -s link`, плюс `ethtool -S <iface>`.
- Большие `Send-Q/Recv-Q` + много `ESTABLISHED` → возможны проблемы в приложении/бэкенде/диске.

---

## Эквиваленты на `ss` (рекомендуется)
| Цель | netstat | ss |
|---|---|---|
| Все слушающие порты | `sudo netstat -tuln` | `sudo ss -tuln` |
| Порты + PID/имя | `sudo netstat -tulpen` | `sudo ss -tulpen` |
| Установленные TCP | `netstat -tan \| awk '$6=="ESTABLISHED"'` | `ss -tan state established` |
| TIME_WAIT/SYN_SENT | `netstat -tan | awk …` | `ss -tan state time-wait,syn-sent` |
| Кто слушает 8080 | `… | grep :8080` | `ss -tulpen | grep :8080` |
| Статистика | `netstat -s` | `ss -s` |

---

## Windows раздел (быстро)
- Все соединения с PID:
```
netstat -ano
```
- Только слушающие:
```
netstat -ano | findstr LISTENING
```
- Кто этот PID:
```
tasklist | findstr <PID>
```
- С фильтрацией порта:
```
netstat -ano | findstr :1433
```

---

## Частые ошибки и ловушки
- **Без `sudo` не видно `-p` (PID/процесс)** на Linux.
- **DNS резолв тормозит** → всегда добавляйте `-n`.
- В некоторых образах `netstat` отсутствует → ставьте `net-tools` или используйте `ss`.

---

## Набор one-liners (копипаст)

Подсчитать соединения по состояниям:
```
netstat -tan | awk '{c[$6]++} END{for (s in c) printf "%-15s %d\n", s, c[s]}' | sort
```

Вывести «локальный:порт → удалённый:порт (только ESTABLISHED)»:
```
netstat -tan | awk '$6=="ESTABLISHED"{print $4,"->",$5}'
```

Топ удалённых IP по числу коннектов к 443:
```
netstat -tan | awk '$5 ~ /:443$/ {print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head
```

Найти процессы, слушающие привилегированные порты (<1024):
```
sudo netstat -tulpen | awk -F'[: ]+' '($0 ~ /LISTEN/ && $(NF-1) < 1024){print $0}'
```

---

## FAQ

**Q: `netstat: command not found`**  
A: Установите `net-tools` или используйте `ss`.

**Q: Почему `-p` не показывает процессы?**  
A: Нужны привилегии (sudo/root).

**Q: Чем `ss` лучше?**  
A: Быстрее, больше фильтров по состояниям/полям, точнее статистика, доступен по умолчанию.

---

