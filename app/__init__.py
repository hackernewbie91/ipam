import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, Markup, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_mail import Mail
from wtforms import PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Optional
import click
import json
from app.scheduler import start_auto_scan, stop_auto_scan

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()
mail = Mail()

def create_app(config_class=None):
    if config_class is None:
        from config import Config
        config_class = Config

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.subnets import subnets_bp
    from app.routes.ips import ips_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(subnets_bp, url_prefix='/subnets')
    app.register_blueprint(ips_bp, url_prefix='/ips')
    app.register_blueprint(api_bp, url_prefix='/api')
    csrf.exempt(api_bp)   # Hanya API yang dikecualikan

    # Inisialisasi auto scan jika diaktifkan
    from app.utils import get_setting
    with app.app_context():
        auto_scan_enabled = get_setting('auto_scan_enabled', 'false') == 'true'
        auto_scan_interval = int(get_setting('auto_scan_interval', app.config.get('AUTO_SCAN_INTERVAL', 30)))
        if auto_scan_enabled:
            start_auto_scan(app, auto_scan_interval)

    # ========== ADMIN PANEL ==========
    admin = Admin(app, name='IPAM Admin', template_mode='bootstrap4', url='/admin')

    from app.models import User, ActivityLog

    class UserAdmin(ModelView):
    # List view
        column_list = ('username', 'email', 'role', 'created_at')
        column_exclude_list = ('password_hash',)
        column_searchable_list = ('username', 'email')
        column_filters = ('role',)

        # Sertakan role dan password di form
        form_columns = ('username', 'email', 'role', 'password')

        # Definisikan role dan password sebagai field manual
        form_extra_fields = {
            'role': SelectField('Role', choices=[
                ('admin', 'Admin'),
                ('manager', 'Manager'),
                ('operator', 'Operator'),
                ('viewer', 'Viewer')
            ], default='viewer'),
            'password': PasswordField('Password')
        }

        # Badge role
        def _role_formatter(view, context, model, name):
            role = model.role
            badge_class = {
                'admin': 'danger',
                'manager': 'warning',
                'operator': 'info',
                'viewer': 'secondary'
            }.get(role, 'light')
            return Markup(f'<span class="badge bg-{badge_class}">{role.capitalize()}</span>')

        column_formatters = {'role': _role_formatter}

        # Set model saat create/edit
        def on_model_change(self, form, model, is_created):
            model.username = form.username.data
            model.email = form.email.data
            model.role = form.role.data
            if form.password.data:
                model.set_password(form.password.data)

        # Proteksi admin terakhir
        def delete_model(self, model):
            if model.role == 'admin':
                if User.query.filter_by(role='admin').count() <= 1:
                    flash('Cannot delete the last admin user.', 'error')
                    return False
            return super().delete_model(model)

    class ActivityLogAdmin(ModelView):
        can_create = False
        can_edit = False
        can_delete = False
        column_list = ('timestamp', 'user', 'action', 'object_type', 'object_id', 'changes')
        column_default_sort = ('timestamp', True)

        # Format changes supaya lebih mudah dibaca
        def _changes_formatter(view, context, model, name):
            if not model.changes:
                return Markup('-')
            try:
                data = json.loads(model.changes)
                html = '<pre style="max-width:300px; white-space:pre-wrap;">' + json.dumps(data, indent=2) + '</pre>'
                return Markup(html)
            except Exception:
                return Markup(model.changes)

        column_formatters = {
            'changes': _changes_formatter
        }

    admin.add_view(UserAdmin(User, db.session, name='Users', endpoint='users'))
    admin.add_view(ActivityLogAdmin(ActivityLog, db.session, name='Activity Log', endpoint='activitylog'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Logging
    if not app.debug and not app.testing:
        if app.config.get('LOG_TO_STDOUT'):
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/ipam.log',
                                               maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('IPAM startup')

    # CLI command untuk membuat admin
    @app.cli.command('create-admin')
    @click.argument('username')
    @click.argument('email')
    @click.argument('password')
    def create_admin(username, email, password):
        """Buat user admin baru."""
        from app.models import User
        user = User(username=username, email=email, is_admin=True, role='admin')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f'Admin user {username} created.')

    # CLI command untuk scan semua subnet
    @app.cli.command('scan')
    def scan_command():
        """Scan all subnets for live hosts."""
        from app.scanner import scan_all_subnets
        result = scan_all_subnets()
        print(f"Scanned {result['subnets_scanned']} subnets.")
        print(f"Online: {result['total_online']}, Offline: {result['total_offline']}")

    @app.context_processor
    def inject_settings():
        from app.utils import get_setting
        return dict(get_setting=get_setting)

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

