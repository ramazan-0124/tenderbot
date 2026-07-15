# Деплой на Hetzner Cloud

Эта инструкция запускает Tender Smart Search на Ubuntu/Debian сервере.

## 1. Подключение

```bash
ssh root@178.105.93.245
```

После первого входа обязательно поменяй пароль:

```bash
passwd
```

## 2. Установка пакетов

```bash
apt update
apt install -y python3 python3-venv git ufw
```

## 3. Загрузка проекта

Если проект уже в GitHub:

```bash
cd /opt
git clone https://github.com/ramazan-0124/tenderbot.git tender-smart-search
cd /opt/tender-smart-search
```

Если проекта в GitHub еще нет, сначала нужно запушить текущую папку в репозиторий.

## 4. Проверочный запуск

```bash
HOST=0.0.0.0 PORT=8090 python3 app/main.py
```

Открой:

```text
http://178.105.93.245:8090
```

## 5. Открыть порт

```bash
ufw allow OpenSSH
ufw allow 8090/tcp
ufw --force enable
```

## 6. Запуск 24/7 через systemd

Создай сервис:

```bash
nano /etc/systemd/system/tender-smart-search.service
```

Вставь:

```ini
[Unit]
Description=Tender Smart Search
After=network.target

[Service]
WorkingDirectory=/opt/tender-smart-search
Environment=HOST=0.0.0.0
Environment=PORT=8090
ExecStart=/usr/bin/python3 /opt/tender-smart-search/app/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запусти:

```bash
systemctl daemon-reload
systemctl enable tender-smart-search
systemctl start tender-smart-search
systemctl status tender-smart-search
```

Логи:

```bash
journalctl -u tender-smart-search -f
```

