import ipaddress
from app.utils import role_required
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Subnet, IPAddress
from app.forms import IPAddressForm
from app.utils import log_activity, log_change
from app.alerting import check_and_alert
from app.webhook import send_webhook

ips_bp = Blueprint('ips', __name__)


@ips_bp.route('/<int:subnet_id>/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'operator')
def add_ip(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    form = IPAddressForm()
    if form.validate_on_submit():
        ip_str = form.ip_address.data
        try:
            ip = ipaddress.ip_address(ip_str)
            net = ipaddress.ip_network(subnet.network_address, strict=False)
            if ip not in net:
                flash('IP address is not within the subnet range.', 'danger')
                return render_template('ip_form.html', form=form,
                                       subnet=subnet, legend='Add IP Address')
        except ValueError:
            flash('Invalid IP address.', 'danger')
            return render_template('ip_form.html', form=form,
                                   subnet=subnet, legend='Add IP Address')

        if IPAddress.query.filter_by(subnet_id=subnet.id, ip_address=ip_str).first():
            flash('This IP already exists in this subnet.', 'danger')
            return render_template('ip_form.html', form=form,
                                   subnet=subnet, legend='Add IP Address')

        new_ip = IPAddress(
            ip_address=ip_str,
            subnet_id=subnet.id,
            status=form.status.data,
            hostname=form.hostname.data,
            mac_address=form.mac_address.data,
            device_type=form.device_type.data,
            assigned_to=form.assigned_to.data,
            description=form.description.data
        )
        db.session.add(new_ip)
        db.session.commit()

        # Audit trail
        changes = {
            'ip': new_ip.ip_address,
            'status': new_ip.status,
            'hostname': new_ip.hostname,
            'mac': new_ip.mac_address,
            'device_type': new_ip.device_type,
            'assigned_to': new_ip.assigned_to,
            'description': new_ip.description
        }
        log_change('CREATE', 'IPAddress', new_ip.id, changes)
        log_activity(f'Added IP {ip_str} to {subnet.name}')

        send_webhook('ip_created', {
            'ip': new_ip.ip_address,
            'subnet': subnet.name,
            'status': new_ip.status,
            'user': current_user.username
        })

        # Cek notifikasi setelah penambahan
        check_and_alert(subnet)

        flash('IP address added.', 'success')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet.id))
    return render_template('ip_form.html', form=form, subnet=subnet, legend='Add IP Address')


@ips_bp.route('/edit/<int:ip_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'operator')
def edit_ip(ip_id):
    ip_entry = IPAddress.query.get_or_404(ip_id)
    subnet = ip_entry.subnet
    form = IPAddressForm()
    if form.validate_on_submit():
        ip_str = form.ip_address.data
        if ip_str != ip_entry.ip_address:
            try:
                ip = ipaddress.ip_address(ip_str)
                net = ipaddress.ip_network(subnet.network_address, strict=False)
                if ip not in net:
                    flash('IP not in subnet range.', 'danger')
                    return render_template('ip_form.html', form=form,
                                           subnet=subnet, ip_entry=ip_entry)
            except ValueError:
                flash('Invalid IP address.', 'danger')
                return render_template('ip_form.html', form=form,
                                       subnet=subnet, ip_entry=ip_entry)
            if IPAddress.query.filter(
                IPAddress.subnet_id == subnet.id,
                IPAddress.ip_address == ip_str,
                IPAddress.id != ip_id).first():
                flash('Another entry with this IP exists.', 'danger')
                return render_template('ip_form.html', form=form,
                                       subnet=subnet, ip_entry=ip_entry)

        # Simpan nilai lama untuk audit
        old_values = {
            'ip_address': ip_entry.ip_address,
            'status': ip_entry.status,
            'hostname': ip_entry.hostname,
            'mac_address': ip_entry.mac_address,
            'device_type': ip_entry.device_type,
            'assigned_to': ip_entry.assigned_to,
            'description': ip_entry.description
        }

        ip_entry.ip_address = ip_str
        ip_entry.status = form.status.data
        ip_entry.hostname = form.hostname.data
        ip_entry.mac_address = form.mac_address.data
        ip_entry.device_type = form.device_type.data
        ip_entry.assigned_to = form.assigned_to.data
        ip_entry.description = form.description.data
        db.session.commit()

        # Bandingkan perubahan
        new_values = {
            'ip_address': ip_entry.ip_address,
            'status': ip_entry.status,
            'hostname': ip_entry.hostname,
            'mac_address': ip_entry.mac_address,
            'device_type': ip_entry.device_type,
            'assigned_to': ip_entry.assigned_to,
            'description': ip_entry.description
        }
        changes = {}
        for key in old_values:
            if str(old_values[key]) != str(new_values[key]):
                changes[key] = {'old': str(old_values[key]), 'new': str(new_values[key])}
        if changes:
            log_change('UPDATE', 'IPAddress', ip_entry.id, changes)

        log_activity(f'Updated IP {ip_str} in {subnet.name}')

        send_webhook('ip_updated', {
            'ip': ip_entry.ip_address,
            'subnet': subnet.name,
            'user': current_user.username
        })

        # Cek notifikasi setelah perubahan (misal status berubah)
        check_and_alert(subnet)

        flash('IP updated.', 'success')
        return redirect(url_for('subnets.subnet_detail', subnet_id=subnet.id))

    elif request.method == 'GET':
        form.ip_address.data = ip_entry.ip_address
        form.status.data = ip_entry.status
        form.hostname.data = ip_entry.hostname
        form.mac_address.data = ip_entry.mac_address
        form.device_type.data = ip_entry.device_type
        form.assigned_to.data = ip_entry.assigned_to
        form.description.data = ip_entry.description
    return render_template('ip_form.html', form=form, subnet=subnet,
                           ip_entry=ip_entry, legend='Edit IP Address')


@ips_bp.route('/delete/<int:ip_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager', 'operator')
def delete_ip(ip_id):
    ip_entry = IPAddress.query.get_or_404(ip_id)
    subnet = ip_entry.subnet   # ambil subnet sebelum dihapus
    subnet_id = ip_entry.subnet_id

    # Simpan data untuk audit sebelum dihapus
    old_data = {
        'ip': ip_entry.ip_address,
        'status': ip_entry.status,
        'hostname': ip_entry.hostname,
        'mac': ip_entry.mac_address,
        'device_type': ip_entry.device_type,
        'assigned_to': ip_entry.assigned_to,
        'description': ip_entry.description
    }

    db.session.delete(ip_entry)
    db.session.commit()

    log_activity(f'Deleted IP {ip_entry.ip_address}')
    log_change('DELETE', 'IPAddress', ip_id, old_data)

    send_webhook('ip_deleted', {
        'ip': ip_entry.ip_address,
        'subnet': subnet.name,
        'user': current_user.username
    })

    # Cek notifikasi setelah penghapusan
    check_and_alert(subnet)

    flash('IP deleted.', 'success')
    return redirect(url_for('subnets.subnet_detail', subnet_id=subnet_id))