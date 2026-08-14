from flask import Blueprint, render_template, request, jsonify
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Subnet, IPAddress
from app.utils import calculate_subnet_details
from app.alerting import get_subnet_utilization
from app import db
from flask import current_app, request
from app.scheduler import start_auto_scan, stop_auto_scan

main_bp = Blueprint('main', __name__)

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