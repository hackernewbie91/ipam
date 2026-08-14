import ipaddress
from functools import wraps
from flask import abort
import json
from app import db
from app.models import ActivityLog
from flask_login import current_user
from app.models import Setting

def calculate_subnet_details(network_str):
    net = ipaddress.ip_network(network_str, strict=False)
    usable = net.num_addresses - 2 if net.version == 4 and net.num_addresses > 2 else 0
    return {
        'network_address': str(net.network_address),
        'broadcast_address': str(net.broadcast_address),
        'netmask': str(net.netmask),
        'prefixlen': net.prefixlen,
        'num_addresses': net.num_addresses,
        'usable_hosts': usable,
        'first_usable': str(net.network_address + 1) if net.num_addresses > 2 else None,
        'last_usable': str(net.broadcast_address - 1) if net.num_addresses > 2 else None,
    }

def log_activity(action, details=None):
    """Catat aktivitas sederhana (hanya untuk kompatibilitas)."""
    if current_user and current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            action=action,
            details=details
        )
        db.session.add(log)
        db.session.commit()

def log_change(action, object_type, object_id, changes=None):
    """Catat perubahan detail (audit trail)."""
    if current_user and current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=json.dumps(changes) if changes else None,
            changes=json.dumps(changes) if changes else None
        )
        db.session.add(log)
        db.session.commit()

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_role(*roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_setting(key, default=None):
    """Ambil nilai setting dari database."""
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        return setting.value
    return default

def set_setting(key, value):
    """Simpan atau update setting."""
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        setting.value = str(value)
    else:
        setting = Setting(key=key, value=str(value))
        db.session.add(setting)
    db.session.commit()