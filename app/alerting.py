from flask import current_app
from flask_mail import Message
from app import db, mail
from app.models import Subnet, IPAddress, ActivityLog

def get_subnet_utilization(subnet):
    """Hitung persentase IP terpakai di subnet. Return (allocated, usable, percentage)."""
    from app.utils import calculate_subnet_details
    details = calculate_subnet_details(subnet.network_address)
    if details['usable_hosts'] == 0:
        return 0, 0, 0
    allocated = IPAddress.query.filter_by(subnet_id=subnet.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
    percentage = int((allocated / details['usable_hosts']) * 100)
    return allocated, details['usable_hosts'], percentage

def check_and_alert(subnet):
    """Periksa utilisasi subnet, dan kirim notifikasi jika melebihi threshold."""
    if subnet.alert_threshold is None or subnet.alert_threshold == 0:
        return  # threshold dimatikan

    allocated, usable, usage_pct = get_subnet_utilization(subnet)
    if usage_pct >= subnet.alert_threshold:
        # Cegah spam: hanya kirim jika belum ada alert untuk threshold ini dalam 1 jam terakhir
        recent_alert = ActivityLog.query.filter(
            ActivityLog.action == 'SUBNET_USAGE_ALERT',
            ActivityLog.details.like(f'%subnet_id={subnet.id}%')
        ).order_by(ActivityLog.timestamp.desc()).first()

        if recent_alert:
            # Periksa apakah sudah 1 jam sejak alert terakhir
            from datetime import datetime, timedelta
            if datetime.utcnow() - recent_alert.timestamp < timedelta(hours=1):
                return  # masih dalam cooldown 1 jam

        # Kirim email ke admin (jika email dikonfigurasi)
        if (current_app.config.get('MAIL_USERNAME') and
            current_app.config.get('MAIL_DEFAULT_SENDER')):
            try:
                # Kirim ke admin pertama, atau ke alamat tertentu
                from app.models import User
                admins = User.query.filter_by(is_admin=True).all()
                recipients = [admin.email for admin in admins if admin.email]
                if recipients:
                    msg = Message(
                        subject=f'[IPAM ALERT] Subnet {subnet.name} hampir penuh ({usage_pct}%)',
                        recipients=recipients,
                        body=f'''Subnet "{subnet.name}" ({subnet.network_address}) telah mencapai {usage_pct}% utilisasi.
                        
Detail:
- Total usable IPs: {usable}
- Terpakai: {allocated}
- Tersedia: {usable - allocated}
- Ambang batas: {subnet.alert_threshold}%

Silakan periksa dan lakukan tindakan yang diperlukan.
'''
                    )
                    mail.send(msg)
                    current_app.logger.info(f'Alert email terkirim untuk subnet {subnet.name}')
            except Exception as e:
                current_app.logger.error(f'Gagal mengirim email alert: {e}')

        # Catat alert ke ActivityLog
        alert_log = ActivityLog(
            user_id=None,  # system alert
            action='SUBNET_USAGE_ALERT',
            details=f'subnet_id={subnet.id}; name={subnet.name}; '
                    f'usage={usage_pct}%; threshold={subnet.alert_threshold}%'
        )
        db.session.add(alert_log)
        db.session.commit()