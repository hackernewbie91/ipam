from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import DNSServer
from app.forms import DNSServerForm
from app.utils import role_required, log_change
from app.dns_providers import get_provider

dns_servers_bp = Blueprint('dns_servers', __name__, url_prefix='/dns-servers')

@dns_servers_bp.route('/')
@login_required
def list_dns_servers():
    servers = DNSServer.query.all()
    return render_template('dns_server_list.html', servers=servers)

@dns_servers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_dns_server():
    form = DNSServerForm()
    if form.validate_on_submit():
        server = DNSServer(
            name=form.name.data,
            provider=form.provider.data,
            host=form.host.data,
            port=form.port.data,
            username=form.username.data,
            password=form.password.data,
            api_url=form.api_url.data,
            api_key=form.api_key.data,
            zone_name=form.zone_name.data,
            reverse_zone=form.reverse_zone.data,
            is_active=form.is_active.data
        )
        db.session.add(server)
        db.session.commit()
        log_change('CREATE', 'DNSServer', server.id, {'name': server.name, 'provider': server.provider})
        flash('DNS Server created successfully.', 'success')
        return redirect(url_for('dns_servers.list_dns_servers'))
    return render_template('dns_server_form.html', form=form, legend='Create DNS Server')

@dns_servers_bp.route('/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_dns_server(server_id):
    server = DNSServer.query.get_or_404(server_id)
    form = DNSServerForm(obj=server)
    if form.validate_on_submit():
        server.name = form.name.data
        server.provider = form.provider.data
        server.host = form.host.data
        server.port = form.port.data
        server.username = form.username.data
        if form.password.data:
            server.password = form.password.data
        server.api_url = form.api_url.data
        server.api_key = form.api_key.data
        server.zone_name = form.zone_name.data
        server.reverse_zone = form.reverse_zone.data
        server.is_active = form.is_active.data
        db.session.commit()
        log_change('UPDATE', 'DNSServer', server.id, {'name': server.name})
        flash('DNS Server updated.', 'success')
        return redirect(url_for('dns_servers.list_dns_servers'))
    return render_template('dns_server_form.html', form=form, legend='Edit DNS Server')

@dns_servers_bp.route('/<int:server_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_dns_server(server_id):
    server = DNSServer.query.get_or_404(server_id)
    db.session.delete(server)
    db.session.commit()
    log_change('DELETE', 'DNSServer', server_id, {'name': server.name})
    flash('DNS Server deleted.', 'success')
    return redirect(url_for('dns_servers.list_dns_servers'))

@dns_servers_bp.route('/<int:server_id>/test', methods=['POST'])
@login_required
@role_required('admin')
def test_dns_server(server_id):
    server = DNSServer.query.get_or_404(server_id)
    provider = get_provider(server)
    if provider:
        result = provider.test_connection()
        if result:
            flash('Connection successful!', 'success')
        else:
            flash('Connection failed!', 'danger')
    else:
        flash('Provider not supported.', 'danger')
    return redirect(url_for('dns_servers.list_dns_servers'))

@dns_servers_bp.route('/<int:server_id>/records')
@login_required
@role_required('admin')
def view_dns_records(server_id):
    """Lihat record DNS dan bandingkan dengan IPAM."""
    server = DNSServer.query.get_or_404(server_id)
    provider = get_provider(server)
    
    if not provider:
        flash('Provider not supported.', 'danger')
        return redirect(url_for('dns_servers.list_dns_servers'))
    
    # Ambil records dari DNS server
    dns_records_raw = provider.get_a_records()
    
    # Ambil data IP dari IPAM yang punya hostname
    from app.models import IPAddress
    ipam_records = IPAddress.query.filter(IPAddress.hostname.isnot(None), IPAddress.hostname != '').all()
    ipam_data = []
    for ip in ipam_records:
        ipam_data.append({
            'hostname': ip.hostname,
            'ip': ip.ip_address,
            'subnet': ip.subnet.name if ip.subnet else ''
        })
    
    return render_template('dns_records.html', 
                           server=server, 
                           dns_records_raw=dns_records_raw,
                           ipam_data=ipam_data)
