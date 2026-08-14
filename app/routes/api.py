from flask import Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth
from app.models import User, Subnet, IPAddress
from app import db
from app.utils import calculate_subnet_details, log_activity
from app.scanner import scan_subnet, scan_all_subnets
import ipaddress

api_bp = Blueprint('api', __name__)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

@auth.error_handler
def unauthorized():
    return jsonify({'error': 'Unauthorized access'}), 401

@api_bp.route('/subnets')
@auth.login_required
def get_subnets():
    subnets = Subnet.query.all()
    result = []
    for s in subnets:
        details = calculate_subnet_details(s.network_address)
        used = IPAddress.query.filter_by(subnet_id=s.id)\
                .filter(IPAddress.status.in_(['allocated', 'reserved'])).count()
        result.append({
            'id': s.id, 'name': s.name, 'network': s.network_address,
            'gateway': s.gateway, 'vlan': s.vlan, 'location': s.location,
            'total_usable': details['usable_hosts'],
            'allocated': used,
            'available': max(0, details['usable_hosts'] - used)
        })
    return jsonify(result)

@api_bp.route('/subnets/<int:subnet_id>/ips')
@auth.login_required
def get_ips(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    ips = IPAddress.query.filter_by(subnet_id=subnet.id).order_by(IPAddress.ip_address).all()
    result = [{
        'id': ip.id, 'ip_address': ip.ip_address, 'status': ip.status,
        'hostname': ip.hostname, 'mac': ip.mac_address,
        'device_type': ip.device_type, 'assigned_to': ip.assigned_to,
        'description': ip.description,
        'last_seen': ip.last_seen.isoformat() if ip.last_seen else None
    } for ip in ips]
    return jsonify(result)

@api_bp.route('/subnets/<int:subnet_id>/ips', methods=['POST'])
@auth.login_required
def create_ip(subnet_id):
    data = request.get_json(silent=True) or {}
    if 'ip_address' not in data:
        return jsonify({'error': 'Missing ip_address field'}), 400
    ip_str = data['ip_address']
    subnet = Subnet.query.get_or_404(subnet_id)
    try:
        ip = ipaddress.ip_address(ip_str)
        net = ipaddress.ip_network(subnet.network_address, strict=False)
        if ip not in net:
            return jsonify({'error': 'IP not in subnet range'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid IP address'}), 400
    if IPAddress.query.filter_by(subnet_id=subnet.id, ip_address=ip_str).first():
        return jsonify({'error': 'IP already exists'}), 409
    new_ip = IPAddress(
        ip_address=ip_str, subnet_id=subnet.id,
        status=data.get('status', 'allocated'),
        hostname=data.get('hostname'), mac_address=data.get('mac'),
        device_type=data.get('device_type'), assigned_to=data.get('assigned_to'),
        description=data.get('description')
    )
    db.session.add(new_ip)
    db.session.commit()
    log_activity(f'API: Created IP {ip_str} in {subnet.name}')
    return jsonify({'message': 'IP created', 'id': new_ip.id}), 201

@api_bp.route('/ips/<int:ip_id>', methods=['PUT'])
@auth.login_required
def update_ip(ip_id):
    ip_entry = IPAddress.query.get_or_404(ip_id)
    data = request.get_json(silent=True) or {}
    if 'ip_address' in data:
        new_ip = data['ip_address']
        try:
            ip = ipaddress.ip_address(new_ip)
            net = ipaddress.ip_network(ip_entry.subnet.network_address, strict=False)
            if ip not in net:
                return jsonify({'error': 'IP not in subnet range'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid IP address'}), 400
        dup = IPAddress.query.filter(
            IPAddress.subnet_id == ip_entry.subnet_id,
            IPAddress.ip_address == new_ip,
            IPAddress.id != ip_id).first()
        if dup:
            return jsonify({'error': 'IP already exists'}), 409
        ip_entry.ip_address = new_ip
    ip_entry.status = data.get('status', ip_entry.status)
    ip_entry.hostname = data.get('hostname', ip_entry.hostname)
    ip_entry.mac_address = data.get('mac', ip_entry.mac_address)
    ip_entry.device_type = data.get('device_type', ip_entry.device_type)
    ip_entry.assigned_to = data.get('assigned_to', ip_entry.assigned_to)
    ip_entry.description = data.get('description', ip_entry.description)
    db.session.commit()
    log_activity(f'API: Updated IP {ip_entry.ip_address}')
    return jsonify({'message': 'IP updated', 'id': ip_entry.id})

@api_bp.route('/ips/<int:ip_id>', methods=['DELETE'])
@auth.login_required
def delete_ip(ip_id):
    ip_entry = IPAddress.query.get_or_404(ip_id)
    db.session.delete(ip_entry)
    db.session.commit()
    log_activity(f'API: Deleted IP {ip_entry.ip_address}')
    return jsonify({'message': 'IP deleted'})

@api_bp.route('/scan/subnet/<int:subnet_id>', methods=['POST'])
@auth.login_required
def trigger_scan_subnet(subnet_id):
    """Trigger scan for a specific subnet."""
    result, status_code = scan_subnet(subnet_id)
    return jsonify(result), status_code

@api_bp.route('/scan/all', methods=['POST'])
@auth.login_required
def trigger_scan_all():
    """Trigger scan for all subnets."""
    result = scan_all_subnets()
    return jsonify(result), 200

@api_bp.route('/autoscan/toggle', methods=['POST'])
@auth.login_required
def toggle_auto_scan():
    """Toggle auto scan ON/OFF."""
    data = request.get_json(silent=True) or {}
    enabled = data.get('enabled', None)
    if enabled is None:
        return jsonify({'error': 'Missing "enabled" field'}), 400

    from flask import current_app
    if enabled:
        interval = data.get('interval', current_app.config.get('AUTO_SCAN_INTERVAL', 30))
        start_auto_scan(current_app, interval)
        return jsonify({'message': f'Auto scan enabled with interval {interval} minutes.', 'enabled': True})
    else:
        stop_auto_scan(current_app)
        return jsonify({'message': 'Auto scan disabled.', 'enabled': False})