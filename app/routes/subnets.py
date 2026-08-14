import csv
from app.utils import role_required
import io
import ipaddress
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Subnet, IPAddress
from app.forms import SubnetForm
from app.utils import calculate_subnet_details, log_activity, log_change
from app.alerting import check_and_alert

subnets_bp = Blueprint('subnets', __name__)


@subnets_bp.route('/')
@login_required
def list_subnets():
    page = request.args.get('page', 1, type=int)
    subnets = Subnet.query.order_by(Subnet.name).paginate(
        page=page, per_page=10, error_out=False)

    # Tambahkan utilisasi untuk setiap subnet
    from app.alerting import get_subnet_utilization
    subnet_data = []
    for s in subnets.items:
        allocated, usable, usage_pct = get_subnet_utilization(s)
        subnet_data.append({
            'subnet': s,
            'allocated': allocated,
            'usable': usable,
            'usage_pct': usage_pct
        })

    return render_template('subnets.html', title='Subnets', subnets=subnets,
                           subnet_data=subnet_data)


@subnets_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def create_subnet():
    form = SubnetForm()
    if form.validate_on_submit():
        subnet = Subnet(
            name=form.name.data,
            network_address=form.network_address.data,
            description=form.description.data,
            vlan=form.vlan.data,
            location=form.location.data,
            gateway=form.gateway.data,
            dns_servers=form.dns_servers.data,
            alert_threshold=form.alert_threshold.data
        )
        db.session.add(subnet)
        db.session.commit()
        log_activity(f'Created subnet {subnet.name}')
        # Audit trail
        changes = {
            'name': subnet.name,
            'network': subnet.network_address,
            'vlan': subnet.vlan,
            'location': subnet.location,
            'gateway': subnet.gateway,
            'dns': subnet.dns_servers,
            'description': subnet.description,
            'alert_threshold': subnet.alert_threshold
        }
        log_change('CREATE', 'Subnet', subnet.id, changes)
        flash('Subnet created successfully.', 'success')
        return redirect(url_for('subnets.list_subnets'))
    return render_template('subnet_form.html', title='Create Subnet',
                           form=form, legend='Create Subnet')


@subnets_bp.route('/<int:subnet_id>')
@login_required
def subnet_detail(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    page = request.args.get('page', 1, type=int)
    ips = IPAddress.query.filter_by(subnet_id=subnet.id)\
            .filter(IPAddress.status.in_(['allocated', 'reserved']))\
            .order_by(IPAddress.ip_address)\
            .paginate(page=page, per_page=20, error_out=False)
    details = calculate_subnet_details(subnet.network_address)
    allocated = IPAddress.query.filter_by(subnet_id=subnet.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
    available = max(0, details['usable_hosts'] - allocated)

    # Hitung daftar IP free/available
    all_ips_in_db = IPAddress.query.filter_by(subnet_id=subnet.id).with_entities(IPAddress.ip_address).all()
    used_ips = set(ip[0] for ip in all_ips_in_db)
    free_ips = []
    net = ipaddress.ip_network(subnet.network_address, strict=False)
    if net.num_addresses > 2:
        start = net.network_address + 1
        end = net.broadcast_address - 1
        current = start
        while current <= end:
            ip_str = str(current)
            if ip_str not in used_ips:
                free_ips.append(ip_str)
            current += 1

    return render_template('subnet_detail.html', subnet=subnet, ips=ips,
                           details=details, allocated_count=allocated,
                           available=available, free_ips=free_ips)


@subnets_bp.route('/<int:subnet_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager') 
def edit_subnet(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    form = SubnetForm()
    if form.validate_on_submit():
        # Simpan nilai lama untuk audit
        old_values = {
            'name': subnet.name,
            'network_address': subnet.network_address,
            'description': subnet.description,
            'vlan': subnet.vlan,
            'location': subnet.location,
            'gateway': subnet.gateway,
            'dns_servers': subnet.dns_servers,
            'alert_threshold': subnet.alert_threshold
        }

        subnet.name = form.name.data
        subnet.network_address = form.network_address.data
        subnet.description = form.description.data
        subnet.vlan = form.vlan.data
        subnet.location = form.location.data
        subnet.gateway = form.gateway.data
        subnet.dns_servers = form.dns_servers.data
        subnet.alert_threshold = form.alert_threshold.data
        db.session.commit()

        # Bandingkan perubahan
        new_values = {
            'name': subnet.name,
            'network_address': subnet.network_address,
            'description': subnet.description,
            'vlan': subnet.vlan,
            'location': subnet.location,
            'gateway': subnet.gateway,
            'dns_servers': subnet.dns_servers,
            'alert_threshold': subnet.alert_threshold
        }
        changes = {}
        for key in old_values:
            if str(old_values[key]) != str(new_values[key]):
                changes[key] = {'old': str(old_values[key]), 'new': str(new_values[key])}
        if changes:
            log_change('UPDATE', 'Subnet', subnet.id, changes)

        log_activity(f'Edited subnet {subnet.name}')
        flash('Subnet updated.', 'success')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet.id))
    elif request.method == 'GET':
        form.name.data = subnet.name
        form.network_address.data = subnet.network_address
        form.description.data = subnet.description
        form.vlan.data = subnet.vlan
        form.location.data = subnet.location
        form.gateway.data = subnet.gateway
        form.dns_servers.data = subnet.dns_servers
        form.alert_threshold.data = subnet.alert_threshold
    return render_template('subnet_form.html', title='Edit Subnet',
                           form=form, legend='Edit Subnet')


@subnets_bp.route('/<int:subnet_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def delete_subnet(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    # Simpan data untuk audit sebelum dihapus
    old_data = {
        'name': subnet.name,
        'network': subnet.network_address,
        'vlan': subnet.vlan,
        'location': subnet.location,
        'gateway': subnet.gateway,
        'dns': subnet.dns_servers,
        'alert_threshold': subnet.alert_threshold
    }
    db.session.delete(subnet)
    db.session.commit()
    log_activity(f'Deleted subnet {subnet.name}')
    log_change('DELETE', 'Subnet', subnet_id, old_data)
    flash('Subnet deleted.', 'success')
    return redirect(url_for('subnets.list_subnets'))


@subnets_bp.route('/<int:subnet_id>/scan', methods=['POST'])
@login_required
def scan_subnet_route(subnet_id):
    from app.scanner import scan_subnet
    result, status_code = scan_subnet(subnet_id)
    return jsonify(result), status_code


@subnets_bp.route('/<int:subnet_id>/export')
@login_required
@role_required('admin', 'manager', 'operator')
def export_csv(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    ips = IPAddress.query.filter_by(subnet_id=subnet.id)\
            .order_by(IPAddress.ip_address).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ip_address', 'status', 'hostname', 'mac_address',
                     'device_type', 'assigned_to', 'description', 'last_seen'])
    for ip in ips:
        writer.writerow([
            ip.ip_address,
            ip.status,
            ip.hostname or '',
            ip.mac_address or '',
            ip.device_type or '',
            ip.assigned_to or '',
            ip.description or '',
            ip.last_seen.isoformat() if ip.last_seen else ''
        ])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={subnet.name}_ips.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


@subnets_bp.route('/<int:subnet_id>/import', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def import_csv(subnet_id):
    if not current_user.is_admin:
        flash('Only administrators can import IP addresses.', 'danger')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))

    subnet = Subnet.query.get_or_404(subnet_id)
    file = request.files.get('csv_file')
    if not file:
        flash('No file selected.', 'danger')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))
    if not file.filename.endswith('.csv'):
        flash('Only CSV files are allowed.', 'danger')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_reader = csv.DictReader(stream)

    success_count = 0
    error_count = 0
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):
        ip_str = row.get('ip_address', '').strip()
        if not ip_str:
            errors.append(f'Row {row_num}: missing IP address')
            error_count += 1
            continue

        try:
            ip_obj = ipaddress.ip_address(ip_str)
            net = ipaddress.ip_network(subnet.network_address, strict=False)
            if ip_obj not in net:
                errors.append(f'Row {row_num}: IP {ip_str} not in subnet range')
                error_count += 1
                continue
        except ValueError:
            errors.append(f'Row {row_num}: invalid IP address {ip_str}')
            error_count += 1
            continue

        existing = IPAddress.query.filter_by(subnet_id=subnet.id, ip_address=ip_str).first()
        if existing:
            errors.append(f'Row {row_num}: IP {ip_str} already exists, skipped')
            error_count += 1
            continue

        status = row.get('status', 'allocated').strip().lower()
        if status not in ('allocated', 'reserved', 'available'):
            status = 'allocated'

        new_ip = IPAddress(
            ip_address=ip_str,
            subnet_id=subnet.id,
            status=status,
            hostname=row.get('hostname', '').strip() or None,
            mac_address=row.get('mac_address', '').strip() or None,
            device_type=row.get('device_type', '').strip() or None,
            assigned_to=row.get('assigned_to', '').strip() or None,
            description=row.get('description', '').strip() or None
        )
        db.session.add(new_ip)
        success_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))

    if success_count:
        flash(f'Successfully imported {success_count} IP address(es).', 'success')
    if error_count:
        flash(f'{error_count} error(s): {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}', 'warning')

    log_activity(f'Imported {success_count} IPs into {subnet.name} (errors: {error_count})')
    check_and_alert(subnet)   # alert setelah import
    return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))


@subnets_bp.route('/<int:subnet_id>/ipmap')
@login_required
def ip_map(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    details = calculate_subnet_details(subnet.network_address)
    allocated = IPAddress.query.filter_by(subnet_id=subnet.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
    available = max(0, details['usable_hosts'] - allocated)
    return render_template('ip_map.html', subnet=subnet, details=details,
                           allocated_count=allocated, available=available)


@subnets_bp.route('/<int:subnet_id>/ipmap/data')
@login_required
def ip_map_data(subnet_id):
    import ipaddress
    subnet = Subnet.query.get_or_404(subnet_id)
    net = ipaddress.ip_network(subnet.network_address, strict=False)

    all_ips = IPAddress.query.filter_by(subnet_id=subnet.id).all()
    ip_dict = {}
    for ip in all_ips:
        ip_dict[ip.ip_address] = {
            'status': ip.status,
            'hostname': ip.hostname or '',
            'online': ip.is_online
        }

    ip_list = []
    if net.num_addresses > 2:
        start = net.network_address + 1
        end = net.broadcast_address - 1
        current = start
        while current <= end:
            ip_str = str(current)
            if ip_str in ip_dict:
                ip_list.append({
                    'ip': ip_str,
                    'status': ip_dict[ip_str]['status'],
                    'hostname': ip_dict[ip_str]['hostname'],
                    'online': ip_dict[ip_str]['online']
                })
            else:
                ip_list.append({
                    'ip': ip_str,
                    'status': 'free',
                    'hostname': '',
                    'online': False
                })
            current += 1

    network_info = {
        'network': str(net.network_address),
        'broadcast': str(net.broadcast_address),
        'netmask': str(net.netmask),
        'gateway': subnet.gateway or '',
        'total_ips': len(ip_list)
    }

    return jsonify({
        'ips': ip_list,
        'network_info': network_info,
        'subnet_name': subnet.name
    })