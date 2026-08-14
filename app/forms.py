from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, TextAreaField,
                     IntegerField, SelectField, SubmitField)
from wtforms.validators import DataRequired, Email, Optional, ValidationError, Length, EqualTo
import ipaddress

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class SubnetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    network_address = StringField('Network Address (CIDR)',
                                  validators=[DataRequired(), Length(max=18)])
    description = TextAreaField('Description')
    vlan = IntegerField('VLAN ID', validators=[Optional()])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    gateway = StringField('Gateway', validators=[Optional(), Length(max=15)])
    dns_servers = StringField('DNS Servers', validators=[Optional(), Length(max=100)])
    alert_threshold = IntegerField('Alert Threshold (%)', validators=[Optional()], default=80,
                                   description='Kirim notifikasi saat utilisasi mencapai nilai ini')
    submit = SubmitField('Save')

    def validate_network_address(self, field):
        try:
            network = ipaddress.ip_network(field.data, strict=False)
            if network.prefixlen < 8 or network.prefixlen > 30:
                raise ValidationError('Prefix length must be between /8 and /30.')
        except ValueError:
            raise ValidationError('Invalid network address. Use CIDR notation.')

class IPAddressForm(FlaskForm):
    ip_address = StringField('IP Address', validators=[DataRequired(), Length(max=15)])
    status = SelectField('Status', choices=[
        ('allocated', 'Allocated'), ('reserved', 'Reserved'),
        ('available', 'Available')], default='allocated')
    hostname = StringField('Hostname', validators=[Optional(), Length(max=255)])
    mac_address = StringField('MAC Address', validators=[Optional(), Length(max=17)])
    device_type = StringField('Device Type', validators=[Optional(), Length(max=50)])
    assigned_to = StringField('Assigned To', validators=[Optional(), Length(max=100)])
    description = TextAreaField('Description')
    submit = SubmitField('Save')

    def validate_ip_address(self, field):
        try:
            ipaddress.ip_address(field.data)
        except ValueError:
            raise ValidationError('Invalid IP address.')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')