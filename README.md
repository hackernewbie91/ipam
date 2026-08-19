# HOW TO INSTALL

**1. Update System**
```ini   
sudo apt update
sudo apt upgrade -y
```
**2. Install Dependencies**
```ini
sudo apt install -y python3 python3-venv python3-pip git postgresql postgresql-contrib
```
Install Nginx (Opsional)
```ini
sudo apt install -y nginx
```
**3. Setup PostgreSQL
3.1 Masuk ke PostgreSQL****
```ini   
sudo -u postgres psql
```
**3.2 Buat Database & User**

```ini
CREATE USER ipam_user WITH PASSWORD 'password_anda';
CREATE DATABASE ipam_db OWNER ipam_user;
GRANT ALL PRIVILEGES ON DATABASE ipam_db TO ipam_user;
\q
```

Catatan: Ganti password_anda dengan password yang kuat.

**4. Clone Repository**

```ini
cd /opt
sudo git clone https://github.com/hackernewbie91/ipam.git
cd ipam
sudo chown -R ubuntu:ubuntu /opt/ipam
```

**5. Setup Virtual Environment
5.1 Buat Virtual Environment**

```ini
cd /opt/ipam
python3 -m venv venv
```

**5.2 Aktifkan Virtual Environment**
```ini
source venv/bin/activate
```
**5.3 Install Dependencies**
```ini
pip install --upgrade pip
pip install -r requirements.txt
```
**6. Konfigurasi Environment
6.1 Buat File .env**
```ini
nano .env
```
Isi dengan:
```ini
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
DATABASE_URL=postgresql://appuser:password@localhost:5432/ipam_db?sslmode=disable

# Mail Server Setting
MAIL_SERVER=mail.yourdomain.com          # ganti dengan server email Anda
MAIL_PORT=465
MAIL_USE_TLS=false                       # jangan gunakan TLS
MAIL_USE_SSL=true                        # gunakan SSL
MAIL_USERNAME=you@yourdomain.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=you@yourdomain.com

AUTO_SCAN_ENABLED=false
AUTO_SCAN_INTERVAL=30

# Gunicorn Settings (opsional)
GUNICORN_WORKERS=4
GUNICORN_BIND=0.0.0.0:5100
GUNICORN_LOG_LEVEL=info
```
**6.2 Generate SECRET_KEY**
```ini
python -c "import secrets; print(secrets.token_hex(32))"
```
Salin hasilnya ke SECRET_KEY di .env.

**7. Inisialisasi Database
7.1 Migrasi Database**
```ini
flask db upgrade
```
**7.2 Buat Admin User**
```ini
flask create-admin admin admin@domain.com password_anda
```
**8. Setup Gunicorn
8.1 Buat File gunicorn_config.py (Jika Belum Ada)**
```ini
nano gunicorn_config.py
```
Isi:
```ini
# gunicorn_config.py

import os

# ============================================
# Gunicorn Configuration for IPAM
# ============================================

# Number of worker processes
# Formula: (2 x CPU cores) + 1
workers = int(os.environ.get('GUNICORN_WORKERS', 4))

# Worker class
# 'sync' is safe for CPU-bound, 'gevent' for I/O-bound
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# Number of threads per worker (only for gthread worker class)
threads = int(os.environ.get('GUNICORN_THREADS', 2))

# Timeout for worker processes (in seconds)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))

# Keep-alive connection time (in seconds)
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 5))

# Maximum number of requests a worker will process before restarting
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))

# Add jitter to avoid all workers restarting at the same time
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Graceful timeout (in seconds)
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', 30))

# Bind address
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5100')

# Access log
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')

# Error log
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')

# Log level
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Preload application (saves memory but requires app to be fork-safe)
preload_app = os.environ.get('GUNICORN_PRELOAD_APP', 'true').lower() == 'true'

# Daemon mode (set to 'true' to run in background)
daemon = os.environ.get('GUNICORN_DAEMON', 'false').lower() == 'true'

# Process name
proc_name = 'ipam'

# PID file (only used in daemon mode)
pidfile = 'logs/gunicorn.pid' if daemon else None

# Server mechanics
forwarded_allow_ips = '*'  # Trust X-Forwarded-For headers from proxy
```
**9. Setup Systemd Service
9.1 Buat Folder Logs**
```ini
mkdir -p /opt/ipam/logs
sudo chown -R ubuntu:ubuntu /opt/ipam/logs
```
**9.2 Buat Service File**
```ini
sudo nano /etc/systemd/system/ipam.service
```
Isi:

```ini
[Unit]
Description=IPAM - IP Address Management System
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/ipam
Environment="PATH=/opt/ipam/venv/bin:/home/ubuntu/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ipam/.env
ExecStart=/opt/ipam/venv/bin/gunicorn --config /opt/ipam/gunicorn_config.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=30
StandardOutput=append:/opt/ipam/logs/ipam_stdout.log
StandardError=append:/opt/ipam/logs/ipam_stderr.log

[Install]
WantedBy=multi-user.target
```

**9.3 Aktifkan Service**
```ini
sudo systemctl daemon-reload
sudo systemctl start ipam
sudo systemctl enable ipam
sudo systemctl status ipam
```
**10. Setup Nginx (Opsional)
10.1 Buat Config Nginx**
```ini    
sudo nano /etc/nginx/sites-available/ipam
```
Isi:
```ini
nginx
server {
    listen 80;
    server_name ipam.domain.com;

    access_log /var/log/nginx/ipam_access.log;
    error_log /var/log/nginx/ipam_error.log;

    location / {
        proxy_pass http://127.0.0.1:5100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_redirect off;
    }

    location /static/ {
        alias /opt/ipam/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```
**10.2 Aktifkan Nginx**
```ini
sudo ln -s /etc/nginx/sites-available/ipam /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
**11. Setup Firewall**
```ini
sudo ufw allow 5100/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
**12. Verifikasi
12.1 Cek Service**
```ini
sudo systemctl status ipam
```
**12.2 Cek Port**
```ini
sudo netstat -tlnp | grep 5100
```
**12.3 Akses Aplikasi**

http://server-ip:5100

**12.4 Cek Log**

tail -f /opt/ipam/logs/ipam.log
sudo journalctl -u ipam -f

**13. Maintenance**
    
Restart Service
```ini
sudo systemctl restart ipam
Stop Service

sudo systemctl stop ipam
```
Backup Database
```ini
sudo -u postgres pg_dump ipam_db > backup_$(date +%Y%m%d).sql
```
Restore Database
```ini
sudo -u postgres psql ipam_db < backup_20260819.sql
```
**14. Troubleshooting**
Cek Error
```ini
sudo journalctl -u ipam --since "5 minutes ago" --no-pager
```
Cek Koneksi Database
```ini
sudo -u ubuntu /opt/ipam/venv/bin/python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.session.execute('SELECT 1')
    print('Database OK')
"
```
Permission Error
```ini
sudo chown -R ubuntu:ubuntu /opt/ipam
sudo chmod -R 755 /opt/ipam/logs
```
✅ Setup Selesai!
Sekarang IPAM sudah berjalan di server baru. Login dengan:

URL: http://server-ip:5100

Username: admin

Password: password_anda
