import ipaddress
import time
from datetime import datetime
from ping3 import ping
from app import db
from app.models import Subnet, IPAddress
from app.utils import log_activity

def ping_host(ip_str, timeout=1):
    """Ping IP address, return True if alive."""
    try:
        delay = ping(ip_str, timeout=timeout)
        return delay is not None
    except Exception:
        return False

def scan_subnet(subnet_id):
    """Scan all IPs in a subnet and update last_seen."""
    subnet = Subnet.query.get(subnet_id)
    if not subnet:
        return {'error': 'Subnet not found'}, 404

    ips = IPAddress.query.filter_by(subnet_id=subnet.id).all()
    results = {
        'subnet': subnet.name,
        'total': len(ips),
        'online': 0,
        'offline': 0,
        'ip_results': []
    }

    for ip_entry in ips:
        alive = ping_host(ip_entry.ip_address)
        now = datetime.utcnow()
        if alive:
            ip_entry.last_seen = now
            results['online'] += 1
            status = 'online'
        else:
            status = 'offline'
            results['offline'] += 1

        results['ip_results'].append({
            'ip': ip_entry.ip_address,
            'hostname': ip_entry.hostname,
            'status': status,
            'last_seen': ip_entry.last_seen.isoformat() if ip_entry.last_seen else None
        })

    db.session.commit()
    log_activity(f'Scanned subnet {subnet.name}: {results["online"]} up, {results["offline"]} down')
    return results, 200

def scan_all_subnets():
    """Scan all subnets."""
    subnets = Subnet.query.all()
    total_online = 0
    total_offline = 0
    for subnet in subnets:
        res, _ = scan_subnet(subnet.id)
        total_online += res.get('online', 0)
        total_offline += res.get('offline', 0)
    return {
        'subnets_scanned': len(subnets),
        'total_online': total_online,
        'total_offline': total_offline
    }