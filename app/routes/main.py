from flask import Blueprint, render_template, request, jsonify
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Subnet, IPAddress
from app.utils import calculate_subnet_details, log_change
from app.alerting import get_subnet_utilization
from app import db
from flask import current_app, request
from app.scheduler import start_auto_scan, stop_auto_scan
import subprocess
import os
from datetime import datetime
from flask import send_from_directory
import time
from datetime import datetime, timedelta
from app.utils import calculate_subnet_details, log_change, get_setting, set_setting

main_bp = Blueprint('main', __name__)

# ========== FUNGSI HELPER ==========
def cleanup_old_backups(backup_dir, retention_days):
    """Hapus file backup yang lebih tua dari retention_days."""
    if retention_days <= 0:
        return 0
    now = time.time()
    cutoff = now - (retention_days * 86400)
    deleted = 0
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.sql'):
                file_path = os.path.join(backup_dir, filename)
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    deleted += 1
    return deleted


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    total_subnets = Subnet.query.count()
    subnets = Subnet.query.all()
    total_allocated = 0
    total_available = 0
    for s in subnets:
        details = calculate_subnet_details(s.network_address)
        used = IPAddress.query.filter_by(subnet_id=s.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
        total_allocated += used
        total_available += max(0, details['usable_hosts'] - used)
    stats = {
        'total_subnets': total_subnets,
        'total_allocated': total_allocated,
        'total_available': total_available,
    }

    # Subnet yang over threshold
    all_subnets = Subnet.query.all()
    alert_subnets = []
    for s in all_subnets:
        if s.alert_threshold and s.alert_threshold > 0:
            allocated, usable, usage_pct = get_subnet_utilization(s)
            if usage_pct >= s.alert_threshold:
                alert_subnets.append({
                    'name': s.name,
                    'id': s.id,
                    'usage': usage_pct,
                    'threshold': s.alert_threshold,
                    'available': usable - allocated
                })

    # ========== PENCARIAN ==========
    search_query = request.args.get('search', '').strip()
    search_results = []
    if search_query:
        # Cari berdasarkan IP address, hostname, MAC, atau nama subnet
        search_results = IPAddress.query.join(Subnet)\
            .filter(
                db.or_(
                    IPAddress.ip_address.ilike(f'%{search_query}%'),
                    IPAddress.hostname.ilike(f'%{search_query}%'),
                    IPAddress.mac_address.ilike(f'%{search_query}%'),
                    IPAddress.assigned_to.ilike(f'%{search_query}%'),
                    IPAddress.device_type.ilike(f'%{search_query}%'),
                    Subnet.name.ilike(f'%{search_query}%')
                )
            ).all()

    return render_template('dashboard.html', title='Dashboard',
                           stats=stats, alert_subnets=alert_subnets,
                           search_results=search_results, search_query=search_query)


@main_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API endpoint untuk data grafik dashboard."""
    subnets = Subnet.query.all()
    pie_labels = []
    pie_data = []
    bar_labels = []
    bar_allocated = []
    bar_available = []

    for s in subnets:
        details = calculate_subnet_details(s.network_address)
        if details['usable_hosts'] > 0:
            used = IPAddress.query.filter_by(subnet_id=s.id)\
                    .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
            available = max(0, details['usable_hosts'] - used)
            pct = round((used / details['usable_hosts']) * 100, 1)
            pie_labels.append(s.name)
            pie_data.append(pct)
            bar_labels.append(s.name)
            bar_allocated.append(used)
            bar_available.append(available)

    # Data donut: distribusi global
    total_allocated = IPAddress.query.filter_by(status='allocated').count()
    total_reserved = IPAddress.query.filter_by(status='reserved').count()
    total_available_global = 0
    for s in Subnet.query.all():
        details = calculate_subnet_details(s.network_address)
        used = IPAddress.query.filter_by(subnet_id=s.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
        total_available_global += max(0, details['usable_hosts'] - used)

    return jsonify({
        'pie': {
            'labels': pie_labels,
            'data': pie_data
        },
        'bar': {
            'labels': bar_labels,
            'allocated': bar_allocated,
            'available': bar_available
        },
        'donut': {
            'labels': ['Allocated', 'Reserved', 'Available'],
            'data': [total_allocated, total_reserved, total_available_global]
        }
    })

@main_bp.route('/autoscan/toggle', methods=['POST'])
@login_required
def toggle_auto_scan_web():
    if not current_user.is_admin:
        flash('Only admin can toggle auto scan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    enabled = request.form.get('enabled') == 'true'
    interval = int(request.form.get('interval', 30))
    
    if enabled:
        start_auto_scan(current_app, interval)
        flash(f'Auto scan enabled (interval: {interval} minutes).', 'success')
    else:
        stop_auto_scan(current_app)
        flash('Auto scan disabled.', 'success')
    
    return redirect(url_for('main.dashboard'))

# BACKUP RESTORE
@main_bp.route('/backup', methods=['GET'])
@login_required
def backup_database():
    if not current_user.is_admin:
        flash('Only admin can backup database.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Buat folder backup jika belum ada
        backup_dir = os.path.join(current_app.root_path, '..', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nama file backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
        
        # Ambil URL database dari config
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Ekstrak informasi koneksi
        # Format: postgresql://user:password@host:port/dbname
        if db_url.startswith('postgresql://'):
            # Parse URL
            from urllib.parse import urlparse
            parsed = urlparse(db_url)
            db_name = parsed.path.lstrip('/')
            db_user = parsed.username
            db_password = parsed.password
            db_host = parsed.hostname or 'localhost'
            db_port = parsed.port or 5432
            
            # Jalankan pg_dump
            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-f', backup_file
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Cleanup old backups
                retention_days = int(get_setting('backup_retention_days', '30'))
                deleted_count = cleanup_old_backups(backup_dir, retention_days)
                
                flash(f'Backup berhasil: {os.path.basename(backup_file)}', 'success')
                if deleted_count > 0:
                    flash(f'{deleted_count} old backup(s) deleted automatically.', 'info')
                log_change('BACKUP', 'Database', 0, {'file': os.path.basename(backup_file)})
            else:
                flash(f'Backup gagal: {result.stderr}', 'danger')
        else:
            flash('Backup hanya tersedia untuk PostgreSQL.', 'warning')
            
    except Exception as e:
        flash(f'Backup error: {str(e)}', 'danger')
    
    return redirect(url_for('main.list_backups'))


@main_bp.route('/backup/download/<filename>')
@login_required
def download_backup(filename):
    if not current_user.is_admin:
        flash('Only admin can download backup.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    return send_from_directory(backup_dir, filename, as_attachment=True)


@main_bp.route('/backup/list')
@login_required
def list_backups():
    if not current_user.is_admin:
        flash('Only admin can view backups.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    backups = []
    if os.path.exists(backup_dir):
        for file in sorted(os.listdir(backup_dir), reverse=True):
            if file.endswith('.sql'):
                file_path = os.path.join(backup_dir, file)
                size = os.path.getsize(file_path)
                backups.append({
                    'filename': file,
                    'size': f'{size / 1024:.2f} KB',
                    'created': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%d-%m-%Y %H:%M:%S')
                })
    
    return render_template('backup_list.html', backups=backups)


@main_bp.route('/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    if not current_user.is_admin:
        flash('Only admin can delete backups.', 'danger')
        return redirect(url_for('main.list_backups'))
    
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    file_path = os.path.join(backup_dir, filename)
    
    if os.path.exists(file_path) and filename.endswith('.sql'):
        os.remove(file_path)
        flash(f'Backup {filename} deleted.', 'success')
        log_change('DELETE', 'Backup', 0, {'file': filename})
    else:
        flash('File tidak ditemukan.', 'danger')
    
    return redirect(url_for('main.list_backups'))


@main_bp.route('/backup/settings', methods=['POST'])
@login_required
def backup_settings():
    if not current_user.is_admin:
        flash('Only admin can change backup settings.', 'danger')
        return redirect(url_for('main.list_backups'))
    
    retention_days = request.form.get('retention_days', '30')
    try:
        retention_days = int(retention_days)
        if retention_days < 1:
            retention_days = 1
        set_setting('backup_retention_days', str(retention_days))
        flash(f'Backup retention set to {retention_days} days.', 'success')
    except ValueError:
        flash('Invalid number of days.', 'danger')
    
    return redirect(url_for('main.list_backups'))


@main_bp.route('/webhooks', methods=['GET', 'POST'])
@login_required
def webhooks():
    if not current_user.is_admin:
        flash('Only admin can manage webhooks.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        event = request.form.get('event')
        is_active = request.form.get('is_active') == 'on'
        
        webhook = Webhook(name=name, url=url, event=event, is_active=is_active)
        db.session.add(webhook)
        db.session.commit()
        flash('Webhook added successfully.', 'success')
        return redirect(url_for('main.webhooks'))
    
    webhooks = Webhook.query.all()
    return render_template('webhooks.html', webhooks=webhooks)


@main_bp.route('/webhooks/<int:webhook_id>/delete', methods=['POST'])
@login_required
def delete_webhook(webhook_id):
    if not current_user.is_admin:
        flash('Only admin can delete webhooks.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    webhook = Webhook.query.get_or_404(webhook_id)
    db.session.delete(webhook)
    db.session.commit()
    flash('Webhook deleted.', 'success')
    return redirect(url_for('main.webhooks'))