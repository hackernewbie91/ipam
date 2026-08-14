from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False, default='viewer')  # admin, manager, operator, viewer
    is_admin = db.Column(db.Boolean, default=False)   # masih bisa disimpan untuk kompatibilitas, tapi tidak digunakan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activities = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    @property
    def is_admin_user(self):   # ganti nama agar tidak bentrok dengan kolom is_admin?
        return self.role == 'admin'

    # Namun kita ingin properti is_admin yang dipanggil oleh Flask-Login atau admin?
    # Gunakan property yang menggantikan kolom is_admin.
    @property
    def is_admin(self):
        return self.role == 'admin'

    @is_admin.setter
    def is_admin(self, value):
        # tidak diperlukan karena kita menggunakan role
        pass

    def has_role(self, *roles):
        return self.role in roles

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Subnet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    network_address = db.Column(db.String(18), nullable=False)
    description = db.Column(db.Text)
    vlan = db.Column(db.Integer)
    location = db.Column(db.String(100))
    gateway = db.Column(db.String(15))
    dns_servers = db.Column(db.String(100))
    alert_threshold = db.Column(db.Integer, default=80)   # <-- BARU
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ips = db.relationship('IPAddress', backref='subnet', lazy='dynamic',
                          cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subnet {self.name} - {self.network_address}>'

class IPAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False, index=True)
    subnet_id = db.Column(db.Integer, db.ForeignKey('subnet.id'), nullable=False)
    status = db.Column(db.String(20), default='allocated')
    hostname = db.Column(db.String(255))
    mac_address = db.Column(db.String(17))
    device_type = db.Column(db.String(50))
    assigned_to = db.Column(db.String(100))
    description = db.Column(db.Text)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ip_address', 'subnet_id', name='unique_ip_subnet'),
    )

    @property
    def is_online(self):
        if self.last_seen is None:
            return False
        # Dianggap online jika terakhir terlihat dalam 5 menit terakhir
        return datetime.utcnow() - self.last_seen < timedelta(minutes=5)

    def __repr__(self):
        return f'<IP {self.ip_address} ({self.status})>'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    object_type = db.Column(db.String(50))     # Nama model: 'Subnet', 'IPAddress', 'User'
    object_id = db.Column(db.Integer)          # ID dari objek yang diubah
    changes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Activity {self.action}>'

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'