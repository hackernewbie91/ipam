# HOW TO SETUP

1. Buat Database PostgreSQL
   
   sudo -u postgres psql

   CREATE USER ipam_user WITH PASSWORD 'password_anda';
   CREATE DATABASE ipam_db OWNER ipam_user;
   GRANT ALL PRIVILEGES ON DATABASE ipam_db TO ipam_user;
   \q

2. Inisialisasi Migrasi (Jika Folder migrations/ Belum Ada di Repository)
   
   Jika folder migrations/ sudah ter-commit di Git, langsung jalankan:

   cd /opt/ipam
   source venv/bin/activate

   # Terapkan migrasi
   flask db upgrade

   Perintah flask db upgrade akan membuat semua tabel sesuai model di app/models.py
   
3. Jika Folder migrations/ Tidak Ada
   Anda perlu buat migrasi awal:

   bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   
4. Buat Admin User

   flask create-admin admin admin@domain.com password_anda
