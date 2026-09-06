from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import PortMapping, IPAddress
from app.forms import PortMappingForm
from app.utils import role_required, log_change
import ipaddress

port_mapping_bp = Blueprint('port_mapping', __name__, url_prefix='/port-mapping')

@port_mapping_bp.route('/')
@login_required
def list_port_mappings():
    page = request.args.get('page', 1, type=int)
    mappings = PortMapping.query.order_by(PortMapping.switch_name, PortMapping.port_number).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('port_mapping_list.html', mappings=mappings)

@port_mapping_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'operator')
def create_port_mapping():
    form = PortMappingForm()
    if form.validate_on_submit():
        ip_obj = None
        if form.ip_address.data:
            try:
                ipaddress.ip_address(form.ip_address.data)
            except ValueError:
                flash('Invalid IP address format.', 'danger')
                return render_template('port_mapping_form.html', form=form, legend='Create Port Mapping')
            ip_obj = IPAddress.query.filter_by(ip_address=form.ip_address.data).first()
            if not ip_obj:
                flash('IP address not found in IPAM. Please add the IP first.', 'warning')
                return render_template('port_mapping_form.html', form=form, legend='Create Port Mapping')

        existing = PortMapping.query.filter_by(switch_name=form.switch_name.data, port_number=form.port_number.data).first()
        if existing:
            flash('Port already mapped for this switch.', 'danger')
            return render_template('port_mapping_form.html', form=form, legend='Create Port Mapping')

        mapping = PortMapping(
            switch_name=form.switch_name.data,
            port_number=form.port_number.data,
            ip_address_id=ip_obj.id if ip_obj else None,
            device_name=form.device_name.data,
            vlan=form.vlan.data,
            status=form.status.data,
            description=form.description.data
        )
        db.session.add(mapping)
        db.session.commit()
        log_change('CREATE', 'PortMapping', mapping.id, {
            'switch': mapping.switch_name,
            'port': mapping.port_number,
            'ip': form.ip_address.data or '',
            'device': mapping.device_name or '',
            'vlan': mapping.vlan or '',
            'status': mapping.status
        })
        flash('Port mapping created successfully.', 'success')
        return redirect(url_for('port_mapping.list_port_mappings'))
    return render_template('port_mapping_form.html', form=form, legend='Create Port Mapping')

@port_mapping_bp.route('/<int:mapping_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'operator')
def edit_port_mapping(mapping_id):
    mapping = PortMapping.query.get_or_404(mapping_id)
    form = PortMappingForm(obj=mapping)
    if mapping.ip_address:
        form.ip_address.data = mapping.ip_address.ip_address
    if form.validate_on_submit():
        ip_obj = None
        if form.ip_address.data:
            try:
                ipaddress.ip_address(form.ip_address.data)
            except ValueError:
                flash('Invalid IP address format.', 'danger')
                return render_template('port_mapping_form.html', form=form, legend='Edit Port Mapping', mapping=mapping)
            ip_obj = IPAddress.query.filter_by(ip_address=form.ip_address.data).first()
            if not ip_obj:
                flash('IP address not found in IPAM.', 'warning')
                return render_template('port_mapping_form.html', form=form, legend='Edit Port Mapping', mapping=mapping)

        existing = PortMapping.query.filter(
            PortMapping.switch_name == form.switch_name.data,
            PortMapping.port_number == form.port_number.data,
            PortMapping.id != mapping.id
        ).first()
        if existing:
            flash('Port already mapped for this switch.', 'danger')
            return render_template('port_mapping_form.html', form=form, legend='Edit Port Mapping', mapping=mapping)

        old_values = {
            'switch': mapping.switch_name,
            'port': mapping.port_number,
            'ip': mapping.ip_address.ip_address if mapping.ip_address else '',
            'device': mapping.device_name or '',
            'vlan': mapping.vlan or '',
            'status': mapping.status
        }
        mapping.switch_name = form.switch_name.data
        mapping.port_number = form.port_number.data
        mapping.ip_address_id = ip_obj.id if ip_obj else None
        mapping.device_name = form.device_name.data
        mapping.vlan = form.vlan.data
        mapping.status = form.status.data
        mapping.description = form.description.data
        db.session.commit()

        new_values = {
            'switch': mapping.switch_name,
            'port': mapping.port_number,
            'ip': mapping.ip_address.ip_address if mapping.ip_address else '',
            'device': mapping.device_name or '',
            'vlan': mapping.vlan or '',
            'status': mapping.status
        }
        changes = {}
        for key in old_values:
            if str(old_values[key]) != str(new_values[key]):
                changes[key] = {'old': str(old_values[key]), 'new': str(new_values[key])}
        if changes:
            log_change('UPDATE', 'PortMapping', mapping.id, changes)
        flash('Port mapping updated.', 'success')
        return redirect(url_for('port_mapping.list_port_mappings'))
    return render_template('port_mapping_form.html', form=form, legend='Edit Port Mapping', mapping=mapping)

@port_mapping_bp.route('/<int:mapping_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def delete_port_mapping(mapping_id):
    mapping = PortMapping.query.get_or_404(mapping_id)
    old_data = {
        'switch': mapping.switch_name,
        'port': mapping.port_number,
        'ip': mapping.ip_address.ip_address if mapping.ip_address else '',
        'device': mapping.device_name or '',
        'vlan': mapping.vlan or '',
        'status': mapping.status
    }
    db.session.delete(mapping)
    db.session.commit()
    log_change('DELETE', 'PortMapping', mapping_id, old_data)
    flash('Port mapping deleted.', 'success')
    return redirect(url_for('port_mapping.list_port_mappings'))
