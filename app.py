from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import threading

# Flask uygulaması oluştur
app = Flask(__name__, 
            static_folder='dash/assets',
            template_folder='dash')

# Konfigürasyon
app.config['SECRET_KEY'] = 'pcba-test-system-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pcba_test_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Performance optimizations
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,  # 5 dakika
    'pool_timeout': 20,
    'max_overflow': 0
}

# Uzantıları başlat
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Kullanıcı yükleme callback'i
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Template context processor - tüm template'lerde current_user kullanılabilir yapar
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Veritabanı Modelleri
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')  # Keep for backward compatibility
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)  # New dynamic role system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations
    assigned_role = db.relationship('Role', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        # Cache permissions in session to avoid repeated DB queries
        if not hasattr(self, '_cached_permissions'):
            self._cached_permissions = self._load_all_permissions()
        
        # Check if permission exists in cached permissions
        return permission_name in self._cached_permissions
    
    def _load_all_permissions(self):
        """Load all effective permissions for this user"""
        permissions = set()
        
        # Get role permissions
        if self.assigned_role:
            permissions.update([p.name for p in self.assigned_role.permissions])
        
        # Get individual permissions
        user_perms = UserPermission.query.filter_by(user_id=self.id).all()
        for up in user_perms:
            if up.granted:
                permissions.add(up.permission.name)
            else:
                # Individual denial overrides role permission
                permissions.discard(up.permission.name)
        
        # Fallback to legacy role system for backward compatibility
        if self.role == 'admin':
            # Admin has all permissions
            all_permissions = Permission.query.all()
            permissions.update([p.name for p in all_permissions])
        elif self.role in ['admin', 'technician']:
            # Add basic view permissions for technicians
            view_permissions = Permission.query.filter(Permission.name.like('view_%')).all()
            permissions.update([p.name for p in view_permissions])
            
        return permissions
    
    def clear_permission_cache(self):
        """Clear cached permissions - call when permissions change"""
        if hasattr(self, '_cached_permissions'):
            delattr(self, '_cached_permissions')
    
    def get_permissions(self):
        """Get all permissions for this user"""
        permissions = set()
        
        # Get role permissions
        if self.assigned_role:
            permissions.update([p.name for p in self.assigned_role.permissions])
        
        # Get individual permissions
        user_perms = UserPermission.query.filter_by(user_id=self.id).all()
        for up in user_perms:
            if up.granted:
                permissions.add(up.permission.name)
            else:
                permissions.discard(up.permission.name)  # Deny permission
        
        return list(permissions)

class TestType(db.Model):
    __tablename__ = 'test_type'
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(20), unique=True, nullable=False)  # ICT, FCT, AOI, etc.
    type_name = db.Column(db.String(100), nullable=False)  # In-Circuit Test, etc.
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestScenario(db.Model):
    __tablename__ = 'test_scenario'
    id = db.Column(db.Integer, primary_key=True)
    scenario_name = db.Column(db.String(100), nullable=False)
    test_parameters = db.Column(db.JSON)  # Test parametreleri JSON formatında
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PCBAModel(db.Model):
    __tablename__ = 'pcba_model'
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    part_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    test_scenario_id = db.Column(db.Integer, db.ForeignKey('test_scenario.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # İlişkiler
    test_scenario = db.relationship('TestScenario', backref=db.backref('pcba_models', lazy=True))

class TestResult(db.Model):
    __tablename__ = 'test_result'
    id = db.Column(db.Integer, primary_key=True)
    pcba_model_id = db.Column(db.Integer, db.ForeignKey('pcba_model.id'), nullable=False)
    test_type_id = db.Column(db.Integer, db.ForeignKey('test_type.id'), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    test_status = db.Column(db.String(20), nullable=False)  # PASS, FAIL, SKIP
    test_data = db.Column(db.JSON)  # Detaylı test sonuçları
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    test_duration = db.Column(db.Float)  # Saniye cinsinden
    notes = db.Column(db.Text)

    # İlişkiler
    pcba_model = db.relationship('PCBAModel', backref=db.backref('test_results', lazy=True))
    test_type = db.relationship('TestType', backref=db.backref('test_results', lazy=True))
    operator = db.relationship('User', backref=db.backref('test_results', lazy=True))

class Connection(db.Model):
    __tablename__ = 'connections'
    id = db.Column(db.Integer, primary_key=True)
    connection_name = db.Column(db.String(100), nullable=False)
    protocol_type = db.Column(db.String(20), nullable=False)  # 'MODBUS_RTU' or 'MODBUS_TCP'
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Modbus RTU Parameters
    serial_port = db.Column(db.String(20))  # COM1, COM2, etc.
    baud_rate = db.Column(db.Integer)  # 9600, 19200, 38400, 115200
    data_bits = db.Column(db.Integer, default=8)  # 7, 8
    parity = db.Column(db.String(10), default='NONE')  # NONE, EVEN, ODD
    stop_bits = db.Column(db.Integer, default=1)  # 1, 2
    modbus_address = db.Column(db.Integer)  # 1-247
    
    # Modbus TCP Parameters
    ip_address = db.Column(db.String(15))  # IP address
    port = db.Column(db.Integer, default=502)  # Modbus TCP port
    gateway_address = db.Column(db.String(15))  # Gateway IP
    subnet_mask = db.Column(db.String(15))  # Subnet mask
    timeout = db.Column(db.Integer, default=5000)  # Connection timeout in ms
    
    # Additional parameters
    connection_parameters = db.Column(db.JSON)  # Additional flexible parameters

# Permission Management Models
class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'view_users', 'manage_tests'
    description = db.Column(db.String(200))
    module = db.Column(db.String(50))  # e.g., 'user_management', 'test_management'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # admin, technician, operator
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Association table for many-to-many relationship between roles and permissions
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class UserPermission(db.Model):
    __tablename__ = 'user_permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    granted = db.Column(db.Boolean, default=True)  # True for grant, False for deny
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref='user_permissions')
    permission = db.relationship('Permission', backref='user_permissions')
    granted_by_user = db.relationship('User', foreign_keys=[granted_by])

# Add relationships to existing models
Role.permissions = db.relationship('Permission', secondary=role_permissions, backref='roles')

# Communication Logging Models
class CommunicationLog(db.Model):
    __tablename__ = 'communication_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection_configs.id'), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'sent', 'received'
    data_hex = db.Column(db.Text)
    data_ascii = db.Column(db.Text)
    data_size = db.Column(db.Integer)
    is_error = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.String(500))
    response_time = db.Column(db.Float)  # milliseconds
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    connection = db.relationship('ConnectionConfig', backref='communication_logs')
    user = db.relationship('User', backref='communication_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'connection_id': self.connection_id,
            'connection_name': self.connection.name if self.connection else None,
            'direction': self.direction,
            'data_hex': self.data_hex,
            'data_ascii': self.data_ascii,
            'data_size': self.data_size,
            'is_error': self.is_error,
            'error_message': self.error_message,
            'response_time': self.response_time,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None
        }

class ConnectionConfig(db.Model):
    __tablename__ = 'connection_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    connection_type = db.Column(db.String(20), nullable=False)  # 'serial', 'tcp'
    is_active = db.Column(db.Boolean, default=True)
    
    # Serial Port Settings
    port = db.Column(db.String(50))
    baud_rate = db.Column(db.Integer, default=9600)
    data_bits = db.Column(db.Integer, default=8)
    stop_bits = db.Column(db.Integer, default=1)
    parity = db.Column(db.String(10), default='none')
    
    # TCP Settings
    ip_address = db.Column(db.String(15))
    tcp_port = db.Column(db.Integer)
    timeout = db.Column(db.Integer, default=5000)  # milliseconds
    
    # Status
    is_connected = db.Column(db.Boolean, default=False)
    last_connected = db.Column(db.DateTime)
    connection_duration = db.Column(db.Integer, default=0)  # seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'connection_type': self.connection_type,
            'is_active': self.is_active,
            'port': self.port,
            'baud_rate': self.baud_rate,
            'data_bits': self.data_bits,
            'stop_bits': self.stop_bits,
            'parity': self.parity,
            'ip_address': self.ip_address,
            'tcp_port': self.tcp_port,
            'timeout': self.timeout,
            'is_connected': self.is_connected,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'connection_duration': self.connection_duration,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ConnectionStatistics(db.Model):
    __tablename__ = 'connection_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection_configs.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date())
    bytes_sent = db.Column(db.BigInteger, default=0)
    bytes_received = db.Column(db.BigInteger, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    messages_received = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    avg_response_time = db.Column(db.Float, default=0)
    
    # Relationship
    connection = db.relationship('ConnectionConfig', backref='statistics')
    
    def to_dict(self):
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'connection_name': self.connection.name if self.connection else None,
            'date': self.date.isoformat() if self.date else None,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'errors_count': self.errors_count,
            'avg_response_time': self.avg_response_time
        }

# Automated Test Execution Models
class TestExecution(db.Model):
    __tablename__ = 'test_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    test_scenario_id = db.Column(db.Integer, db.ForeignKey('test_scenario.id'), nullable=False)
    pcba_model_id = db.Column(db.Integer, db.ForeignKey('pcba_model.id'), nullable=False)
    serial_number = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    execution_type = db.Column(db.String(20), nullable=False, default='MANUAL')  # MANUAL, SCHEDULED
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(100), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    test_data = db.Column(db.JSON, nullable=True)  # Real-time test measurements
    final_result = db.Column(db.String(20), nullable=True)  # PASS, FAIL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test_scenario = db.relationship('TestScenario', backref='executions')
    pcba_model = db.relationship('PCBAModel', backref='executions')
    user = db.relationship('User', backref='test_executions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'test_scenario_id': self.test_scenario_id,
            'test_scenario_name': self.test_scenario.scenario_name if self.test_scenario else None,
            'pcba_model_id': self.pcba_model_id,
            'pcba_model_name': self.pcba_model.model_name if self.pcba_model else None,
            'serial_number': self.serial_number,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'execution_type': self.execution_type,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'progress': self.progress,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'test_data': self.test_data,
            'final_result': self.final_result,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ScheduledTest(db.Model):
    __tablename__ = 'scheduled_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    test_scenario_id = db.Column(db.Integer, db.ForeignKey('test_scenario.id'), nullable=False)
    pcba_model_id = db.Column(db.Integer, db.ForeignKey('pcba_model.id'), nullable=False)
    schedule_type = db.Column(db.String(20), nullable=False)  # ONCE, DAILY, WEEKLY, MONTHLY
    schedule_time = db.Column(db.Time, nullable=False)  # Time of day to run
    schedule_days = db.Column(db.String(20), nullable=True)  # For weekly: "1,3,5" (Monday, Wednesday, Friday)
    schedule_date = db.Column(db.Date, nullable=True)  # For ONCE type
    next_run = db.Column(db.DateTime, nullable=True)
    last_run = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_emails = db.Column(db.Text, nullable=True)  # Comma-separated emails
    serial_number_prefix = db.Column(db.String(20), nullable=True)  # Auto-generated serial numbers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test_scenario = db.relationship('TestScenario', backref='scheduled_tests')
    pcba_model = db.relationship('PCBAModel', backref='scheduled_tests')
    creator = db.relationship('User', backref='created_scheduled_tests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'test_scenario_id': self.test_scenario_id,
            'test_scenario_name': self.test_scenario.scenario_name if self.test_scenario else None,
            'pcba_model_id': self.pcba_model_id,
            'pcba_model_name': self.pcba_model.model_name if self.pcba_model else None,
            'schedule_type': self.schedule_type,
            'schedule_time': self.schedule_time.strftime('%H:%M') if self.schedule_time else None,
            'schedule_days': self.schedule_days,
            'schedule_date': self.schedule_date.isoformat() if self.schedule_date else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'notification_emails': self.notification_emails,
            'serial_number_prefix': self.serial_number_prefix,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TestConfiguration(db.Model):
    __tablename__ = 'test_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(20), nullable=False, default='STRING')  # STRING, INTEGER, BOOLEAN, JSON, FLOAT
    category = db.Column(db.String(50), nullable=False, default='GENERAL')  # GENERAL, TIMEOUT, RETRY, NOTIFICATION, LOGGING
    is_system = db.Column(db.Boolean, default=False)  # System configs cannot be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'data_type': self.data_type,
            'category': self.category,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_typed_value(self):
        """Return value converted to appropriate type"""
        if self.data_type == 'INTEGER':
            return int(self.value)
        elif self.data_type == 'FLOAT':
            return float(self.value)
        elif self.data_type == 'BOOLEAN':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'JSON':
            import json
            return json.loads(self.value)
        else:
            return self.value

# Permission decorator
def require_permission(permission_name):
    """Decorator to require specific permission for route access"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission_name):
                flash(f'Bu sayfaya erişim için "{permission_name}" yetkisine ihtiyacınız var.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Ana sayfa route'ları
@app.route('/')
@login_required
def dashboard():
    # Dashboard için istatistikler
    total_tests = TestResult.query.count()
    passed_tests = TestResult.query.filter_by(test_status='PASS').count()
    failed_tests = TestResult.query.filter_by(test_status='FAIL').count()
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # Son test sonuçları
    recent_tests = TestResult.query.order_by(TestResult.test_date.desc()).limit(10).all()
    
    return render_template('index.html', 
                         total_tests=total_tests,
                         passed_tests=passed_tests,
                         failed_tests=failed_tests,
                         success_rate=success_rate,
                         recent_tests=recent_tests)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Geçersiz kullanıcı adı veya şifre')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/user-settings')
@login_required
def user_settings():
    return render_template('user-settings.html', user=current_user)

@app.route('/system-settings')
@require_permission('manage_system_settings')
def system_settings():
    return render_template('system-settings.html')

@app.route('/test-parameters')
@require_permission('manage_test_parameters')
def test_parameters():
    pcba_models = PCBAModel.query.filter_by(is_active=True).all()
    return render_template('test-parameters.html', pcba_models=pcba_models)

# Test Type Management Routes
@app.route('/test-types')
@require_permission('manage_test_types')
def test_types():
    test_types = TestType.query.all()
    return render_template('test-types.html', test_types=test_types)

@app.route('/add-test-type', methods=['GET', 'POST'])
@require_permission('manage_test_types')
def add_test_type():
    
    if request.method == 'POST':
        type_code = request.form['type_code'].upper()
        type_name = request.form['type_name']
        description = request.form['description']
        
        # Kod benzersizlik kontrolü
        if TestType.query.filter_by(type_code=type_code).first():
            return render_template('add-test-type.html', error='Bu test tipi kodu zaten kullanılıyor')
        
        new_test_type = TestType(
            type_code=type_code,
            type_name=type_name,
            description=description
        )
        
        db.session.add(new_test_type)
        db.session.commit()
        
        return redirect(url_for('test_types'))
    
    return render_template('add-test-type.html')

@app.route('/edit-test-type/<int:test_type_id>', methods=['GET', 'POST'])
@require_permission('manage_test_types')
def edit_test_type(test_type_id):
    
    test_type = TestType.query.get_or_404(test_type_id)
    
    if request.method == 'POST':
        type_code = request.form['type_code'].upper()
        type_name = request.form['type_name']
        description = request.form['description']
        is_active = 'is_active' in request.form
        
        # Kod benzersizlik kontrolü (kendisi hariç)
        existing_type = TestType.query.filter(TestType.type_code == type_code, TestType.id != test_type_id).first()
        if existing_type:
            return render_template('edit-test-type.html', test_type=test_type, error='Bu test tipi kodu zaten kullanılıyor')
        
        test_type.type_code = type_code
        test_type.type_name = type_name
        test_type.description = description
        test_type.is_active = is_active
        
        db.session.commit()
        
        return redirect(url_for('test_types'))
    
    return render_template('edit-test-type.html', test_type=test_type)

@app.route('/delete-test-type/<int:test_type_id>', methods=['POST'])
@require_permission('manage_test_types')
def delete_test_type(test_type_id):
    
    test_type = TestType.query.get_or_404(test_type_id)
    
    # Test sonuçları var mı kontrol et
    if test_type.test_results:
        return jsonify({'success': False, 'message': 'Bu test tipinin mevcut test sonuçları var, silinemez'})
    
    # Test tipini pasif yap (tamamen silmek yerine)
    test_type.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Test tipi başarıyla silindi'})

# Test Scenario Management Routes
@app.route('/test-scenarios')
@login_required
def test_scenarios():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    test_scenarios = TestScenario.query.all()
    return render_template('test-scenarios.html', test_scenarios=test_scenarios)

@app.route('/add-test-scenario', methods=['GET', 'POST'])
@login_required
def add_test_scenario():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        scenario_name = request.form['scenario_name']
        description = request.form['description']
        
        # Test parametrelerini al
        test_parameters = {}
        
        # Voltaj parametreleri
        if request.form.get('voltage_min') and request.form.get('voltage_max'):
            test_parameters['voltage_range'] = {
                'min': float(request.form['voltage_min']),
                'max': float(request.form['voltage_max'])
            }
        
        # Akım parametreleri
        if request.form.get('current_min') and request.form.get('current_max'):
            test_parameters['current_range'] = {
                'min': float(request.form['current_min']),
                'max': float(request.form['current_max'])
            }
        
        # Frekans parametreleri
        if request.form.get('frequency_target') and request.form.get('frequency_tolerance'):
            test_parameters['frequency_test'] = {
                'target': int(request.form['frequency_target']),
                'tolerance': int(request.form['frequency_tolerance'])
            }
        
        new_scenario = TestScenario(
            scenario_name=scenario_name,
            description=description,
            test_parameters=test_parameters
        )
        
        db.session.add(new_scenario)
        db.session.commit()
        
        return redirect(url_for('test_scenarios'))
    
    return render_template('add-test-scenario.html')

@app.route('/edit-test-scenario/<int:scenario_id>', methods=['GET', 'POST'])
@login_required
def edit_test_scenario(scenario_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    scenario = TestScenario.query.get_or_404(scenario_id)
    
    if request.method == 'POST':
        scenario.scenario_name = request.form['scenario_name']
        scenario.description = request.form['description']
        scenario.is_active = 'is_active' in request.form
        
        # Test parametrelerini güncelle
        test_parameters = {}
        
        if request.form.get('voltage_min') and request.form.get('voltage_max'):
            test_parameters['voltage_range'] = {
                'min': float(request.form['voltage_min']),
                'max': float(request.form['voltage_max'])
            }
        
        if request.form.get('current_min') and request.form.get('current_max'):
            test_parameters['current_range'] = {
                'min': float(request.form['current_min']),
                'max': float(request.form['current_max'])
            }
        
        if request.form.get('frequency_target') and request.form.get('frequency_tolerance'):
            test_parameters['frequency_test'] = {
                'target': int(request.form['frequency_target']),
                'tolerance': int(request.form['frequency_tolerance'])
            }
        
        scenario.test_parameters = test_parameters
        db.session.commit()
        
        return redirect(url_for('test_scenarios'))
    
    return render_template('edit-test-scenario.html', scenario=scenario)

@app.route('/delete-test-scenario/<int:scenario_id>', methods=['POST'])
@login_required
def delete_test_scenario(scenario_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    scenario = TestScenario.query.get_or_404(scenario_id)
    
    # PCBA modelleri var mı kontrol et
    if scenario.pcba_models:
        return jsonify({'success': False, 'message': 'Bu senaryoyu kullanan PCBA modelleri var, silinemez'})
    
    scenario.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Test senaryosu başarıyla silindi'})

# PCBA Model Management Routes
@app.route('/pcba-models')
@login_required
def pcba_models():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    pcba_models = PCBAModel.query.all()
    return render_template('pcba-models.html', pcba_models=pcba_models)

@app.route('/add-pcba-model', methods=['GET', 'POST'])
@login_required
def add_pcba_model():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        model_name = request.form['model_name']
        part_number = request.form['part_number']
        description = request.form['description']
        test_scenario_id = request.form.get('test_scenario_id')
        
        # Part number benzersizlik kontrolü
        if PCBAModel.query.filter_by(part_number=part_number).first():
            test_scenarios = TestScenario.query.filter_by(is_active=True).all()
            return render_template('add-pcba-model.html', test_scenarios=test_scenarios, 
                                 error='Bu part numarası zaten kullanılıyor')
        
        new_model = PCBAModel(
            model_name=model_name,
            part_number=part_number,
            description=description,
            test_scenario_id=int(test_scenario_id) if test_scenario_id else None
        )
        
        db.session.add(new_model)
        db.session.commit()
        
        return redirect(url_for('pcba_models'))
    
    test_scenarios = TestScenario.query.filter_by(is_active=True).all()
    return render_template('add-pcba-model.html', test_scenarios=test_scenarios)

@app.route('/edit-pcba-model/<int:model_id>', methods=['GET', 'POST'])
@login_required
def edit_pcba_model(model_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    model = PCBAModel.query.get_or_404(model_id)
    
    if request.method == 'POST':
        part_number = request.form['part_number']
        test_scenario_id = request.form.get('test_scenario_id')
        
        # Part number benzersizlik kontrolü (kendisi hariç)
        existing_model = PCBAModel.query.filter(PCBAModel.part_number == part_number, PCBAModel.id != model_id).first()
        if existing_model:
            test_scenarios = TestScenario.query.filter_by(is_active=True).all()
            return render_template('edit-pcba-model.html', model=model, test_scenarios=test_scenarios,
                                 error='Bu part numarası zaten kullanılıyor')
        
        model.model_name = request.form['model_name']
        model.part_number = part_number
        model.description = request.form['description']
        model.test_scenario_id = int(test_scenario_id) if test_scenario_id else None
        model.is_active = 'is_active' in request.form
        
        db.session.commit()
        
        return redirect(url_for('pcba_models'))
    
    test_scenarios = TestScenario.query.filter_by(is_active=True).all()
    return render_template('edit-pcba-model.html', model=model, test_scenarios=test_scenarios)

@app.route('/delete-pcba-model/<int:model_id>', methods=['POST'])
@login_required
def delete_pcba_model(model_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    model = PCBAModel.query.get_or_404(model_id)
    
    # Test sonuçları var mı kontrol et
    if model.test_results:
        return jsonify({'success': False, 'message': 'Bu modelin mevcut test sonuçları var, silinemez'})
    
    model.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'PCBA modeli başarıyla silindi'})

@app.route('/users')
@require_permission('manage_users')
def users():
    # Eager loading ile role bilgisini de getir
    users = User.query.options(db.joinedload(User.assigned_role)).all()
    return render_template('users.html', users=users)

@app.route('/add-user', methods=['GET', 'POST'])
@require_permission('manage_users')
def add_user():
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Kullanıcı adı benzersizlik kontrolü
        if User.query.filter_by(username=username).first():
            return render_template('add-user.html', error='Bu kullanıcı adı zaten kullanılıyor')
        
        # E-posta benzersizlik kontrolü
        if User.query.filter_by(email=email).first():
            return render_template('add-user.html', error='Bu e-posta adresi zaten kullanılıyor')
        
        # Yeni kullanıcı oluştur
        new_user = User(
            username=username,
            email=email,
            role=role
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('users'))
    
    return render_template('add-user.html')

@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@require_permission('manage_users')
def edit_user(user_id):
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        is_active = 'is_active' in request.form
        
        # E-posta benzersizlik kontrolü (kendisi hariç)
        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            return render_template('edit-user.html', user=user, error='Bu e-posta adresi zaten kullanılıyor')
        
        user.email = email
        user.role = role
        user.is_active = is_active
        
        # Şifre değiştirilmek isteniyorsa
        if request.form.get('new_password'):
            user.set_password(request.form['new_password'])
        
        db.session.commit()
        
        return redirect(url_for('users'))
    
    return render_template('edit-user.html', user=user)

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@require_permission('manage_users')
def delete_user(user_id):
    
    user = User.query.get_or_404(user_id)
    
    # Kendi hesabını silemez
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Kendi hesabınızı silemezsiniz'})
    
    # Kullanıcıyı pasif yap (tamamen silmek yerine)
    user.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Kullanıcı başarıyla silindi'})

# Test Operations Routes
@app.route('/test-operations')
@login_required
def test_operations():
    # Aktif PCBA modelleri ve test tiplerini getir
    pcba_models = PCBAModel.query.filter_by(is_active=True).all()
    test_types = TestType.query.filter_by(is_active=True).all()
    
    # Kullanıcının son kullandığı test ayarlarını getir
    last_test = TestResult.query.filter_by(operator_id=current_user.id).order_by(TestResult.test_date.desc()).first()
    last_pcba_model_id = last_test.pcba_model_id if last_test else None
    last_test_type_id = last_test.test_type_id if last_test else None
    
    return render_template('test-operations.html', 
                         pcba_models=pcba_models,
                         test_types=test_types,
                         last_pcba_model_id=last_pcba_model_id,
                         last_test_type_id=last_test_type_id)

@app.route('/api/run-test', methods=['POST'])
@login_required
def api_run_test():
    try:
        data = request.get_json()
        pcba_model_id = data.get('pcba_model_id')
        serial_number = data.get('serial_number')
        test_type_id = data.get('test_type_id')
        
        if not all([pcba_model_id, serial_number, test_type_id]):
            return jsonify({'success': False, 'message': 'Tüm alanlar gerekli'})
        
        # PCBA modeli kontrol et
        pcba_model = PCBAModel.query.get(pcba_model_id)
        if not pcba_model:
            return jsonify({'success': False, 'message': 'PCBA modeli bulunamadı'})
        
        # Test tipi kontrol et
        test_type = TestType.query.get(test_type_id)
        if not test_type:
            return jsonify({'success': False, 'message': 'Test tipi bulunamadı'})
        
        # Seri numarası benzersizlik kontrolü (aynı test tipi için)
        existing_test = TestResult.query.filter_by(
            serial_number=serial_number,
            test_type_id=test_type_id,
            pcba_model_id=pcba_model_id
        ).first()
        
        if existing_test:
            return jsonify({'success': False, 'message': 'Bu seri numarası ve test tipi için zaten test mevcut'})
        
        # Test simülasyonu (gerçek test yerine)
        import random
        import time
        
        # Test parametrelerini test senaryosundan al
        test_params = {}
        if pcba_model.test_scenario:
            test_params = pcba_model.test_scenario.test_parameters or {}
        
        # Test sonuçlarını simüle et
        test_results = {}
        test_status = 'PASS'
        
        # Voltaj testi
        if 'voltage_range' in test_params:
            voltage_range = test_params['voltage_range']
            measured_voltage = round(random.uniform(
                voltage_range['min'] - 0.1, 
                voltage_range['max'] + 0.1
            ), 2)
            test_results['voltage'] = {
                'measured': measured_voltage,
                'expected_min': voltage_range['min'],
                'expected_max': voltage_range['max'],
                'status': 'PASS' if voltage_range['min'] <= measured_voltage <= voltage_range['max'] else 'FAIL'
            }
            if test_results['voltage']['status'] == 'FAIL':
                test_status = 'FAIL'
        
        # Akım testi
        if 'current_range' in test_params:
            current_range = test_params['current_range']
            measured_current = round(random.uniform(
                current_range['min'] - 0.05, 
                current_range['max'] + 0.05
            ), 3)
            test_results['current'] = {
                'measured': measured_current,
                'expected_min': current_range['min'],
                'expected_max': current_range['max'],
                'status': 'PASS' if current_range['min'] <= measured_current <= current_range['max'] else 'FAIL'
            }
            if test_results['current']['status'] == 'FAIL':
                test_status = 'FAIL'
        
        # Frekans testi
        if 'frequency_test' in test_params:
            freq_test = test_params['frequency_test']
            measured_freq = random.randint(
                freq_test['target'] - freq_test['tolerance'] - 5,
                freq_test['target'] + freq_test['tolerance'] + 5
            )
            test_results['frequency'] = {
                'measured': measured_freq,
                'expected': freq_test['target'],
                'tolerance': freq_test['tolerance'],
                'status': 'PASS' if abs(measured_freq - freq_test['target']) <= freq_test['tolerance'] else 'FAIL'
            }
            if test_results['frequency']['status'] == 'FAIL':
                test_status = 'FAIL'
        
        # Test süresini simüle et
        test_duration = round(random.uniform(15, 120), 1)
        
        # Test sonucunu veritabanına kaydet
        test_result = TestResult(
            pcba_model_id=pcba_model_id,
            test_type_id=test_type_id,
            serial_number=serial_number,
            test_status=test_status,
            test_data=test_results,
            operator_id=current_user.id,
            test_duration=test_duration,
            notes=f'{test_type.type_name} test completed by {current_user.username}'
        )
        
        db.session.add(test_result)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'test_result': {
                'id': test_result.id,
                'status': test_status,
                'duration': test_duration,
                'results': test_results,
                'serial_number': serial_number,
                'test_type': test_type.type_code,
                'test_type_name': test_type.type_name,
                'model_name': pcba_model.model_name
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Test sırasında hata oluştu: {str(e)}'})

@app.route('/test-results')
@login_required
def test_results():
    # Test sonuçlarını sayfalama ile getir
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Eager loading ile ilişkili verileri de getir
    tests = TestResult.query.options(
        db.joinedload(TestResult.pcba_model),
        db.joinedload(TestResult.test_type),
        db.joinedload(TestResult.operator)
    ).order_by(TestResult.test_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # İstatistikler
    total_tests = TestResult.query.count()
    passed_tests = TestResult.query.filter_by(test_status='PASS').count()
    failed_tests = TestResult.query.filter_by(test_status='FAIL').count()
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    return render_template('test-results.html', 
                         tests=tests, 
                         total_tests=total_tests,
                         passed_tests=passed_tests,
                         failed_tests=failed_tests,
                         success_rate=success_rate)

@app.route('/scheduled-tests')
@login_required
@require_permission('view_scheduled_tests')
def scheduled_tests():
    return render_template('scheduled-tests.html')

# ============================================================================
# AUTOMATED TEST EXECUTION ROUTES
# ============================================================================

@app.route('/test-execution')
@login_required
@require_permission('start_manual_tests')
def test_execution():
    """Test execution page for manual test runs"""
    # Get active test scenarios and PCBA models
    test_scenarios = TestScenario.query.filter_by(is_active=True).all()
    pcba_models = PCBAModel.query.filter_by(is_active=True).all()
    
    # Get user's recent test executions
    recent_executions = TestExecution.query.filter_by(user_id=current_user.id)\
        .order_by(TestExecution.created_at.desc())\
        .limit(5).all()
    
    return render_template('test-execution.html',
                         test_scenarios=test_scenarios,
                         pcba_models=pcba_models,
                         recent_executions=recent_executions)

@app.route('/test-monitoring')
@login_required
@require_permission('view_test_executions')
def test_monitoring():
    """Test monitoring page for real-time test tracking"""
    return render_template('test-monitoring.html')


@app.route('/reports')
@login_required
def reports():
    # Raporlama için istatistikler
    from datetime import datetime, timedelta
    
    # Son 30 günlük veriler
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_tests = TestResult.query.filter(TestResult.test_date >= thirty_days_ago).all()
    
    # Günlük test sayıları (son 7 gün)
    daily_stats = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_tests = TestResult.query.filter(
            TestResult.test_date >= day_start,
            TestResult.test_date <= day_end
        ).all()
        
        passed = len([t for t in day_tests if t.test_status == 'PASS'])
        failed = len([t for t in day_tests if t.test_status == 'FAIL'])
        
        daily_stats.append({
            'date': date.strftime('%d.%m'),
            'total': len(day_tests),
            'passed': passed,
            'failed': failed
        })
    
    daily_stats.reverse()  # Eski tarihten yeniye
    
    # Test tipi dağılımı
    test_type_stats = {}
    for test in recent_tests:
        test_type = test.test_type.type_code
        if test_type not in test_type_stats:
            test_type_stats[test_type] = {'total': 0, 'passed': 0, 'failed': 0}
        
        test_type_stats[test_type]['total'] += 1
        if test.test_status == 'PASS':
            test_type_stats[test_type]['passed'] += 1
        else:
            test_type_stats[test_type]['failed'] += 1
    
    # Operatör performansı
    operator_stats = {}
    for test in recent_tests:
        operator = test.operator.username
        if operator not in operator_stats:
            operator_stats[operator] = {'total': 0, 'passed': 0, 'failed': 0}
        
        operator_stats[operator]['total'] += 1
        if test.test_status == 'PASS':
            operator_stats[operator]['passed'] += 1
        else:
            operator_stats[operator]['failed'] += 1
    
    return render_template('reports.html',
                         daily_stats=daily_stats,
                         test_type_stats=test_type_stats,
                         operator_stats=operator_stats,
                         recent_tests=recent_tests)

@app.route('/api/test-detail/<int:test_id>')
@login_required
def api_test_detail(test_id):
    test = TestResult.query.get_or_404(test_id)
    return jsonify({
        'id': test.id,
        'serial_number': test.serial_number,
        'model_name': test.pcba_model.model_name,
        'part_number': test.pcba_model.part_number,
        'test_type': test.test_type.type_code,
        'test_status': test.test_status,
        'test_date': test.test_date.strftime('%d.%m.%Y %H:%M:%S'),
        'test_duration': test.test_duration,
        'operator': test.operator.username,
        'test_data': test.test_data,
        'notes': test.notes
    })

# API Route'ları
@app.route('/api/test-results')
@login_required
def api_test_results():
    tests = TestResult.query.all()
    results = []
    for test in tests:
        results.append({
            'id': test.id,
            'serial_number': test.serial_number,
            'model_name': test.pcba_model.model_name,
            'test_type': test.test_type.type_code,
            'test_status': test.test_status,
            'test_date': test.test_date.strftime('%Y-%m-%d %H:%M:%S'),
            'operator': test.operator.username
        })
    return jsonify(results)

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats_old():
    total_tests = TestResult.query.count()
    passed_tests = TestResult.query.filter_by(test_status='PASS').count()
    failed_tests = TestResult.query.filter_by(test_status='FAIL').count()
    
    # Günlük test sayıları (son 7 gün)
    from datetime import datetime, timedelta
    daily_stats = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_tests = TestResult.query.filter(
            TestResult.test_date >= day_start,
            TestResult.test_date <= day_end
        ).count()
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'tests': day_tests
        })
    
    return jsonify({
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        'daily_stats': daily_stats
    })

@app.route('/api/update-profile', methods=['POST'])
@login_required
def api_update_profile():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'E-posta adresi gerekli'})
        
        # E-posta formatı kontrolü
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'message': 'Geçersiz e-posta formatı'})
        
        # E-posta benzersizlik kontrolü
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Bu e-posta adresi zaten kullanılıyor'})
        
        current_user.email = email
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Profil başarıyla güncellendi'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': 'Güncelleme sırasında hata oluştu'})

@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Mevcut şifre ve yeni şifre gerekli'})
        
        # Mevcut şifre kontrolü
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Mevcut şifre yanlış'})
        
        # Yeni şifre uzunluk kontrolü
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Yeni şifre en az 6 karakter olmalıdır'})
        
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Şifre başarıyla değiştirildi'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': 'Şifre değiştirme sırasında hata oluştu'})

# Bağlantı Yönetimi Route'ları
@app.route('/connections')
@login_required
def connections():
    connections = Connection.query.filter_by(is_active=True).all()
    return render_template('connections.html', connections=connections)

@app.route('/add-connection', methods=['GET', 'POST'])
@login_required
def add_connection():
    if request.method == 'POST':
        try:
            connection_name = request.form['connection_name']
            protocol_type = request.form['protocol_type']
            description = request.form.get('description', '')
            
            connection = Connection(
                connection_name=connection_name,
                protocol_type=protocol_type,
                description=description
            )
            
            # Protocol specific parameters
            if protocol_type == 'MODBUS_RTU':
                connection.serial_port = request.form.get('serial_port')
                connection.baud_rate = int(request.form.get('baud_rate', 9600))
                connection.data_bits = int(request.form.get('data_bits', 8))
                connection.parity = request.form.get('parity', 'NONE')
                connection.stop_bits = int(request.form.get('stop_bits', 1))
                connection.modbus_address = int(request.form.get('modbus_address', 1))
            
            elif protocol_type == 'MODBUS_TCP':
                connection.ip_address = request.form.get('ip_address')
                connection.port = int(request.form.get('port', 502))
                connection.gateway_address = request.form.get('gateway_address')
                connection.subnet_mask = request.form.get('subnet_mask')
                connection.timeout = int(request.form.get('timeout', 5000))
            
            db.session.add(connection)
            db.session.commit()
            
            return redirect(url_for('connections'))
            
        except Exception as e:
            return render_template('add-connection.html', error='Bağlantı eklenirken hata oluştu: ' + str(e))
    
    return render_template('add-connection.html')

@app.route('/edit-connection/<int:connection_id>', methods=['GET', 'POST'])
@login_required
def edit_connection(connection_id):
    connection = Connection.query.get_or_404(connection_id)
    
    if request.method == 'POST':
        try:
            connection.connection_name = request.form['connection_name']
            connection.protocol_type = request.form['protocol_type']
            connection.description = request.form.get('description', '')
            
            # Protocol specific parameters
            if connection.protocol_type == 'MODBUS_RTU':
                connection.serial_port = request.form.get('serial_port')
                connection.baud_rate = int(request.form.get('baud_rate', 9600))
                connection.data_bits = int(request.form.get('data_bits', 8))
                connection.parity = request.form.get('parity', 'NONE')
                connection.stop_bits = int(request.form.get('stop_bits', 1))
                connection.modbus_address = int(request.form.get('modbus_address', 1))
                # Clear TCP parameters
                connection.ip_address = None
                connection.port = 502
                connection.gateway_address = None
                connection.subnet_mask = None
                connection.timeout = 5000
                
            elif connection.protocol_type == 'MODBUS_TCP':
                connection.ip_address = request.form.get('ip_address')
                connection.port = int(request.form.get('port', 502))
                connection.gateway_address = request.form.get('gateway_address')
                connection.subnet_mask = request.form.get('subnet_mask')
                connection.timeout = int(request.form.get('timeout', 5000))
                # Clear RTU parameters
                connection.serial_port = None
                connection.baud_rate = None
                connection.modbus_address = None
            
            db.session.commit()
            return redirect(url_for('connections'))
            
        except Exception as e:
            return render_template('edit-connection.html', connection=connection, 
                                 error='Bağlantı güncellenirken hata oluştu: ' + str(e))
    
    return render_template('edit-connection.html', connection=connection)

@app.route('/delete-connection/<int:connection_id>', methods=['POST'])
@login_required
def delete_connection(connection_id):
    connection = Connection.query.get_or_404(connection_id)
    connection.is_active = False
    db.session.commit()
    return redirect(url_for('connections'))

@app.route('/api/test-connection/<int:connection_id>', methods=['POST'])
@login_required
def api_test_connection(connection_id):
    connection = Connection.query.get_or_404(connection_id)
    
    try:
        # Bu kısımda gerçek Modbus bağlantı testi yapılacak
        # Şimdilik basit bir simülasyon yapıyoruz
        
        if connection.protocol_type == 'MODBUS_RTU':
            # RTU bağlantı testi simülasyonu
            test_result = {
                'success': True,
                'message': f'Modbus RTU bağlantısı başarılı: {connection.serial_port}, Adres: {connection.modbus_address}',
                'connection_time': 250,  # ms
                'device_info': 'Test Device RTU'
            }
        
        elif connection.protocol_type == 'MODBUS_TCP':
            # TCP bağlantı testi simülasyonu
            test_result = {
                'success': True,
                'message': f'Modbus TCP bağlantısı başarılı: {connection.ip_address}:{connection.port}',
                'connection_time': 150,  # ms
                'device_info': 'Test Device TCP'
            }
        
        return jsonify(test_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Bağlantı testi başarısız: {str(e)}'
        })

# Veritabanını başlat
def init_db():
    with app.app_context():
        db.create_all()
        
        # Varsayılan admin kullanıcısı oluştur
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@pcbatest.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
        # Test operator kullanıcısı oluştur
        if not User.query.filter_by(username='operator').first():
            operator = User(
                username='operator',
                email='operator@pcbatest.com',
                role='operator'
            )
            operator.set_password('operator123')
            db.session.add(operator)
            
            # Test tiplerini oluştur
            test_types_data = [
                {'code': 'ICT', 'name': 'In-Circuit Test', 'desc': 'Devre içi test - elektriksel bağlantıları kontrol eder'},
                {'code': 'FCT', 'name': 'Functional Test', 'desc': 'Fonksiyonel test - cihazın çalışma performansını test eder'},
                {'code': 'AOI', 'name': 'Automated Optical Inspection', 'desc': 'Otomatik optik muayene - görsel kusurları tespit eder'},
                {'code': 'Boundary Scan', 'name': 'Boundary Scan Test', 'desc': 'Sınır tarama testi - dijital devreleri test eder'},
                {'code': 'RF Test', 'name': 'Radio Frequency Test', 'desc': 'RF test - kablosuz iletişim performansını test eder'},
                {'code': 'Power Test', 'name': 'Power Supply Test', 'desc': 'Güç kaynağı testi - voltaj ve akım değerlerini kontrol eder'}
            ]
            
            test_type_objects = []
            for tt_data in test_types_data:
                test_type = TestType(
                    type_code=tt_data['code'],
                    type_name=tt_data['name'],
                    description=tt_data['desc']
                )
                db.session.add(test_type)
                test_type_objects.append(test_type)
            
            # Test senaryolarını oluştur
            test_scenario1 = TestScenario(
                scenario_name='Standard Electronics Test',
                description='Standart elektronik devre testleri',
                test_parameters={
                    'voltage_range': {'min': 3.2, 'max': 3.4},
                    'current_range': {'min': 0.1, 'max': 0.5},
                    'frequency_test': {'target': 1000, 'tolerance': 10}
                }
            )
            db.session.add(test_scenario1)
            
            test_scenario2 = TestScenario(
                scenario_name='High Power Test',
                description='Yüksek güç elektronik test senaryosu',
                test_parameters={
                    'voltage_range': {'min': 11.8, 'max': 12.2},
                    'current_range': {'min': 1.0, 'max': 3.0},
                    'frequency_test': {'target': 2000, 'tolerance': 20}
                }
            )
            db.session.add(test_scenario2)
            
            db.session.commit()  # Test tipleri ve senaryoları kaydet
            
            # Örnek PCBA modelleri
            pcba_model1 = PCBAModel(
                model_name='Demo Board v1.0',
                part_number='PCB-001',
                description='Demo PCBA for standard testing',
                test_scenario_id=test_scenario1.id
            )
            db.session.add(pcba_model1)
            
            pcba_model2 = PCBAModel(
                model_name='Power Board v2.1',
                part_number='PCB-002',
                description='High power PCBA board',
                test_scenario_id=test_scenario2.id
            )
            db.session.add(pcba_model2)
            
            db.session.commit()  # PCBA modelleri kaydet
            
            # Örnek test sonuçları ekle
            from datetime import datetime, timedelta
            import random
            
            statuses = ['PASS', 'FAIL']
            pcba_models = [pcba_model1, pcba_model2]
            
            for i in range(30):  # 30 test sonucu
                test_date = datetime.utcnow() - timedelta(days=random.randint(0, 7))
                status = random.choices(statuses, weights=[8, 2])[0]  # %80 PASS, %20 FAIL
                selected_pcba = random.choice(pcba_models)
                selected_test_type = random.choice(test_type_objects)
                
                # Test senaryosuna göre test verileri oluştur
                if selected_pcba.test_scenario:
                    params = selected_pcba.test_scenario.test_parameters
                    test_data = {}
                    
                    if 'voltage_range' in params:
                        v_range = params['voltage_range']
                        test_data['voltage'] = round(random.uniform(
                            v_range['min'] - 0.1, v_range['max'] + 0.1
                        ), 2)
                    
                    if 'current_range' in params:
                        c_range = params['current_range']
                        test_data['current'] = round(random.uniform(
                            c_range['min'] - 0.05, c_range['max'] + 0.05
                        ), 3)
                    
                    if 'frequency_test' in params:
                        f_test = params['frequency_test']
                        test_data['frequency'] = random.randint(
                            f_test['target'] - f_test['tolerance'] - 5,
                            f_test['target'] + f_test['tolerance'] + 5
                        )
                else:
                    # Varsayılan test verileri
                    test_data = {
                        'voltage': round(random.uniform(3.15, 3.45), 2),
                        'current': round(random.uniform(0.08, 0.52), 3),
                        'frequency': random.randint(995, 1005)
                    }
                
                test_result = TestResult(
                    pcba_model_id=selected_pcba.id,
                    test_type_id=selected_test_type.id,
                    serial_number=f'SN{1000 + i:04d}',
                    test_status=status,
                    test_data=test_data,
                    operator_id=admin.id,
                    test_date=test_date,
                    test_duration=round(random.uniform(30, 180), 1),
                    notes=f'Test #{i+1} - {selected_test_type.type_name} on {selected_pcba.model_name}'
                )
                db.session.add(test_result)
            
            db.session.commit()
            
            # Initialize permissions and roles
            init_permissions_and_roles()
            print("Veritabanı başlatıldı ve varsayılan veriler eklendi.")

def init_permissions_and_roles():
    """Initialize default permissions and roles"""
    
    # Define default permissions
    default_permissions = [
        # Dashboard permissions
        {'name': 'view_dashboard', 'description': 'Dashboard görüntüleme yetkisi', 'module': 'dashboard'},
        
        # User management permissions
        {'name': 'view_users', 'description': 'Kullanıcıları görüntüleme yetkisi', 'module': 'user_management'},
        {'name': 'manage_users', 'description': 'Kullanıcıları yönetme yetkisi (ekleme, düzenleme, silme)', 'module': 'user_management'},
        {'name': 'manage_user_permissions', 'description': 'Kullanıcı yetkilerini yönetme', 'module': 'user_management'},
        
        # Test management permissions  
        {'name': 'view_test_types', 'description': 'Test tiplerini görüntüleme yetkisi', 'module': 'test_management'},
        {'name': 'manage_test_types', 'description': 'Test tiplerini yönetme yetkisi', 'module': 'test_management'},
        {'name': 'view_test_scenarios', 'description': 'Test senaryolarını görüntüleme yetkisi', 'module': 'test_management'},
        {'name': 'manage_test_scenarios', 'description': 'Test senaryolarını yönetme yetkisi', 'module': 'test_management'},
        {'name': 'view_pcba_models', 'description': 'PCBA modellerini görüntüleme yetkisi', 'module': 'test_management'},
        {'name': 'manage_pcba_models', 'description': 'PCBA modellerini yönetme yetkisi', 'module': 'test_management'},
        
        # Test operations permissions
        {'name': 'run_tests', 'description': 'Test çalıştırma yetkisi', 'module': 'test_operations'},
        {'name': 'view_test_results', 'description': 'Test sonuçlarını görüntüleme yetkisi', 'module': 'test_operations'},
        {'name': 'delete_test_results', 'description': 'Test sonuçlarını silme yetkisi', 'module': 'test_operations'},
        
        # Connection management permissions
        {'name': 'view_connections', 'description': 'Bağlantıları görüntüleme yetkisi', 'module': 'connection_management'},
        {'name': 'manage_connections', 'description': 'Bağlantıları yönetme yetkisi', 'module': 'connection_management'},
        {'name': 'test_connections', 'description': 'Bağlantı testi yapma yetkisi', 'module': 'connection_management'},
        
        # Report permissions
        {'name': 'view_reports', 'description': 'Raporları görüntüleme yetkisi', 'module': 'reports'},
        {'name': 'export_reports', 'description': 'Raporları dışa aktarma yetkisi', 'module': 'reports'},
        
        # Settings permissions
        {'name': 'view_settings', 'description': 'Ayarları görüntüleme yetkisi', 'module': 'settings'},
        {'name': 'manage_system_settings', 'description': 'Sistem ayarlarını yönetme yetkisi', 'module': 'settings'},
        {'name': 'manage_test_parameters', 'description': 'Test parametrelerini yönetme yetkisi', 'module': 'settings'}
    ]
    
    # Create permissions
    for perm_data in default_permissions:
        if not Permission.query.filter_by(name=perm_data['name']).first():
            permission = Permission(
                name=perm_data['name'],
                description=perm_data['description'],
                module=perm_data['module']
            )
            db.session.add(permission)
    
    db.session.commit()
    
    # Define default roles
    default_roles = [
        {
            'name': 'admin',
            'description': 'Sistem yöneticisi - tüm yetkilere sahip',
            'permissions': [
                'view_dashboard', 'view_users', 'manage_users',
                'manage_user_permissions', 'view_test_types', 'manage_test_types',
                'view_test_scenarios', 'manage_test_scenarios', 'view_pcba_models',
                'manage_pcba_models', 'run_tests', 'view_test_results', 'delete_test_results',
                'view_connections', 'manage_connections', 'test_connections', 'view_reports',
                'export_reports', 'view_settings', 'manage_system_settings', 'manage_test_parameters'
            ]
        },
        {
            'name': 'technician',
            'description': 'Teknisyen - test yönetimi ve çalıştırma yetkileri',
            'permissions': [
                'view_dashboard', 'view_test_types', 'view_test_scenarios', 'view_pcba_models',
                'run_tests', 'view_test_results', 'view_connections', 'test_connections',
                'view_reports', 'view_settings', 'manage_test_parameters'
            ]
        },
        {
            'name': 'operator',
            'description': 'Operatör - temel test çalıştırma yetkileri',
            'permissions': [
                'view_dashboard', 'run_tests', 'view_test_results', 'view_connections', 'view_settings'
            ]
        }
    ]
    
    # Create roles and assign permissions
    for role_data in default_roles:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(
                name=role_data['name'],
                description=role_data['description']
            )
            db.session.add(role)
            db.session.commit()  # Commit to get role ID
        
        # Clear existing permissions for this role
        role.permissions.clear()
        
        # Add permissions to role
        for perm_name in role_data['permissions']:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                role.permissions.append(permission)
    
    db.session.commit()
    
    # Assign roles to existing users
    admin_role = Role.query.filter_by(name='admin').first()
    technician_role = Role.query.filter_by(name='technician').first()
    operator_role = Role.query.filter_by(name='operator').first()
    
    # Update admin user
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user and not admin_user.role_id:
        admin_user.role_id = admin_role.id
    
    # Update operator user
    operator_user = User.query.filter_by(username='operator').first()
    if operator_user and not operator_user.role_id:
        operator_user.role_id = operator_role.id
    
    db.session.commit()

# Role Management Routes (Individual user permissions removed - using role-based system only)

@app.route('/role-management')
@require_permission('manage_user_permissions')
def role_management():
    
    roles = Role.query.all()
    permissions = Permission.query.all()
    
    return render_template('role-management.html', roles=roles, permissions=permissions)

@app.route('/api/role-permissions/<int:role_id>')
@require_permission('manage_user_permissions')
def api_role_permissions(role_id):
    
    role = Role.query.get_or_404(role_id)
    role_permissions = [p.name for p in role.permissions]
    
    return jsonify({
        'role_id': role.id,
        'role': role.name,
        'description': role.description,
        'permissions': role_permissions
    })

@app.route('/edit-role/<int:role_id>', methods=['GET', 'POST'])
@require_permission('manage_user_permissions')
def edit_role(role_id):
    
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        try:
            role.name = request.form['name']
            role.description = request.form['description']
            role.is_active = 'is_active' in request.form
            
            # Update permissions
            role.permissions.clear()
            for permission_id in request.form.getlist('permissions'):
                permission = Permission.query.get(int(permission_id))
                if permission:
                    role.permissions.append(permission)
            
            db.session.commit()
            return redirect(url_for('role_management'))
            
        except Exception as e:
            db.session.rollback()
            return render_template('edit-role.html', role=role, error=f'Güncelleme hatası: {str(e)}')
    
    permissions = Permission.query.all()
    role_permission_ids = [p.id for p in role.permissions]
    
    return render_template('edit-role-fixed.html', role=role, permissions=permissions,
                         role_permission_ids=role_permission_ids)

# Static file caching
@app.after_request
def after_request(response):
    """Static dosyalar için cache headers ekle"""
    if request.endpoint == 'static':
        # Static dosyalar için 1 saat cache
        response.cache_control.max_age = 3600
        response.cache_control.public = True
    return response

# Session management iyileştirmeleri
@app.before_request
def before_request():
    """Her request öncesi çalışacak fonksiyon"""
    # Session timeout kontrolü (24 saat)
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=24)
    
    # Database connection pool yönetimi
    if hasattr(db.engine, 'pool'):
        db.engine.pool.pre_ping = True

# Communication Logging Routes
@app.route('/communication-logs')
def communication_logs():
    """Communication logs sayfası"""
    return render_template('communication-logs.html')

@app.route('/api/communication-logs')
@login_required
@require_permission('communication_view')
def api_communication_logs():
    """Communication logs API - AJAX için"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filters
    connection_type = request.args.get('connection_type')
    connection_id = request.args.get('connection_id', type=int)
    direction = request.args.get('direction')
    status = request.args.get('status')  # 'success' or 'error'
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    
    # Base query with join to get connection info
    query = CommunicationLog.query.join(ConnectionConfig)
    
    # Apply filters
    if connection_type:
        query = query.filter(ConnectionConfig.connection_type == connection_type)
    if connection_id:
        query = query.filter(CommunicationLog.connection_id == connection_id)
    if direction:
        query = query.filter(CommunicationLog.direction == direction)
    if status:
        if status == 'error':
            query = query.filter(CommunicationLog.is_error == True)
        elif status == 'success':
            query = query.filter(CommunicationLog.is_error == False)
    if start_date:
        query = query.filter(CommunicationLog.timestamp >= start_date)
    if end_date:
        query = query.filter(CommunicationLog.timestamp <= end_date)
    if search:
        query = query.filter(
            db.or_(
                CommunicationLog.data_ascii.contains(search),
                CommunicationLog.data_hex.contains(search),
                CommunicationLog.error_message.contains(search)
            )
        )
    
    # Order by timestamp desc and paginate
    logs = query.order_by(CommunicationLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Convert to dict with connection info
    logs_data = []
    for log in logs.items:
        log_dict = log.to_dict()
        if log.connection:
            log_dict['connection_type'] = log.connection.connection_type
            log_dict['connection_display'] = log.connection.port if log.connection.connection_type == 'serial' else f"{log.connection.ip_address}:{log.connection.tcp_port}"
        logs_data.append(log_dict)
    
    return jsonify({
        'logs': logs_data,
        'total': logs.total,
        'pages': logs.pages,
        'current_page': logs.page,
        'per_page': logs.per_page,
        'has_next': logs.has_next,
        'has_prev': logs.has_prev
    })

@app.route('/api/connection-status')
@login_required
@require_permission('communication_view')
def api_connection_status():
    """Connection status API"""
    connections = ConnectionConfig.query.filter_by(is_active=True).all()
    return jsonify({
        'connections': [conn.to_dict() for conn in connections]
    })

@app.route('/api/connection-configs')
@login_required
@require_permission('communication_view')
def api_connection_configs():
    """Connection configurations API"""
    connections = ConnectionConfig.query.filter_by(is_active=True).all()
    return jsonify({
        'connections': [conn.to_dict() for conn in connections]
    })

@app.route('/api/communication-logs/export', methods=['POST'])
@login_required
@require_permission('communication_export')
def export_communication_logs():
    """Communication logs export"""
    data = request.get_json()
    export_format = data.get('format', 'csv')  # csv, json
    
    # Apply same filters as API
    query = CommunicationLog.query
    
    # Apply filters from request
    if data.get('connection_id'):
        query = query.filter(CommunicationLog.connection_id == data['connection_id'])
    if data.get('direction'):
        query = query.filter(CommunicationLog.direction == data['direction'])
    if data.get('is_error') is not None:
        query = query.filter(CommunicationLog.is_error == data['is_error'])
    if data.get('start_date'):
        query = query.filter(CommunicationLog.timestamp >= data['start_date'])
    if data.get('end_date'):
        query = query.filter(CommunicationLog.timestamp <= data['end_date'])
    
    logs = query.order_by(CommunicationLog.timestamp.desc()).limit(10000).all()  # Limit for performance
    
    if export_format == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Timestamp', 'Connection', 'Direction', 'Data (ASCII)', 'Data (HEX)',
            'Data Size', 'Is Error', 'Error Message', 'Response Time (ms)', 'User'
        ])
        
        # Data
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat() if log.timestamp else '',
                log.connection.name if log.connection else '',
                log.direction,
                log.data_ascii or '',
                log.data_hex or '',
                log.data_size or 0,
                'Yes' if log.is_error else 'No',
                log.error_message or '',
                log.response_time or '',
                log.user.username if log.user else ''
            ])
        
        output.seek(0)
        return jsonify({
            'success': True,
            'data': output.getvalue(),
            'filename': f'communication_logs_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        })
    
    elif export_format == 'json':
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs],
            'filename': f'communication_logs_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        })
    
    else:
        return jsonify({'success': False, 'message': 'Unsupported export format'})

# ============================================================================
# AUTOMATED TEST EXECUTION API ENDPOINTS
# ============================================================================

@app.route('/api/test/start', methods=['POST'])
@login_required
@require_permission('start_manual_tests')
def api_start_test():
    """Start a manual test execution with connection management"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['test_scenario_id', 'pcba_model_id', 'serial_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'})
        
        # Check connection status before starting test
        connection_status = check_test_equipment_connections()
        if not connection_status['success']:
            return jsonify({
                'success': False, 
                'message': f'Cannot start test: {connection_status["message"]}',
                'error_type': 'CONNECTION_ERROR'
            })
        
        # Log connection check
        log_communication_event(
            connection_id=connection_status.get('connection_id'),
            event_type='CONNECTION_CHECK',
            direction='SYSTEM',
            message='Connection verified before test start',
            status='SUCCESS'
        )
        
        # Start the test
        result = test_executor_service.start_manual_test(
            test_scenario_id=data['test_scenario_id'],
            pcba_model_id=data['pcba_model_id'],
            serial_number=data['serial_number'],
            user_id=current_user.id,
            connection_id=connection_status.get('connection_id')
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to start test: {str(e)}'})

@app.route('/api/test/status/<int:execution_id>')
@login_required
@require_permission('view_test_executions')
def api_get_test_status(execution_id):
    """Get current test execution status"""
    try:
        result = test_executor_service.get_test_status(execution_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get test status: {str(e)}'})

@app.route('/api/test/stop/<int:execution_id>', methods=['POST'])
@login_required
@require_permission('stop_tests')
def api_stop_test(execution_id):
    """Stop a running test execution"""
    try:
        result = test_executor_service.stop_test(execution_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to stop test: {str(e)}'})

@app.route('/api/test/running')
@login_required
@require_permission('view_test_executions')
def api_get_running_tests():
    """Get list of currently running tests"""
    try:
        result = test_executor_service.get_running_tests()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get running tests: {str(e)}'})

@app.route('/api/test/history')
@login_required
@require_permission('view_test_executions')
def api_get_test_history():
    """Get test execution history with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status', '')
        scenario_filter = request.args.get('scenario_id', '', type=str)
        model_filter = request.args.get('model_id', '', type=str)
        user_filter = request.args.get('user_id', '', type=str)
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query
        query = TestExecution.query
        
        # Apply filters
        if status_filter:
            query = query.filter(TestExecution.status == status_filter)
        
        if scenario_filter:
            query = query.filter(TestExecution.test_scenario_id == int(scenario_filter))
        
        if model_filter:
            query = query.filter(TestExecution.pcba_model_id == int(model_filter))
        
        if user_filter:
            query = query.filter(TestExecution.user_id == int(user_filter))
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(TestExecution.created_at >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire day
                to_date = to_date + timedelta(days=1)
                query = query.filter(TestExecution.created_at < to_date)
            except ValueError:
                pass
        
        # Order by creation date (newest first)
        query = query.order_by(TestExecution.created_at.desc())
        
        # Paginate
        executions = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'executions': [execution.to_dict() for execution in executions.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': executions.total,
                'pages': executions.pages,
                'has_next': executions.has_next,
                'has_prev': executions.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get test history: {str(e)}'})

@app.route('/api/test/scenarios')
@login_required
@require_permission('view_test_scenarios')
def api_get_test_scenarios():
    """Get list of active test scenarios for test execution"""
    try:
        scenarios = TestScenario.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'scenarios': [{
                'id': scenario.id,
                'name': scenario.scenario_name,
                'description': scenario.description,
                'parameters': scenario.test_parameters
            } for scenario in scenarios]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get test scenarios: {str(e)}'})

@app.route('/api/test/pcba-models')
@login_required
@require_permission('view_pcba_models')
def api_get_pcba_models():
    """Get list of active PCBA models for test execution"""
    try:
        models = PCBAModel.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'models': [{
                'id': model.id,
                'name': model.model_name,
                'part_number': model.part_number,
                'description': model.description,
                'test_scenario_id': model.test_scenario_id,
                'test_scenario_name': model.test_scenario.scenario_name if model.test_scenario else None
            } for model in models]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get PCBA models: {str(e)}'})

@app.route('/api/test/monitoring')
@login_required
@require_permission('view_test_executions')
def api_test_monitoring():
    """Get comprehensive test monitoring data"""
    try:
        # Get all test executions from last 24 hours
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=24)
        
        all_executions = TestExecution.query.filter(
            TestExecution.created_at >= since
        ).order_by(TestExecution.created_at.desc()).all()
        
        # Count by status
        counts = {
            'running': len([e for e in all_executions if e.status == 'RUNNING']),
            'completed': len([e for e in all_executions if e.status == 'COMPLETED']),
            'failed': len([e for e in all_executions if e.status in ['FAILED', 'CANCELLED']]),
            'avg_duration': 0
        }
        
        # Calculate average duration for completed tests
        completed_tests = [e for e in all_executions if e.status == 'COMPLETED' and e.end_time and e.start_time]
        if completed_tests:
            total_duration = sum([(e.end_time - e.start_time).total_seconds() for e in completed_tests])
            counts['avg_duration'] = round(total_duration / len(completed_tests), 1)
        
        # Get active tests (running or recently completed)
        active_executions = [e for e in all_executions if e.status in ['RUNNING', 'COMPLETED', 'FAILED'] and 
                           (datetime.utcnow() - e.created_at).total_seconds() < 3600]  # Last hour
        
        active_tests = []
        for execution in active_executions:
            duration = 0
            if execution.start_time:
                end_time = execution.end_time or datetime.utcnow()
                duration = (end_time - execution.start_time).total_seconds()
            
            # Simulate real-time data for running tests
            real_time_data = {}
            if execution.status == 'RUNNING' and execution.test_data:
                # Extract current measurements from test_data
                test_data = execution.test_data
                if isinstance(test_data, dict):
                    for key, value in test_data.items():
                        if isinstance(value, dict) and 'measured' in value:
                            real_time_data[key] = value
            
            active_tests.append({
                'id': execution.id,
                'serial_number': execution.serial_number,
                'status': execution.status,
                'progress': execution.progress,
                'current_step': execution.current_step,
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'duration': duration,
                'test_scenario_name': execution.test_scenario.scenario_name if execution.test_scenario else None,
                'operator_name': execution.user.username if execution.user else None,
                'error_message': execution.error_message,
                'passed_steps': len([k for k, v in (execution.test_data or {}).items() 
                                   if isinstance(v, dict) and v.get('status') == 'PASS']),
                'failed_steps': len([k for k, v in (execution.test_data or {}).items() 
                                   if isinstance(v, dict) and v.get('status') == 'FAIL']),
                'real_time_data': real_time_data,
                'final_result': execution.final_result
            })
        
        return jsonify({
            'success': True,
            'counts': counts,
            'active_tests': active_tests
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get monitoring data: {str(e)}'})

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Get dashboard statistics for real-time updates"""
    try:
        from datetime import datetime, timedelta
        
        # Today's date range
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Count today's completed tests
        today_completed = TestExecution.query.filter(
            TestExecution.status == 'COMPLETED',
            TestExecution.end_time >= today_start,
            TestExecution.end_time <= today_end
        ).count()
        
        # Count today's failed tests
        today_failed = TestExecution.query.filter(
            TestExecution.status.in_(['FAILED', 'CANCELLED']),
            TestExecution.created_at >= today_start,
            TestExecution.created_at <= today_end
        ).count()
        
        # Count scheduled tests (active ones)
        scheduled_tests = ScheduledTest.query.filter_by(is_active=True).count()
        
        return jsonify({
            'success': True,
            'today_completed': today_completed,
            'today_failed': today_failed,
            'scheduled_tests': scheduled_tests
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get dashboard stats: {str(e)}'})

# ============================================================================
# SCHEDULED TESTS API ENDPOINTS
# ============================================================================

@app.route('/api/scheduled-tests')
@login_required
@require_permission('view_scheduled_tests')
def api_get_scheduled_tests():
    """Get all scheduled tests"""
    try:
        scheduled_tests = ScheduledTest.query.order_by(ScheduledTest.created_at.desc()).all()
        
        tests_data = []
        for test in scheduled_tests:
            tests_data.append({
                'id': test.id,
                'name': test.name,
                'test_scenario_id': test.test_scenario_id,
                'test_scenario_name': test.test_scenario.scenario_name if test.test_scenario else None,
                'pcba_model_id': test.pcba_model_id,
                'pcba_model_name': test.pcba_model.part_number if test.pcba_model else None,
                'schedule_type': test.schedule_type,
                'schedule_time': test.schedule_time.strftime('%H:%M') if test.schedule_time else None,
                'schedule_days': test.schedule_days,
                'next_run': test.next_run.isoformat() if test.next_run else None,
                'last_run': test.last_run.isoformat() if test.last_run else None,
                'is_active': test.is_active,
                'created_by': test.creator.username if test.creator else None,
                'notification_emails': test.notification_emails,
                'created_at': test.created_at.isoformat() if test.created_at else None
            })
        
        return jsonify({
            'success': True,
            'scheduled_tests': tests_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get scheduled tests: {str(e)}'})

@app.route('/api/scheduled-tests', methods=['POST'])
@login_required
@require_permission('manage_scheduled_tests')
def api_create_scheduled_test():
    """Create a new scheduled test"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'test_scenario_id', 'pcba_model_id', 'schedule_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'})
        
        # Validate schedule_type
        valid_types = ['ONCE', 'DAILY', 'WEEKLY', 'INTERVAL']
        if data['schedule_type'] not in valid_types:
            return jsonify({'success': False, 'message': f'Invalid schedule_type. Must be one of: {valid_types}'})
        
        # Parse schedule_time
        schedule_time = None
        if 'schedule_time' in data and data['schedule_time']:
            try:
                from datetime import time
                time_parts = data['schedule_time'].split(':')
                schedule_time = time(int(time_parts[0]), int(time_parts[1]))
            except:
                return jsonify({'success': False, 'message': 'Invalid schedule_time format. Use HH:MM'})
        
        # Calculate next_run
        next_run = None
        if data['schedule_type'] == 'ONCE' and 'next_run' in data:
            try:
                next_run = datetime.fromisoformat(data['next_run'].replace('Z', '+00:00'))
            except:
                return jsonify({'success': False, 'message': 'Invalid next_run format'})
        elif schedule_time:
            # Calculate next run for recurring tests
            now = datetime.utcnow()
            next_run = now.replace(
                hour=schedule_time.hour,
                minute=schedule_time.minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                if data['schedule_type'] == 'DAILY':
                    next_run += timedelta(days=1)
                elif data['schedule_type'] == 'WEEKLY':
                    next_run += timedelta(days=7)
        
        # Create scheduled test
        scheduled_test = ScheduledTest(
            name=data['name'],
            test_scenario_id=data['test_scenario_id'],
            pcba_model_id=data['pcba_model_id'],
            schedule_type=data['schedule_type'],
            schedule_time=schedule_time,
            schedule_days=data.get('schedule_days', ''),
            next_run=next_run,
            is_active=data.get('is_active', True),
            created_by=current_user.id,
            notification_emails=data.get('notification_emails', '')
        )
        
        db.session.add(scheduled_test)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled test created successfully',
            'scheduled_test_id': scheduled_test.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to create scheduled test: {str(e)}'})

@app.route('/api/scheduled-tests/<int:test_id>', methods=['PUT'])
@login_required
@require_permission('manage_scheduled_tests')
def api_update_scheduled_test(test_id):
    """Update an existing scheduled test"""
    try:
        scheduled_test = ScheduledTest.query.get_or_404(test_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            scheduled_test.name = data['name']
        if 'test_scenario_id' in data:
            scheduled_test.test_scenario_id = data['test_scenario_id']
        if 'pcba_model_id' in data:
            scheduled_test.pcba_model_id = data['pcba_model_id']
        if 'schedule_type' in data:
            scheduled_test.schedule_type = data['schedule_type']
        if 'schedule_time' in data and data['schedule_time']:
            try:
                from datetime import time
                time_parts = data['schedule_time'].split(':')
                scheduled_test.schedule_time = time(int(time_parts[0]), int(time_parts[1]))
            except:
                return jsonify({'success': False, 'message': 'Invalid schedule_time format'})
        if 'schedule_days' in data:
            scheduled_test.schedule_days = data['schedule_days']
        if 'is_active' in data:
            scheduled_test.is_active = data['is_active']
        if 'notification_emails' in data:
            scheduled_test.notification_emails = data['notification_emails']
        
        # Recalculate next_run if schedule changed
        if any(field in data for field in ['schedule_type', 'schedule_time', 'schedule_days']):
            if scheduled_test.schedule_type != 'ONCE' and scheduled_test.schedule_time:
                now = datetime.utcnow()
                next_run = now.replace(
                    hour=scheduled_test.schedule_time.hour,
                    minute=scheduled_test.schedule_time.minute,
                    second=0,
                    microsecond=0
                )
                if next_run <= now:
                    if scheduled_test.schedule_type == 'DAILY':
                        next_run += timedelta(days=1)
                    elif scheduled_test.schedule_type == 'WEEKLY':
                        next_run += timedelta(days=7)
                scheduled_test.next_run = next_run
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled test updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to update scheduled test: {str(e)}'})

@app.route('/api/scheduled-tests/<int:test_id>', methods=['DELETE'])
@login_required
@require_permission('manage_scheduled_tests')
def api_delete_scheduled_test(test_id):
    """Delete a scheduled test"""
    try:
        scheduled_test = ScheduledTest.query.get_or_404(test_id)
        
        # Delete from database
        db.session.delete(scheduled_test)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled test deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to delete scheduled test: {str(e)}'})

@app.route('/api/scheduled-tests/<int:test_id>/toggle', methods=['POST'])
@login_required
@require_permission('manage_scheduled_tests')
def api_toggle_scheduled_test(test_id):
    """Toggle active status of a scheduled test"""
    try:
        scheduled_test = ScheduledTest.query.get_or_404(test_id)
        
        # Toggle active status
        scheduled_test.is_active = not scheduled_test.is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scheduled test {"activated" if scheduled_test.is_active else "deactivated"}',
            'is_active': scheduled_test.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to toggle scheduled test: {str(e)}'})

@app.route('/api/scheduled-tests/<int:test_id>/run', methods=['POST'])
@login_required
@require_permission('manage_scheduled_tests')
def api_run_scheduled_test_now(test_id):
    """Run a scheduled test immediately"""
    try:
        scheduled_test = ScheduledTest.query.get_or_404(test_id)
        
        # Create test execution record
        execution = TestExecution(
            test_scenario_id=scheduled_test.test_scenario_id,
            pcba_model_id=scheduled_test.pcba_model_id,
            serial_number=f"MANUAL_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            status='RUNNING',
            start_time=datetime.utcnow(),
            execution_type='MANUAL',
            user_id=current_user.id,
            progress=0,
            current_step='Initializing'
        )
        
        db.session.add(execution)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scheduled test "{scheduled_test.name}" started manually',
            'execution_id': execution.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to run scheduled test: {str(e)}'})

# ============================================================================
# ADVANCED TEST RESULTS API ENDPOINTS
# ============================================================================

@app.route('/api/test-results-advanced', methods=['GET'])
@login_required
@require_permission('view_test_results')
def api_get_advanced_test_results():
    """Get test results with advanced filtering and analytics"""
    try:
        # Get filter parameters
        status = request.args.get('status')
        pcba_model_id = request.args.get('pcba_model_id', type=int)
        test_type_id = request.args.get('test_type_id', type=int)
        operator_id = request.args.get('operator_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        serial_number = request.args.get('serial_number')
        duration_min = request.args.get('duration_min', type=int)
        duration_max = request.args.get('duration_max', type=int)
        error_message = request.args.get('error_message')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        
        # Build query
        query = TestResult.query.options(
            db.joinedload(TestResult.pcba_model),
            db.joinedload(TestResult.test_type),
            db.joinedload(TestResult.operator)
        )
        
        # Apply filters
        if status:
            query = query.filter(TestResult.test_status == status)
        
        if pcba_model_id:
            query = query.filter(TestResult.pcba_model_id == pcba_model_id)
        
        if test_type_id:
            query = query.filter(TestResult.test_type_id == test_type_id)
        
        if operator_id:
            query = query.filter(TestResult.operator_id == operator_id)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(TestResult.test_date >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(TestResult.test_date <= end_dt)
            except ValueError:
                pass
        
        if serial_number:
            query = query.filter(TestResult.serial_number.ilike(f'%{serial_number}%'))
        
        if duration_min is not None:
            query = query.filter(TestResult.test_duration >= duration_min)
        
        if duration_max is not None:
            query = query.filter(TestResult.test_duration <= duration_max)
        
        if error_message:
            query = query.filter(TestResult.error_message.ilike(f'%{error_message}%'))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        results = query.order_by(TestResult.test_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format results
        test_results = []
        for result in results.items:
            test_results.append({
                'id': result.id,
                'pcba_model_name': result.pcba_model.part_number if result.pcba_model else None,
                'test_type_name': result.test_type.type_name if result.test_type else None,
                'serial_number': result.serial_number,
                'test_status': result.test_status,
                'test_duration': result.test_duration,
                'test_date': result.test_date.isoformat() if result.test_date else None,
                'operator_name': result.operator.username if result.operator else None,
                'error_message': result.error_message,
                'test_data': result.test_data
            })
        
        # Calculate statistics
        all_results = query.all()
        passed_count = len([r for r in all_results if r.test_status == 'PASS'])
        failed_count = len([r for r in all_results if r.test_status == 'FAIL'])
        error_count = len([r for r in all_results if r.test_status == 'ERROR'])
        total_tests = len(all_results)
        
        success_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average duration
        durations = [r.test_duration for r in all_results if r.test_duration]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        statistics = {
            'passed_count': passed_count,
            'failed_count': failed_count,
            'error_count': error_count,
            'total_count': total_tests,
            'success_rate': round(success_rate, 1),
            'avg_duration': round(avg_duration, 1)
        }
        
        # Generate chart data
        chart_data = generate_chart_data(all_results)
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'total_count': total_count,
            'statistics': statistics,
            'chart_data': chart_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_pages': results.pages,
                'has_next': results.has_next,
                'has_prev': results.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get advanced test results: {str(e)}'})

@app.route('/api/test-results/<int:test_id>', methods=['GET'])
@login_required
@require_permission('view_test_results')
def api_get_test_result_details(test_id):
    """Get detailed information for a specific test result"""
    try:
        result = TestResult.query.options(
            db.joinedload(TestResult.pcba_model),
            db.joinedload(TestResult.test_type),
            db.joinedload(TestResult.operator)
        ).get_or_404(test_id)
        
        test_result = {
            'id': result.id,
            'pcba_model_name': result.pcba_model.part_number if result.pcba_model else None,
            'test_type_name': result.test_type.type_name if result.test_type else None,
            'serial_number': result.serial_number,
            'test_status': result.test_status,
            'test_duration': result.test_duration,
            'test_date': result.test_date.isoformat() if result.test_date else None,
            'operator_name': result.operator.username if result.operator else None,
            'error_message': result.error_message,
            'test_data': result.test_data,
            'created_at': result.created_at.isoformat() if result.created_at else None
        }
        
        return jsonify({
            'success': True,
            'test_result': test_result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get test result details: {str(e)}'})

@app.route('/api/test-results-export', methods=['GET'])
@login_required
@require_permission('view_test_results')
def api_export_test_results():
    """Export test results to CSV or PDF"""
    try:
        export_format = request.args.get('export', 'csv')
        
        # Get same filters as advanced results
        status = request.args.get('status')
        pcba_model_id = request.args.get('pcba_model_id', type=int)
        test_type_id = request.args.get('test_type_id', type=int)
        operator_id = request.args.get('operator_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        serial_number = request.args.get('serial_number')
        duration_min = request.args.get('duration_min', type=int)
        duration_max = request.args.get('duration_max', type=int)
        error_message = request.args.get('error_message')
        
        # Build query (same as advanced results)
        query = TestResult.query.options(
            db.joinedload(TestResult.pcba_model),
            db.joinedload(TestResult.test_type),
            db.joinedload(TestResult.operator)
        )
        
        # Apply same filters
        if status:
            query = query.filter(TestResult.test_status == status)
        if pcba_model_id:
            query = query.filter(TestResult.pcba_model_id == pcba_model_id)
        if test_type_id:
            query = query.filter(TestResult.test_type_id == test_type_id)
        if operator_id:
            query = query.filter(TestResult.operator_id == operator_id)
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(TestResult.test_date >= start_dt)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(TestResult.test_date <= end_dt)
            except ValueError:
                pass
        if serial_number:
            query = query.filter(TestResult.serial_number.ilike(f'%{serial_number}%'))
        if duration_min is not None:
            query = query.filter(TestResult.test_duration >= duration_min)
        if duration_max is not None:
            query = query.filter(TestResult.test_duration <= duration_max)
        if error_message:
            query = query.filter(TestResult.error_message.ilike(f'%{error_message}%'))
        
        results = query.order_by(TestResult.test_date.desc()).all()
        
        if export_format == 'csv':
            return export_results_csv(results)
        elif export_format == 'pdf':
            return export_results_pdf(results)
        else:
            return jsonify({'success': False, 'message': 'Invalid export format'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to export test results: {str(e)}'})

def generate_chart_data(results):
    """Generate chart data for test results analytics"""
    try:
        # Distribution data
        distribution = {
            'pass': len([r for r in results if r.test_status == 'PASS']),
            'fail': len([r for r in results if r.test_status == 'FAIL']),
            'error': len([r for r in results if r.test_status == 'ERROR'])
        }
        
        # Trend data (last 7 days)
        from collections import defaultdict
        trend_data = defaultdict(lambda: {'pass': 0, 'fail': 0, 'error': 0})
        
        for result in results:
            if result.test_date:
                date_key = result.test_date.strftime('%Y-%m-%d')
                if result.test_status == 'PASS':
                    trend_data[date_key]['pass'] += 1
                elif result.test_status == 'FAIL':
                    trend_data[date_key]['fail'] += 1
                elif result.test_status == 'ERROR':
                    trend_data[date_key]['error'] += 1
        
        # Sort by date and get last 7 days
        sorted_dates = sorted(trend_data.keys())[-7:]
        
        trend = {
            'labels': sorted_dates,
            'pass': [trend_data[date]['pass'] for date in sorted_dates],
            'fail': [trend_data[date]['fail'] for date in sorted_dates],
            'error': [trend_data[date]['error'] for date in sorted_dates]
        }
        
        return {
            'distribution': distribution,
            'trend': trend
        }
        
    except Exception as e:
        print(f"Error generating chart data: {e}")
        return {
            'distribution': {'pass': 0, 'fail': 0, 'error': 0},
            'trend': {'labels': [], 'pass': [], 'fail': [], 'error': []}
        }

def export_results_csv(results):
    """Export test results to CSV format"""
    import csv
    import io
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Test ID', 'PCBA Model', 'Seri Numarası', 'Test Tipi', 'Durum', 
        'Süre (sn)', 'Tarih', 'Operatör', 'Hata Mesajı'
    ])
    
    # Write data
    for result in results:
        writer.writerow([
            result.id,
            result.pcba_model.part_number if result.pcba_model else '',
            result.serial_number or '',
            result.test_type.type_name if result.test_type else '',
            result.test_status,
            result.test_duration or 0,
            result.test_date.strftime('%Y-%m-%d %H:%M:%S') if result.test_date else '',
            result.operator.username if result.operator else '',
            result.error_message or ''
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

def export_results_pdf(results):
    """Export test results to PDF format"""
    # For now, return a simple message
    # In a real implementation, you would use a library like ReportLab
    return jsonify({
        'success': False, 
        'message': 'PDF export not implemented yet. Please use CSV export.'
    })

@app.route('/test-results-advanced')
@login_required
@require_permission('view_test_results')
def test_results_advanced():
    return render_template('test-results-advanced.html')

# ============================================================================
# TEST CONFIGURATION API ENDPOINTS
# ============================================================================

@app.route('/api/test-config', methods=['GET'])
@login_required
@require_permission('manage_system_settings')
def api_get_test_config():
    """Get current test configuration"""
    try:
        # Get configuration from database or use defaults
        config = TestConfiguration.query.first()
        
        if not config:
            # Create default configuration
            config = TestConfiguration(
                test_timeout=300,
                retry_count=3,
                retry_delay=5,
                connection_timeout=30,
                heartbeat_interval=30,
                auto_reconnect=True,
                log_level='INFO',
                log_file_size=10,
                log_retention_days=30,
                email_notifications=True,
                smtp_server='smtp.gmail.com',
                smtp_port=587,
                notification_emails='',
                max_concurrent_tests=3,
                db_cleanup_interval=90
            )
            db.session.add(config)
            db.session.commit()
        
        config_data = {
            'test_timeout': config.test_timeout,
            'retry_count': config.retry_count,
            'retry_delay': config.retry_delay,
            'connection_timeout': config.connection_timeout,
            'heartbeat_interval': config.heartbeat_interval,
            'auto_reconnect': config.auto_reconnect,
            'log_level': config.log_level,
            'log_file_size': config.log_file_size,
            'log_retention_days': config.log_retention_days,
            'email_notifications': config.email_notifications,
            'smtp_server': config.smtp_server,
            'smtp_port': config.smtp_port,
            'notification_emails': config.notification_emails,
            'max_concurrent_tests': config.max_concurrent_tests,
            'db_cleanup_interval': config.db_cleanup_interval
        }
        
        return jsonify({
            'success': True,
            'config': config_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get test configuration: {str(e)}'})

@app.route('/api/test-config', methods=['PUT'])
@login_required
@require_permission('manage_system_settings')
def api_update_test_config():
    """Update test configuration"""
    try:
        data = request.get_json()
        
        # Get or create configuration
        config = TestConfiguration.query.first()
        if not config:
            config = TestConfiguration()
            db.session.add(config)
        
        # Update configuration fields
        if 'test_timeout' in data:
            config.test_timeout = data['test_timeout']
        if 'retry_count' in data:
            config.retry_count = data['retry_count']
        if 'retry_delay' in data:
            config.retry_delay = data['retry_delay']
        if 'connection_timeout' in data:
            config.connection_timeout = data['connection_timeout']
        if 'heartbeat_interval' in data:
            config.heartbeat_interval = data['heartbeat_interval']
        if 'auto_reconnect' in data:
            config.auto_reconnect = data['auto_reconnect']
        if 'log_level' in data:
            config.log_level = data['log_level']
        if 'log_file_size' in data:
            config.log_file_size = data['log_file_size']
        if 'log_retention_days' in data:
            config.log_retention_days = data['log_retention_days']
        if 'email_notifications' in data:
            config.email_notifications = data['email_notifications']
        if 'smtp_server' in data:
            config.smtp_server = data['smtp_server']
        if 'smtp_port' in data:
            config.smtp_port = data['smtp_port']
        if 'notification_emails' in data:
            config.notification_emails = data['notification_emails']
        if 'max_concurrent_tests' in data:
            config.max_concurrent_tests = data['max_concurrent_tests']
        if 'db_cleanup_interval' in data:
            config.db_cleanup_interval = data['db_cleanup_interval']
        
        config.updated_at = datetime.utcnow()
        config.updated_by = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Test configuration updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to update test configuration: {str(e)}'})

@app.route('/api/test-connection', methods=['POST'])
@login_required
@require_permission('manage_system_settings')
def api_test_equipment_connection():
    """Test connection to test equipment"""
    try:
        # Get current configuration
        config = TestConfiguration.query.first()
        
        # Simulate connection test
        # In a real implementation, this would test actual hardware connections
        import time
        time.sleep(2)  # Simulate connection test delay
        
        # For demo purposes, randomly succeed or fail
        import random
        if random.random() > 0.2:  # 80% success rate
            return jsonify({
                'success': True,
                'message': 'All test equipment connections are working properly'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Connection failed: Test equipment not responding'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection test failed: {str(e)}'})

@app.route('/test-configuration')
@login_required
@require_permission('manage_system_settings')
def test_configuration():
    return render_template('test-configuration.html')

# ============================================================================
# CONNECTION MANAGEMENT FUNCTIONS
# ============================================================================

def check_test_equipment_connections():
    """Check status of all test equipment connections"""
    try:
        # Get active connections
        active_connections = Connection.query.filter_by(is_active=True).all()
        
        if not active_connections:
            return {
                'success': False,
                'message': 'No active test equipment connections found'
            }
        
        # Check each connection
        failed_connections = []
        working_connections = []
        
        for connection in active_connections:
            try:
                # Test the connection
                if test_single_connection(connection):
                    working_connections.append(connection)
                    
                    # Log successful connection check
                    log_communication_event(
                        connection_id=connection.id,
                        event_type='HEARTBEAT',
                        direction='OUTGOING',
                        message='Connection check successful',
                        status='SUCCESS'
                    )
                else:
                    failed_connections.append(connection)
                    
                    # Log failed connection check
                    log_communication_event(
                        connection_id=connection.id,
                        event_type='HEARTBEAT',
                        direction='OUTGOING',
                        message='Connection check failed',
                        status='FAILED'
                    )
                    
            except Exception as e:
                failed_connections.append(connection)
                
                # Log connection error
                log_communication_event(
                    connection_id=connection.id,
                    event_type='ERROR',
                    direction='SYSTEM',
                    message=f'Connection check error: {str(e)}',
                    status='ERROR'
                )
        
        if failed_connections:
            failed_names = [conn.connection_name for conn in failed_connections]
            return {
                'success': False,
                'message': f'Connection failed for: {", ".join(failed_names)}',
                'failed_connections': failed_connections,
                'working_connections': working_connections
            }
        
        # Return first working connection for test execution
        return {
            'success': True,
            'message': 'All connections are working',
            'connection_id': working_connections[0].id if working_connections else None,
            'working_connections': working_connections
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Connection check failed: {str(e)}'
        }

def test_single_connection(connection):
    """Test a single connection to equipment"""
    try:
        # Get test configuration for timeouts
        config = TestConfiguration.query.first()
        timeout = config.connection_timeout if config else 30
        
        # Simulate connection test based on connection type
        if connection.connection_type == 'TCP':
            return test_tcp_connection(connection, timeout)
        elif connection.connection_type == 'SERIAL':
            return test_serial_connection(connection, timeout)
        elif connection.connection_type == 'USB':
            return test_usb_connection(connection, timeout)
        else:
            # Unknown connection type
            return False
            
    except Exception as e:
        print(f"Connection test error for {connection.connection_name}: {e}")
        return False

def test_tcp_connection(connection, timeout):
    """Test TCP connection"""
    try:
        import socket
        
        # Parse host and port from connection details
        host = connection.host or 'localhost'
        port = connection.port or 8080
        
        # Create socket and test connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
        
    except Exception as e:
        print(f"TCP connection test failed: {e}")
        return False

def test_serial_connection(connection, timeout):
    """Test Serial connection"""
    try:
        # For demo purposes, simulate serial connection test
        # In real implementation, you would use pyserial
        import time
        time.sleep(0.1)  # Simulate connection test delay
        
        # Simulate 90% success rate for demo
        import random
        return random.random() > 0.1
        
    except Exception as e:
        print(f"Serial connection test failed: {e}")
        return False

def test_usb_connection(connection, timeout):
    """Test USB connection"""
    try:
        # For demo purposes, simulate USB connection test
        # In real implementation, you would use appropriate USB libraries
        import time
        time.sleep(0.1)  # Simulate connection test delay
        
        # Simulate 85% success rate for demo
        import random
        return random.random() > 0.15
        
    except Exception as e:
        print(f"USB connection test failed: {e}")
        return False

def attempt_reconnection(connection_id):
    """Attempt to reconnect to a failed connection"""
    try:
        connection = Connection.query.get(connection_id)
        if not connection:
            return False
        
        # Log reconnection attempt
        log_communication_event(
            connection_id=connection_id,
            event_type='RECONNECT_ATTEMPT',
            direction='SYSTEM',
            message='Attempting to reconnect',
            status='PENDING'
        )
        
        # Test the connection
        if test_single_connection(connection):
            # Update connection status
            connection.last_heartbeat = datetime.utcnow()
            connection.is_active = True
            db.session.commit()
            
            # Log successful reconnection
            log_communication_event(
                connection_id=connection_id,
                event_type='RECONNECT_SUCCESS',
                direction='SYSTEM',
                message='Reconnection successful',
                status='SUCCESS'
            )
            
            return True
        else:
            # Log failed reconnection
            log_communication_event(
                connection_id=connection_id,
                event_type='RECONNECT_FAILED',
                direction='SYSTEM',
                message='Reconnection failed',
                status='FAILED'
            )
            
            return False
            
    except Exception as e:
        # Log reconnection error
        log_communication_event(
            connection_id=connection_id,
            event_type='RECONNECT_ERROR',
            direction='SYSTEM',
            message=f'Reconnection error: {str(e)}',
            status='ERROR'
        )
        
        return False

def handle_connection_failure_during_test(execution_id, connection_id):
    """Handle connection failure during test execution"""
    try:
        execution = TestExecution.query.get(execution_id)
        if not execution:
            return
        
        # Get test configuration for auto-reconnect setting
        config = TestConfiguration.query.first()
        auto_reconnect = config.auto_reconnect if config else True
        
        if auto_reconnect:
            # Attempt reconnection
            if attempt_reconnection(connection_id):
                # Continue test execution
                log_communication_event(
                    connection_id=connection_id,
                    event_type='TEST_RESUMED',
                    direction='SYSTEM',
                    message=f'Test execution {execution_id} resumed after reconnection',
                    status='SUCCESS'
                )
                return
        
        # Stop test execution due to connection failure
        execution.status = 'FAILED'
        execution.end_time = datetime.utcnow()
        execution.error_message = 'Test stopped due to connection failure'
        execution.progress = execution.progress  # Keep current progress
        
        db.session.commit()
        
        # Log test stop
        log_communication_event(
            connection_id=connection_id,
            event_type='TEST_STOPPED',
            direction='SYSTEM',
            message=f'Test execution {execution_id} stopped due to connection failure',
            status='FAILED'
        )
        
    except Exception as e:
        print(f"Error handling connection failure: {e}")

def log_communication_event(connection_id, event_type, direction, message, status, data=None):
    """Log communication events for monitoring and debugging"""
    try:
        # Create communication log entry
        log_entry = CommunicationLog(
            connection_id=connection_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            direction=direction,
            message=message,
            data=data,
            status=status
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
    except Exception as e:
        print(f"Failed to log communication event: {e}")

# ============================================================================
# CONNECTION MONITORING API ENDPOINTS
# ============================================================================

@app.route('/api/connections/status', methods=['GET'])
@login_required
@require_permission('view_connections')
def api_get_connections_status():
    """Get current status of all connections"""
    try:
        connections = Connection.query.all()
        
        connection_status = []
        for conn in connections:
            # Test connection
            is_working = test_single_connection(conn) if conn.is_active else False
            
            connection_status.append({
                'id': conn.id,
                'name': conn.connection_name,
                'type': conn.connection_type,
                'host': conn.host,
                'port': conn.port,
                'is_active': conn.is_active,
                'is_working': is_working,
                'last_heartbeat': conn.last_heartbeat.isoformat() if conn.last_heartbeat else None,
                'created_at': conn.created_at.isoformat() if conn.created_at else None
            })
        
        return jsonify({
            'success': True,
            'connections': connection_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get connection status: {str(e)}'})

@app.route('/api/connections/<int:connection_id>/test', methods=['POST'])
@login_required
@require_permission('manage_connections')
def api_test_connection_endpoint(connection_id):
    """Test a specific connection"""
    try:
        connection = Connection.query.get_or_404(connection_id)
        
        # Test the connection
        is_working = test_single_connection(connection)
        
        if is_working:
            # Update last heartbeat
            connection.last_heartbeat = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Connection to {connection.connection_name} is working'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Connection to {connection.connection_name} failed'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection test failed: {str(e)}'})

@app.route('/api/connections/<int:connection_id>/reconnect', methods=['POST'])
@login_required
@require_permission('manage_connections')
def api_reconnect_connection(connection_id):
    """Attempt to reconnect a failed connection"""
    try:
        if attempt_reconnection(connection_id):
            return jsonify({
                'success': True,
                'message': 'Reconnection successful'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Reconnection failed'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Reconnection attempt failed: {str(e)}'})

# ============================================================================
# ERROR MANAGEMENT AND NOTIFICATION SYSTEM
# ============================================================================

def handle_test_error(execution_id, error_type, error_message, retry_count=0):
    """Handle test execution errors with retry logic"""
    try:
        execution = TestExecution.query.get(execution_id)
        if not execution:
            return False
        
        # Get test configuration
        config = TestConfiguration.query.first()
        max_retries = config.retry_count if config else 3
        retry_delay = config.retry_delay if config else 5
        
        # Log the error
        log_test_error(execution_id, error_type, error_message, retry_count)
        
        # Check if we should retry
        if retry_count < max_retries and error_type in ['CONNECTION_ERROR', 'TIMEOUT_ERROR', 'COMMUNICATION_ERROR']:
            # Schedule retry
            schedule_test_retry(execution_id, retry_count + 1, retry_delay)
            
            # Update execution status
            execution.status = 'RETRYING'
            execution.error_message = f'Retry {retry_count + 1}/{max_retries}: {error_message}'
            db.session.commit()
            
            return True
        else:
            # Mark test as failed
            execution.status = 'FAILED'
            execution.end_time = datetime.utcnow()
            execution.error_message = error_message
            db.session.commit()
            
            # Send failure notification
            send_test_failure_notification(execution)
            
            return False
            
    except Exception as e:
        print(f"Error handling test error: {e}")
        return False

def log_test_error(execution_id, error_type, error_message, retry_count):
    """Log test errors for analysis and debugging"""
    try:
        execution = TestExecution.query.get(execution_id)
        if not execution:
            return
        
        # Create error log entry
        error_log = {
            'execution_id': execution_id,
            'error_type': error_type,
            'error_message': error_message,
            'retry_count': retry_count,
            'timestamp': datetime.utcnow().isoformat(),
            'test_scenario_id': execution.test_scenario_id,
            'pcba_model_id': execution.pcba_model_id,
            'serial_number': execution.serial_number,
            'user_id': execution.user_id
        }
        
        # In a real implementation, you might store this in a separate error log table
        # or send to a logging service like ELK stack
        print(f"TEST ERROR LOG: {error_log}")
        
        # Also log to communication logs if it's a connection-related error
        if error_type in ['CONNECTION_ERROR', 'COMMUNICATION_ERROR']:
            log_communication_event(
                connection_id=execution.connection_id if hasattr(execution, 'connection_id') else None,
                event_type='TEST_ERROR',
                direction='SYSTEM',
                message=f'Test {execution_id} error: {error_message}',
                status='ERROR',
                data=str(error_log)
            )
        
    except Exception as e:
        print(f"Failed to log test error: {e}")

def schedule_test_retry(execution_id, retry_count, delay_seconds):
    """Schedule a test retry after specified delay"""
    try:
        # In a real implementation, you would use a task queue like Celery
        # For now, we'll simulate scheduling
        import threading
        import time
        
        def retry_test():
            time.sleep(delay_seconds)
            retry_test_execution(execution_id, retry_count)
        
        # Start retry in background thread
        retry_thread = threading.Thread(target=retry_test)
        retry_thread.daemon = True
        retry_thread.start()
        
        print(f"Scheduled retry for execution {execution_id} in {delay_seconds} seconds")
        
    except Exception as e:
        print(f"Failed to schedule test retry: {e}")

def retry_test_execution(execution_id, retry_count):
    """Retry a failed test execution"""
    try:
        execution = TestExecution.query.get(execution_id)
        if not execution:
            return
        
        # Check connection status before retry
        if hasattr(execution, 'connection_id') and execution.connection_id:
            connection_status = check_test_equipment_connections()
            if not connection_status['success']:
                # Connection still failed, don't retry
                handle_test_error(execution_id, 'CONNECTION_ERROR', 
                                'Retry failed: Connection still unavailable', retry_count)
                return
        
        # Reset execution status for retry
        execution.status = 'RUNNING'
        execution.start_time = datetime.utcnow()
        execution.end_time = None
        execution.progress = 0
        execution.current_step = f'Retrying test (attempt {retry_count})'
        
        db.session.commit()
        
        # Log retry attempt
        log_communication_event(
            connection_id=execution.connection_id if hasattr(execution, 'connection_id') else None,
            event_type='TEST_RETRY',
            direction='SYSTEM',
            message=f'Test execution {execution_id} retry attempt {retry_count}',
            status='PENDING'
        )
        
        # Restart the test (in a real implementation, this would trigger the actual test)
        # For now, we'll simulate test execution
        simulate_test_retry(execution_id, retry_count)
        
    except Exception as e:
        print(f"Failed to retry test execution: {e}")
        handle_test_error(execution_id, 'SYSTEM_ERROR', f'Retry failed: {str(e)}', retry_count)

def simulate_test_retry(execution_id, retry_count):
    """Simulate test retry execution"""
    try:
        import threading
        import time
        import random
        
        def run_retry():
            execution = TestExecution.query.get(execution_id)
            if not execution:
                return
            
            # Simulate test execution with higher success rate on retry
            success_rate = 0.7 + (retry_count * 0.1)  # Increase success rate with retries
            
            # Simulate test duration
            for i in range(10):
                time.sleep(0.5)
                execution.progress = (i + 1) * 10
                execution.current_step = f'Retry step {i + 1}/10'
                db.session.commit()
            
            # Determine test result
            if random.random() < success_rate:
                # Test succeeded
                execution.status = 'COMPLETED'
                execution.end_time = datetime.utcnow()
                execution.progress = 100
                execution.current_step = 'Test completed successfully'
                execution.error_message = None
                
                # Send success notification
                send_test_success_notification(execution)
            else:
                # Test failed again
                handle_test_error(execution_id, 'TEST_FAILURE', 
                                'Test failed after retry', retry_count)
            
            db.session.commit()
        
        # Run retry in background thread
        retry_thread = threading.Thread(target=run_retry)
        retry_thread.daemon = True
        retry_thread.start()
        
    except Exception as e:
        print(f"Failed to simulate test retry: {e}")

def send_test_failure_notification(execution):
    """Send notification for test failure"""
    try:
        # Get test configuration
        config = TestConfiguration.query.first()
        if not config or not config.email_notifications:
            return
        
        # Get notification email addresses
        notification_emails = config.notification_emails
        if not notification_emails:
            return
        
        # Prepare notification data
        test_scenario = execution.test_scenario.scenario_name if execution.test_scenario else 'Unknown'
        pcba_model = execution.pcba_model.part_number if execution.pcba_model else 'Unknown'
        operator = execution.user.username if execution.user else 'Unknown'
        
        subject = f"Test Failure Alert - {test_scenario}"
        message = f"""
Test Execution Failed

Test Details:
- Test ID: {execution.id}
- Test Scenario: {test_scenario}
- PCBA Model: {pcba_model}
- Serial Number: {execution.serial_number}
- Operator: {operator}
- Start Time: {execution.start_time}
- End Time: {execution.end_time}
- Error: {execution.error_message}

Please check the system for more details.
        """
        
        # Send email notification
        send_email_notification(notification_emails, subject, message)
        
        # Log notification
        log_communication_event(
            connection_id=None,
            event_type='NOTIFICATION_SENT',
            direction='OUTGOING',
            message=f'Test failure notification sent for execution {execution.id}',
            status='SUCCESS'
        )
        
    except Exception as e:
        print(f"Failed to send test failure notification: {e}")

def send_test_success_notification(execution):
    """Send notification for test success (if configured)"""
    try:
        # Get test configuration
        config = TestConfiguration.query.first()
        if not config or not config.email_notifications:
            return
        
        # Only send success notifications for scheduled tests or critical tests
        if execution.execution_type != 'SCHEDULED':
            return
        
        # Get notification email addresses
        notification_emails = config.notification_emails
        if not notification_emails:
            return
        
        # Prepare notification data
        test_scenario = execution.test_scenario.scenario_name if execution.test_scenario else 'Unknown'
        pcba_model = execution.pcba_model.part_number if execution.pcba_model else 'Unknown'
        
        subject = f"Test Success - {test_scenario}"
        message = f"""
Test Execution Completed Successfully

Test Details:
- Test ID: {execution.id}
- Test Scenario: {test_scenario}
- PCBA Model: {pcba_model}
- Serial Number: {execution.serial_number}
- Duration: {(execution.end_time - execution.start_time).total_seconds():.1f} seconds

Test completed without errors.
        """
        
        # Send email notification
        send_email_notification(notification_emails, subject, message)
        
    except Exception as e:
        print(f"Failed to send test success notification: {e}")

def send_email_notification(email_addresses, subject, message):
    """Send email notification using SMTP"""
    try:
        # Get SMTP configuration
        config = TestConfiguration.query.first()
        if not config:
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Parse email addresses
        recipients = [email.strip() for email in email_addresses.split(',') if email.strip()]
        if not recipients:
            return
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = 'noreply@taytech.com'
        msg['Subject'] = subject
        
        # Add message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Send to each recipient
        for recipient in recipients:
            try:
                msg['To'] = recipient
                
                # Connect to SMTP server
                server = smtplib.SMTP(config.smtp_server, config.smtp_port)
                server.starttls()
                
                # In a real implementation, you would use proper authentication
                # server.login(username, password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(msg['From'], recipient, text)
                server.quit()
                
                print(f"Email notification sent to {recipient}")
                
            except Exception as e:
                print(f"Failed to send email to {recipient}: {e}")
        
    except Exception as e:
        print(f"Failed to send email notification: {e}")

def cleanup_old_logs():
    """Clean up old logs based on retention policy"""
    try:
        # Get test configuration
        config = TestConfiguration.query.first()
        if not config:
            return
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=config.log_retention_days)
        
        # Clean up communication logs
        old_comm_logs = CommunicationLog.query.filter(
            CommunicationLog.timestamp < cutoff_date
        ).count()
        
        if old_comm_logs > 0:
            CommunicationLog.query.filter(
                CommunicationLog.timestamp < cutoff_date
            ).delete()
            
            print(f"Cleaned up {old_comm_logs} old communication log entries")
        
        # Clean up old test results (optional - be careful with this)
        # old_results = TestResult.query.filter(
        #     TestResult.test_date < cutoff_date
        # ).count()
        
        db.session.commit()
        
    except Exception as e:
        print(f"Failed to cleanup old logs: {e}")
        db.session.rollback()

# ============================================================================
# ERROR RECOVERY PROCEDURES
# ============================================================================

def recover_from_system_error():
    """Attempt to recover from system-level errors"""
    try:
        # Check and restart failed connections
        failed_connections = Connection.query.filter_by(is_active=False).all()
        
        for connection in failed_connections:
            if attempt_reconnection(connection.id):
                print(f"Recovered connection: {connection.connection_name}")
        
        # Check for stuck test executions
        stuck_executions = TestExecution.query.filter(
            TestExecution.status == 'RUNNING',
            TestExecution.start_time < datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        for execution in stuck_executions:
            execution.status = 'FAILED'
            execution.end_time = datetime.utcnow()
            execution.error_message = 'Test execution timed out and was automatically stopped'
            
            print(f"Recovered stuck execution: {execution.id}")
        
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"System recovery failed: {e}")
        return False

# ============================================================================
# BACKGROUND TASK PROCESSING SYSTEM
# ============================================================================

import threading
import queue
import time
from enum import Enum

class TaskType(Enum):
    TEST_EXECUTION = "test_execution"
    CONNECTION_CHECK = "connection_check"
    LOG_CLEANUP = "log_cleanup"
    NOTIFICATION = "notification"
    SYSTEM_RECOVERY = "system_recovery"

class BackgroundTask:
    def __init__(self, task_type, task_data, priority=1):
        self.task_type = task_type
        self.task_data = task_data
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.attempts = 0
        self.max_attempts = 3

class BackgroundTaskProcessor:
    def __init__(self):
        self.task_queue = queue.PriorityQueue()
        self.workers = []
        self.is_running = False
        self.worker_count = 3
        
    def start(self):
        """Start the background task processor"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start worker threads
        for i in range(self.worker_count):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        # Start periodic tasks
        periodic_thread = threading.Thread(target=self._periodic_tasks)
        periodic_thread.daemon = True
        periodic_thread.start()
        
        print(f"Background task processor started with {self.worker_count} workers")
    
    def stop(self):
        """Stop the background task processor"""
        self.is_running = False
        print("Background task processor stopped")
    
    def add_task(self, task_type, task_data, priority=1):
        """Add a task to the processing queue"""
        task = BackgroundTask(task_type, task_data, priority)
        # Use negative priority for priority queue (lower number = higher priority)
        self.task_queue.put((-priority, task.created_at, task))
        print(f"Added task: {task_type.value} with priority {priority}")
    
    def _worker(self, worker_id):
        """Worker thread that processes tasks"""
        print(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get task from queue with timeout
                try:
                    priority, created_at, task = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Process the task
                success = self._process_task(task, worker_id)
                
                # Handle task result
                if not success and task.attempts < task.max_attempts:
                    task.attempts += 1
                    # Re-queue with lower priority
                    self.task_queue.put((-task.priority + task.attempts, task.created_at, task))
                    print(f"Re-queued task {task.task_type.value} (attempt {task.attempts})")
                
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                time.sleep(1)
        
        print(f"Worker {worker_id} stopped")
    
    def _process_task(self, task, worker_id):
        """Process a single task"""
        try:
            print(f"Worker {worker_id} processing: {task.task_type.value}")
            
            if task.task_type == TaskType.TEST_EXECUTION:
                return self._process_test_execution(task.task_data)
            elif task.task_type == TaskType.CONNECTION_CHECK:
                return self._process_connection_check(task.task_data)
            elif task.task_type == TaskType.LOG_CLEANUP:
                return self._process_log_cleanup(task.task_data)
            elif task.task_type == TaskType.NOTIFICATION:
                return self._process_notification(task.task_data)
            elif task.task_type == TaskType.SYSTEM_RECOVERY:
                return self._process_system_recovery(task.task_data)
            else:
                print(f"Unknown task type: {task.task_type}")
                return False
                
        except Exception as e:
            print(f"Task processing error: {e}")
            return False
    
    def _process_test_execution(self, task_data):
        """Process test execution task"""
        try:
            execution_id = task_data.get('execution_id')
            if not execution_id:
                return False
            
            # Simulate test execution
            execution = TestExecution.query.get(execution_id)
            if not execution:
                return False
            
            # Update execution status
            execution.status = 'RUNNING'
            execution.progress = 0
            execution.current_step = 'Starting test execution'
            db.session.commit()
            
            # Simulate test steps
            steps = ['Initializing', 'Connecting', 'Testing', 'Validating', 'Completing']
            for i, step in enumerate(steps):
                time.sleep(2)  # Simulate work
                
                execution.progress = (i + 1) * 20
                execution.current_step = step
                db.session.commit()
                
                # Check if test was cancelled
                execution = TestExecution.query.get(execution_id)
                if execution.status == 'CANCELLED':
                    return True
            
            # Complete test
            execution.status = 'COMPLETED'
            execution.end_time = datetime.utcnow()
            execution.progress = 100
            execution.current_step = 'Test completed'
            db.session.commit()
            
            # Send success notification
            send_test_success_notification(execution)
            
            return True
            
        except Exception as e:
            print(f"Test execution task error: {e}")
            return False
    
    def _process_connection_check(self, task_data):
        """Process connection check task"""
        try:
            connection_id = task_data.get('connection_id')
            if connection_id:
                # Check specific connection
                return test_single_connection(Connection.query.get(connection_id))
            else:
                # Check all connections
                result = check_test_equipment_connections()
                return result['success']
                
        except Exception as e:
            print(f"Connection check task error: {e}")
            return False
    
    def _process_log_cleanup(self, task_data):
        """Process log cleanup task"""
        try:
            cleanup_old_logs()
            return True
            
        except Exception as e:
            print(f"Log cleanup task error: {e}")
            return False
    
    def _process_notification(self, task_data):
        """Process notification task"""
        try:
            email_addresses = task_data.get('email_addresses')
            subject = task_data.get('subject')
            message = task_data.get('message')
            
            if email_addresses and subject and message:
                send_email_notification(email_addresses, subject, message)
                return True
            
            return False
            
        except Exception as e:
            print(f"Notification task error: {e}")
            return False
    
    def _process_system_recovery(self, task_data):
        """Process system recovery task"""
        try:
            return recover_from_system_error()
            
        except Exception as e:
            print(f"System recovery task error: {e}")
            return False
    
    def _periodic_tasks(self):
        """Run periodic maintenance tasks"""
        print("Periodic tasks thread started")
        
        while self.is_running:
            try:
                # Run every 5 minutes
                time.sleep(300)
                
                if not self.is_running:
                    break
                
                # Add periodic tasks
                self.add_task(TaskType.CONNECTION_CHECK, {}, priority=3)
                
                # Run log cleanup daily (check every 5 minutes but only run once per day)
                current_hour = datetime.utcnow().hour
                if current_hour == 2:  # Run at 2 AM
                    self.add_task(TaskType.LOG_CLEANUP, {}, priority=5)
                
                # System recovery check
                self.add_task(TaskType.SYSTEM_RECOVERY, {}, priority=4)
                
            except Exception as e:
                print(f"Periodic tasks error: {e}")
                time.sleep(60)
        
        print("Periodic tasks thread stopped")

# Global task processor instance
task_processor = BackgroundTaskProcessor()

# ============================================================================
# BACKGROUND TASK API ENDPOINTS
# ============================================================================

@app.route('/api/tasks/status', methods=['GET'])
@login_required
@require_permission('view_system_status')
def api_get_task_status():
    """Get background task processor status"""
    try:
        return jsonify({
            'success': True,
            'status': {
                'is_running': task_processor.is_running,
                'worker_count': task_processor.worker_count,
                'queue_size': task_processor.task_queue.qsize(),
                'workers_active': len(task_processor.workers)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get task status: {str(e)}'})

@app.route('/api/tasks/start', methods=['POST'])
@login_required
@require_permission('manage_system_settings')
def api_start_task_processor():
    """Start the background task processor"""
    try:
        task_processor.start()
        
        return jsonify({
            'success': True,
            'message': 'Background task processor started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to start task processor: {str(e)}'})

@app.route('/api/tasks/stop', methods=['POST'])
@login_required
@require_permission('manage_system_settings')
def api_stop_task_processor():
    """Stop the background task processor"""
    try:
        task_processor.stop()
        
        return jsonify({
            'success': True,
            'message': 'Background task processor stopped'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to stop task processor: {str(e)}'})

# ============================================================================
# AUDIT LOGGING AND SECURITY SYSTEM
# ============================================================================

def log_audit_event(user_id, action, resource_type, resource_id=None, details=None, ip_address=None):
    """Log security and audit events"""
    try:
        # Create audit log entry
        audit_log = {
            'user_id': user_id,
            'username': current_user.username if current_user and current_user.is_authenticated else 'Anonymous',
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details,
            'ip_address': ip_address or request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session.get('_id') if session else None
        }
        
        # In a real implementation, you would store this in a dedicated audit log table
        # For now, we'll print it and could store in a file or external logging service
        print(f"AUDIT LOG: {audit_log}")
        
        # Also log critical security events to communication logs
        if action in ['LOGIN_FAILED', 'PERMISSION_DENIED', 'UNAUTHORIZED_ACCESS']:
            log_communication_event(
                connection_id=None,
                event_type='SECURITY_EVENT',
                direction='SYSTEM',
                message=f'Security event: {action} by user {audit_log["username"]}',
                status='WARNING',
                data=str(audit_log)
            )
        
    except Exception as e:
        print(f"Failed to log audit event: {e}")

def enhanced_require_permission(permission_name, log_access=True):
    """Enhanced permission decorator with audit logging"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if log_access:
                    log_audit_event(
                        user_id=None,
                        action='UNAUTHORIZED_ACCESS',
                        resource_type='ENDPOINT',
                        resource_id=request.endpoint,
                        details=f'Attempted to access {request.endpoint} without authentication'
                    )
                return redirect(url_for('login'))
            
            # Check if user has the required permission
            if not has_permission(current_user, permission_name):
                if log_access:
                    log_audit_event(
                        user_id=current_user.id,
                        action='PERMISSION_DENIED',
                        resource_type='ENDPOINT',
                        resource_id=request.endpoint,
                        details=f'User lacks permission: {permission_name}'
                    )
                
                flash(f'Bu işlem için yetkiniz bulunmamaktadır. Gerekli yetki: {permission_name}', 'error')
                return redirect(url_for('index'))
            
            # Log successful access for sensitive operations
            if log_access and permission_name in ['manage_system_settings', 'manage_users', 'manage_scheduled_tests']:
                log_audit_event(
                    user_id=current_user.id,
                    action='ACCESS_GRANTED',
                    resource_type='ENDPOINT',
                    resource_id=request.endpoint,
                    details=f'Accessed {request.endpoint} with permission: {permission_name}'
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_test_execution_permissions(user, test_scenario_id, pcba_model_id):
    """Validate if user can execute specific test scenarios and models"""
    try:
        # Check basic test execution permission
        if not has_permission(user, 'start_manual_tests'):
            return False, 'No permission to start manual tests'
        
        # Check if user can access specific test scenario
        test_scenario = TestScenario.query.get(test_scenario_id)
        if not test_scenario:
            return False, 'Test scenario not found'
        
        if not test_scenario.is_active:
            return False, 'Test scenario is not active'
        
        # Check if user can access specific PCBA model
        pcba_model = PCBAModel.query.get(pcba_model_id)
        if not pcba_model:
            return False, 'PCBA model not found'
        
        if not pcba_model.is_active:
            return False, 'PCBA model is not active'
        
        # Additional role-based restrictions
        if user.role == 'operator':
            # Operators might have restrictions on certain test types
            restricted_test_types = ['CALIBRATION', 'FIRMWARE_UPDATE']
            if test_scenario.test_type and test_scenario.test_type.type_name in restricted_test_types:
                return False, f'Operators cannot run {test_scenario.test_type.type_name} tests'
        
        return True, 'Permission granted'
        
    except Exception as e:
        return False, f'Permission validation error: {str(e)}'

def validate_scheduled_test_permissions(user, action, scheduled_test=None):
    """Validate permissions for scheduled test operations"""
    try:
        # Basic permission check
        if action in ['create', 'update', 'delete', 'toggle']:
            if not has_permission(user, 'manage_scheduled_tests'):
                return False, 'No permission to manage scheduled tests'
        elif action == 'view':
            if not has_permission(user, 'view_scheduled_tests'):
                return False, 'No permission to view scheduled tests'
        
        # Additional checks for specific actions
        if scheduled_test and action in ['update', 'delete']:
            # Check if user created the scheduled test or is admin
            if user.role != 'admin' and scheduled_test.created_by != user.id:
                return False, 'Can only modify scheduled tests you created'
        
        return True, 'Permission granted'
        
    except Exception as e:
        return False, f'Permission validation error: {str(e)}'

def validate_configuration_access(user, config_section):
    """Validate access to configuration sections"""
    try:
        # Basic system settings permission
        if not has_permission(user, 'manage_system_settings'):
            return False, 'No permission to manage system settings'
        
        # Additional restrictions for critical sections
        critical_sections = ['security', 'database', 'network']
        if config_section in critical_sections and user.role != 'admin':
            return False, f'Only administrators can modify {config_section} settings'
        
        return True, 'Permission granted'
        
    except Exception as e:
        return False, f'Permission validation error: {str(e)}'

def check_rate_limiting(user_id, action, limit_per_minute=10):
    """Simple rate limiting for API endpoints"""
    try:
        # In a real implementation, you would use Redis or similar
        # For now, we'll use a simple in-memory approach
        
        if not hasattr(check_rate_limiting, 'requests'):
            check_rate_limiting.requests = {}
        
        current_time = datetime.utcnow()
        key = f"{user_id}:{action}"
        
        # Clean old entries
        if key in check_rate_limiting.requests:
            check_rate_limiting.requests[key] = [
                req_time for req_time in check_rate_limiting.requests[key]
                if (current_time - req_time).total_seconds() < 60
            ]
        else:
            check_rate_limiting.requests[key] = []
        
        # Check rate limit
        if len(check_rate_limiting.requests[key]) >= limit_per_minute:
            return False, 'Rate limit exceeded'
        
        # Add current request
        check_rate_limiting.requests[key].append(current_time)
        
        return True, 'Rate limit OK'
        
    except Exception as e:
        return True, 'Rate limiting error - allowing request'

def validate_input_security(data, allowed_fields=None, max_length=1000):
    """Validate input data for security issues"""
    try:
        if not isinstance(data, dict):
            return False, 'Invalid data format'
        
        # Check for allowed fields
        if allowed_fields:
            for field in data.keys():
                if field not in allowed_fields:
                    return False, f'Field not allowed: {field}'
        
        # Check for SQL injection patterns
        dangerous_patterns = [
            'union select', 'drop table', 'delete from', 'insert into',
            'update set', 'exec(', 'execute(', 'sp_', 'xp_'
        ]
        
        for field, value in data.items():
            if isinstance(value, str):
                # Check length
                if len(value) > max_length:
                    return False, f'Field {field} exceeds maximum length'
                
                # Check for dangerous patterns
                value_lower = value.lower()
                for pattern in dangerous_patterns:
                    if pattern in value_lower:
                        return False, f'Potentially dangerous input detected in {field}'
        
        return True, 'Input validation passed'
        
    except Exception as e:
        return False, f'Input validation error: {str(e)}'

# ============================================================================
# ENHANCED SECURITY API ENDPOINTS
# ============================================================================

@app.route('/api/security/audit-logs', methods=['GET'])
@login_required
@enhanced_require_permission('view_audit_logs')
def api_get_audit_logs():
    """Get audit logs (admin only)"""
    try:
        # Only admins can view audit logs
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'})
        
        # In a real implementation, you would query audit log table
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'message': 'Audit logs would be returned here',
            'logs': []
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get audit logs: {str(e)}'})

@app.route('/api/security/active-sessions', methods=['GET'])
@login_required
@enhanced_require_permission('view_system_status')
def api_get_active_sessions():
    """Get active user sessions"""
    try:
        # Only admins can view active sessions
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'})
        
        # In a real implementation, you would track active sessions
        # For now, return current user session info
        return jsonify({
            'success': True,
            'sessions': [{
                'user_id': current_user.id,
                'username': current_user.username,
                'login_time': 'Current session',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get active sessions: {str(e)}'})

@app.route('/api/security/permissions/validate', methods=['POST'])
@login_required
def api_validate_permissions():
    """Validate user permissions for specific actions"""
    try:
        data = request.get_json()
        
        # Validate input
        allowed_fields = ['action', 'resource_type', 'resource_id']
        is_valid, message = validate_input_security(data, allowed_fields)
        if not is_valid:
            return jsonify({'success': False, 'message': message})
        
        action = data.get('action')
        resource_type = data.get('resource_type')
        resource_id = data.get('resource_id')
        
        # Validate permissions based on resource type
        if resource_type == 'test_execution':
            if action == 'start':
                test_scenario_id = data.get('test_scenario_id')
                pcba_model_id = data.get('pcba_model_id')
                
                is_valid, message = validate_test_execution_permissions(
                    current_user, test_scenario_id, pcba_model_id
                )
                
                return jsonify({
                    'success': is_valid,
                    'message': message,
                    'has_permission': is_valid
                })
        
        elif resource_type == 'scheduled_test':
            scheduled_test = None
            if resource_id:
                scheduled_test = ScheduledTest.query.get(resource_id)
            
            is_valid, message = validate_scheduled_test_permissions(
                current_user, action, scheduled_test
            )
            
            return jsonify({
                'success': is_valid,
                'message': message,
                'has_permission': is_valid
            })
        
        return jsonify({
            'success': False,
            'message': 'Unknown resource type or action'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Permission validation failed: {str(e)}'})

# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/test-stats', methods=['GET'])
@login_required
def api_dashboard_test_stats():
    """Get test statistics for dashboard"""
    try:
        # Get test statistics for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        total_tests = TestResult.query.filter(
            TestResult.test_date >= thirty_days_ago
        ).count()
        
        passed_tests = TestResult.query.filter(
            TestResult.test_date >= thirty_days_ago,
            TestResult.test_status == 'PASS'
        ).count()
        
        failed_tests = TestResult.query.filter(
            TestResult.test_date >= thirty_days_ago,
            TestResult.test_status == 'FAIL'
        ).count()
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return jsonify({
            'success': True,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': round(success_rate, 1)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get dashboard stats: {str(e)}'})

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    """404 - Sayfa bulunamadı hatası"""
    return render_template('error.html', 
                         error_code=404,
                         error_message="Aradığınız sayfa bulunamadı.",
                         error_description="Girdiğiniz adres mevcut değil veya kaldırılmış olabilir."), 404

@app.errorhandler(500)
def internal_error(error):
    """500 - Sunucu hatası"""
    db.session.rollback()
    return render_template('error.html',
                         error_code=500,
                         error_message="Sunucu hatası oluştu.",
                         error_description="Bir hata oluştu. Lütfen daha sonra tekrar deneyin."), 500

@app.errorhandler(403)
def forbidden_error(error):
    """403 - Yetkisiz erişim hatası"""
    return render_template('error.html',
                         error_code=403,
                         error_message="Bu sayfaya erişim yetkiniz yok.",
                         error_description="Bu işlemi gerçekleştirmek için gerekli yetkilere sahip değilsiniz."), 403

@app.errorhandler(Exception)
def handle_exception(e):
    """Genel exception handler"""
    # Veritabanı session'ını temizle
    db.session.rollback()
    
    # Development modunda detaylı hata göster
    if app.debug:
        return render_template('error.html',
                             error_code=500,
                             error_message=f"Hata: {str(e)}",
                             error_description="Development modunda detaylı hata bilgisi gösteriliyor."), 500
    
    # Production modunda genel hata mesajı
    return render_template('error.html',
                         error_code=500,
                         error_message="Beklenmeyen bir hata oluştu.",
                         error_description="Sistem yöneticisi ile iletişime geçin."), 500

# ============================================================================
# AUTOMATED TEST EXECUTION SERVICES
# ============================================================================

import threading
import time
import queue
import random
from datetime import datetime, timedelta

class TestRunner:
    """Individual test execution runner"""
    
    def __init__(self, execution_id):
        self.execution_id = execution_id
        self.execution = None
        self.is_cancelled = False
        self.current_progress = 0
        
    def run(self):
        """Main test execution method"""
        try:
            with app.app_context():
                # Get execution record
                self.execution = TestExecution.query.get(self.execution_id)
                if not self.execution:
                    raise Exception(f"Test execution {self.execution_id} not found")
                
                # Update status to running
                self.execution.status = 'RUNNING'
                self.execution.start_time = datetime.utcnow()
                db.session.commit()
                
                # Get test scenario and parameters
                test_scenario = self.execution.test_scenario
                if not test_scenario or not test_scenario.test_parameters:
                    raise Exception("Test scenario or parameters not found")
                
                test_params = test_scenario.test_parameters
                test_results = {}
                
                # Execute test steps
                self._execute_test_step("Initializing", self._initialize_test, 10)
                self._execute_test_step("Connecting to Hardware", self._connect_hardware, 20)
                
                # Execute parameter tests
                if 'voltage_range' in test_params:
                    self._execute_test_step("Voltage Test", 
                                          lambda: self._test_voltage(test_params['voltage_range']), 40)
                    test_results['voltage'] = self.execution.test_data.get('voltage', {})
                
                if 'current_range' in test_params:
                    self._execute_test_step("Current Test", 
                                          lambda: self._test_current(test_params['current_range']), 60)
                    test_results['current'] = self.execution.test_data.get('current', {})
                
                if 'frequency_test' in test_params:
                    self._execute_test_step("Frequency Test", 
                                          lambda: self._test_frequency(test_params['frequency_test']), 80)
                    test_results['frequency'] = self.execution.test_data.get('frequency', {})
                
                self._execute_test_step("Finalizing", self._finalize_test, 100)
                
                # Determine final result
                final_result = 'PASS'
                for test_name, result in test_results.items():
                    if result.get('status') == 'FAIL':
                        final_result = 'FAIL'
                        break
                
                # Update execution record
                self.execution.status = 'COMPLETED'
                self.execution.end_time = datetime.utcnow()
                self.execution.final_result = final_result
                self.execution.progress = 100
                self.execution.current_step = 'Completed'
                db.session.commit()
                
                print(f"Test execution {self.execution_id} completed with result: {final_result}")
                
        except Exception as e:
            with app.app_context():
                if self.execution:
                    self.execution.status = 'FAILED'
                    self.execution.end_time = datetime.utcnow()
                    self.execution.error_message = str(e)
                    self.execution.progress = self.current_progress
                    db.session.commit()
                print(f"Test execution {self.execution_id} failed: {str(e)}")
    
    def _execute_test_step(self, step_name, test_function, target_progress):
        """Execute a single test step with progress tracking"""
        if self.is_cancelled:
            raise Exception("Test cancelled by user")
        
        with app.app_context():
            self.execution.current_step = step_name
            self.execution.progress = target_progress
            self.current_progress = target_progress
            db.session.commit()
        
        print(f"Executing step: {step_name} ({target_progress}%)")
        
        # Execute the test function
        test_function()
        
        # Simulate some processing time
        time.sleep(1)
    
    def _initialize_test(self):
        """Initialize test environment"""
        # Simulate initialization
        time.sleep(0.5)
        
        # Initialize test_data if not exists
        if not self.execution.test_data:
            self.execution.test_data = {}
    
    def _connect_hardware(self):
        """Connect to hardware interfaces"""
        # Simulate hardware connection
        time.sleep(1)
        
        # In real implementation, this would connect to actual hardware
        # For now, we'll simulate a successful connection
        pass
    
    def _test_voltage(self, voltage_params):
        """Execute voltage test"""
        time.sleep(2)  # Simulate test duration
        
        # Simulate voltage measurement
        min_voltage = voltage_params['min']
        max_voltage = voltage_params['max']
        
        # Generate realistic measurement with some variation
        measured_voltage = round(random.uniform(min_voltage - 0.1, max_voltage + 0.1), 2)
        
        # Determine test result
        status = 'PASS' if min_voltage <= measured_voltage <= max_voltage else 'FAIL'
        
        # Store result
        voltage_result = {
            'measured': measured_voltage,
            'expected_min': min_voltage,
            'expected_max': max_voltage,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not self.execution.test_data:
            self.execution.test_data = {}
        self.execution.test_data['voltage'] = voltage_result
        db.session.commit()
    
    def _test_current(self, current_params):
        """Execute current test"""
        time.sleep(2)  # Simulate test duration
        
        # Simulate current measurement
        min_current = current_params['min']
        max_current = current_params['max']
        
        # Generate realistic measurement with some variation
        measured_current = round(random.uniform(min_current - 0.05, max_current + 0.05), 3)
        
        # Determine test result
        status = 'PASS' if min_current <= measured_current <= max_current else 'FAIL'
        
        # Store result
        current_result = {
            'measured': measured_current,
            'expected_min': min_current,
            'expected_max': max_current,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not self.execution.test_data:
            self.execution.test_data = {}
        self.execution.test_data['current'] = current_result
        db.session.commit()
    
    def _test_frequency(self, frequency_params):
        """Execute frequency test"""
        time.sleep(2)  # Simulate test duration
        
        # Simulate frequency measurement
        target_freq = frequency_params['target']
        tolerance = frequency_params['tolerance']
        
        # Generate realistic measurement with some variation
        measured_freq = random.randint(
            target_freq - tolerance - 5,
            target_freq + tolerance + 5
        )
        
        # Determine test result
        min_freq = target_freq - tolerance
        max_freq = target_freq + tolerance
        status = 'PASS' if min_freq <= measured_freq <= max_freq else 'FAIL'
        
        # Store result
        frequency_result = {
            'measured': measured_freq,
            'expected': target_freq,
            'tolerance': tolerance,
            'min_acceptable': min_freq,
            'max_acceptable': max_freq,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not self.execution.test_data:
            self.execution.test_data = {}
        self.execution.test_data['frequency'] = frequency_result
        db.session.commit()
    
    def _finalize_test(self):
        """Finalize test execution"""
        time.sleep(0.5)
        
        # Cleanup and finalization
        # In real implementation, this would disconnect hardware, cleanup resources, etc.
        pass
    
    def cancel(self):
        """Cancel the test execution"""
        self.is_cancelled = True
        with app.app_context():
            if self.execution:
                self.execution.status = 'CANCELLED'
                self.execution.end_time = datetime.utcnow()
                self.execution.current_step = 'Cancelled'
                db.session.commit()

class TestExecutorService:
    """Main service for managing test executions"""
    
    def __init__(self):
        self.running_tests = {}  # execution_id -> TestRunner
        self.test_threads = {}   # execution_id -> Thread
        self.max_concurrent_tests = 3
        
    def start_manual_test(self, test_scenario_id, pcba_model_id, serial_number, user_id):
        """Start a manual test execution"""
        try:
            # Check concurrent test limit
            if len(self.running_tests) >= self.max_concurrent_tests:
                return {'success': False, 'message': f'Maximum {self.max_concurrent_tests} concurrent tests allowed'}
            
            # Validate inputs
            test_scenario = TestScenario.query.get(test_scenario_id)
            if not test_scenario:
                return {'success': False, 'message': 'Test scenario not found'}
            
            pcba_model = PCBAModel.query.get(pcba_model_id)
            if not pcba_model:
                return {'success': False, 'message': 'PCBA model not found'}
            
            # Check for duplicate serial number in running tests
            for runner in self.running_tests.values():
                if (runner.execution and 
                    runner.execution.serial_number == serial_number and 
                    runner.execution.pcba_model_id == pcba_model_id):
                    return {'success': False, 'message': 'Test with this serial number is already running'}
            
            # Create test execution record
            execution = TestExecution(
                test_scenario_id=test_scenario_id,
                pcba_model_id=pcba_model_id,
                serial_number=serial_number,
                status='PENDING',
                execution_type='MANUAL',
                user_id=user_id,
                progress=0,
                current_step='Initializing'
            )
            
            db.session.add(execution)
            db.session.commit()
            
            # Create and start test runner
            runner = TestRunner(execution.id)
            thread = threading.Thread(target=runner.run, daemon=True)
            
            self.running_tests[execution.id] = runner
            self.test_threads[execution.id] = thread
            
            thread.start()
            
            return {
                'success': True, 
                'message': 'Test started successfully',
                'execution_id': execution.id
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to start test: {str(e)}'}
    
    def start_scheduled_test(self, scheduled_test_id):
        """Start a scheduled test execution"""
        try:
            scheduled_test = ScheduledTest.query.get(scheduled_test_id)
            if not scheduled_test:
                return {'success': False, 'message': 'Scheduled test not found'}
            
            # Generate auto serial number
            serial_number = f"{scheduled_test.serial_number_prefix or 'AUTO'}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return self.start_manual_test(
                scheduled_test.test_scenario_id,
                scheduled_test.pcba_model_id,
                serial_number,
                scheduled_test.created_by
            )
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to start scheduled test: {str(e)}'}
    
    def stop_test(self, execution_id):
        """Stop a running test"""
        try:
            if execution_id in self.running_tests:
                runner = self.running_tests[execution_id]
                runner.cancel()
                
                # Wait for thread to finish (with timeout)
                if execution_id in self.test_threads:
                    thread = self.test_threads[execution_id]
                    thread.join(timeout=5)
                
                # Cleanup
                self._cleanup_test(execution_id)
                
                return {'success': True, 'message': 'Test stopped successfully'}
            else:
                return {'success': False, 'message': 'Test not found or not running'}
                
        except Exception as e:
            return {'success': False, 'message': f'Failed to stop test: {str(e)}'}
    
    def get_test_status(self, execution_id):
        """Get current test status"""
        try:
            execution = TestExecution.query.get(execution_id)
            if not execution:
                return {'success': False, 'message': 'Test execution not found'}
            
            return {
                'success': True,
                'execution': execution.to_dict(),
                'is_running': execution_id in self.running_tests
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to get test status: {str(e)}'}
    
    def get_running_tests(self):
        """Get list of currently running tests"""
        try:
            running_executions = []
            for execution_id in list(self.running_tests.keys()):
                execution = TestExecution.query.get(execution_id)
                if execution:
                    running_executions.append(execution.to_dict())
                else:
                    # Cleanup orphaned test
                    self._cleanup_test(execution_id)
            
            return {
                'success': True,
                'running_tests': running_executions,
                'count': len(running_executions)
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to get running tests: {str(e)}'}
    
    def _cleanup_test(self, execution_id):
        """Clean up completed or cancelled test"""
        if execution_id in self.running_tests:
            del self.running_tests[execution_id]
        if execution_id in self.test_threads:
            del self.test_threads[execution_id]
    
    def cleanup_completed_tests(self):
        """Clean up completed test threads"""
        completed_tests = []
        for execution_id, thread in self.test_threads.items():
            if not thread.is_alive():
                completed_tests.append(execution_id)
        
        for execution_id in completed_tests:
            self._cleanup_test(execution_id)

# ============================================================================
# TEST SCHEDULER SERVICE
# ============================================================================

class TestScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Register cleanup on exit
        atexit.register(lambda: self.scheduler.shutdown())
        
    def add_scheduled_test(self, scheduled_test):
        """Add a new scheduled test to the scheduler"""
        try:
            job_id = f"scheduled_test_{scheduled_test.id}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            if scheduled_test.schedule_type == 'ONCE':
                # Schedule for specific datetime
                self.scheduler.add_job(
                    func=self._execute_scheduled_test,
                    args=[scheduled_test.id],
                    trigger='date',
                    run_date=scheduled_test.next_run,
                    id=job_id,
                    name=f"Once: {scheduled_test.name}"
                )
            elif scheduled_test.schedule_type == 'DAILY':
                # Schedule daily at specific time
                self.scheduler.add_job(
                    func=self._execute_scheduled_test,
                    args=[scheduled_test.id],
                    trigger='cron',
                    hour=scheduled_test.schedule_time.hour,
                    minute=scheduled_test.schedule_time.minute,
                    id=job_id,
                    name=f"Daily: {scheduled_test.name}"
                )
            elif scheduled_test.schedule_type == 'WEEKLY':
                # Schedule weekly on specific days
                days = [int(d) for d in scheduled_test.schedule_days.split(',') if d.strip()]
                day_of_week = ','.join([str(d-1) for d in days])  # APScheduler uses 0-6 for Mon-Sun
                
                self.scheduler.add_job(
                    func=self._execute_scheduled_test,
                    args=[scheduled_test.id],
                    trigger='cron',
                    day_of_week=day_of_week,
                    hour=scheduled_test.schedule_time.hour,
                    minute=scheduled_test.schedule_time.minute,
                    id=job_id,
                    name=f"Weekly: {scheduled_test.name}"
                )
            elif scheduled_test.schedule_type == 'MONTHLY':
                # Schedule monthly on first day of month
                self.scheduler.add_job(
                    func=self._execute_scheduled_test,
                    args=[scheduled_test.id],
                    trigger='cron',
                    day=1,
                    hour=scheduled_test.schedule_time.hour,
                    minute=scheduled_test.schedule_time.minute,
                    id=job_id,
                    name=f"Monthly: {scheduled_test.name}"
                )
            
            print(f"✓ Scheduled test added: {scheduled_test.name} ({scheduled_test.schedule_type})")
            return True
            
        except Exception as e:
            print(f"✗ Failed to add scheduled test: {str(e)}")
            return False
    
    def remove_scheduled_test(self, scheduled_test_id):
        """Remove a scheduled test from the scheduler"""
        try:
            job_id = f"scheduled_test_{scheduled_test_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                print(f"✓ Scheduled test removed: {job_id}")
                return True
            return False
        except Exception as e:
            print(f"✗ Failed to remove scheduled test: {str(e)}")
            return False
    
    def update_scheduled_test(self, scheduled_test):
        """Update an existing scheduled test"""
        # Remove and re-add
        self.remove_scheduled_test(scheduled_test.id)
        return self.add_scheduled_test(scheduled_test)
    
    def get_scheduled_jobs(self):
        """Get list of all scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def _execute_scheduled_test(self, scheduled_test_id):
        """Execute a scheduled test"""
        try:
            with app.app_context():
                scheduled_test = ScheduledTest.query.get(scheduled_test_id)
                if not scheduled_test or not scheduled_test.is_active:
                    print(f"Scheduled test {scheduled_test_id} not found or inactive")
                    return
                
                print(f"Executing scheduled test: {scheduled_test.name}")
                
                # Generate unique serial number for scheduled test
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                serial_number = f"SCHED_{scheduled_test.id}_{timestamp}"
                
                # Start the test using test executor service
                execution_id = test_executor_service.start_test(
                    test_scenario_id=scheduled_test.test_scenario_id,
                    pcba_model_id=scheduled_test.pcba_model_id,
                    serial_number=serial_number,
                    user_id=scheduled_test.created_by,
                    execution_type='SCHEDULED'
                )
                
                # Update last run time
                scheduled_test.last_run = datetime.utcnow()
                
                # Calculate next run time for recurring tests
                if scheduled_test.schedule_type != 'ONCE':
                    scheduled_test.next_run = self._calculate_next_run(scheduled_test)
                
                db.session.commit()
                
                print(f"✓ Scheduled test executed successfully: {execution_id}")
                
                # Send notification if configured
                if scheduled_test.notification_emails:
                    self._send_notification(scheduled_test, execution_id, 'STARTED')
                
        except Exception as e:
            print(f"✗ Failed to execute scheduled test {scheduled_test_id}: {str(e)}")
            
            # Send error notification
            try:
                with app.app_context():
                    scheduled_test = ScheduledTest.query.get(scheduled_test_id)
                    if scheduled_test and scheduled_test.notification_emails:
                        self._send_notification(scheduled_test, None, 'ERROR', str(e))
            except:
                pass
    
    def _calculate_next_run(self, scheduled_test):
        """Calculate next run time for recurring tests"""
        now = datetime.utcnow()
        
        if scheduled_test.schedule_type == 'DAILY':
            next_run = now.replace(
                hour=scheduled_test.schedule_time.hour,
                minute=scheduled_test.schedule_time.minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
            
        elif scheduled_test.schedule_type == 'WEEKLY':
            # Find next occurrence of scheduled days
            days = [int(d) for d in scheduled_test.schedule_days.split(',') if d.strip()]
            current_weekday = now.weekday() + 1  # Convert to 1-7 format
            
            next_day = None
            for day in sorted(days):
                if day > current_weekday:
                    next_day = day
                    break
            
            if next_day is None:
                next_day = min(days)  # Next week
                days_ahead = 7 - current_weekday + next_day
            else:
                days_ahead = next_day - current_weekday
            
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(
                hour=scheduled_test.schedule_time.hour,
                minute=scheduled_test.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
            
        elif scheduled_test.schedule_type == 'MONTHLY':
            # Next month, first day
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_run = now.replace(month=now.month + 1, day=1)
            
            next_run = next_run.replace(
                hour=scheduled_test.schedule_time.hour,
                minute=scheduled_test.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        
        return None
    
    def _send_notification(self, scheduled_test, execution_id, status, error_message=None):
        """Send email notification for scheduled test"""
        # TODO: Implement email notification
        # For now, just log the notification
        emails = scheduled_test.notification_emails.split(',')
        print(f"📧 Notification would be sent to: {emails}")
        print(f"   Test: {scheduled_test.name}")
        print(f"   Status: {status}")
        if execution_id:
            print(f"   Execution ID: {execution_id}")
        if error_message:
            print(f"   Error: {error_message}")
    
    def load_existing_scheduled_tests(self):
        """Load and schedule all existing active scheduled tests"""
        try:
            with app.app_context():
                scheduled_tests = ScheduledTest.query.filter_by(is_active=True).all()
                
                for scheduled_test in scheduled_tests:
                    self.add_scheduled_test(scheduled_test)
                
                print(f"✓ Loaded {len(scheduled_tests)} scheduled tests")
                
        except Exception as e:
            print(f"✗ Failed to load scheduled tests: {str(e)}")

# Global instances
test_executor_service = TestExecutorService()
test_scheduler = TestScheduler()

if __name__ == '__main__':
    init_db()
    print("Flask uygulaması başlatılıyor...")
    
    # Load existing scheduled tests
    print("Zamanlanmış testler yükleniyor...")
    test_scheduler.load_existing_scheduled_tests()
    
    # Start background task processor
    print("Background task processor başlatılıyor...")
    task_processor.start()
    
    # Debug: Route'ları listele
    print("Yüklenen route'lar:")
    for rule in app.url_map.iter_rules():
        if 'communication' in rule.rule:
            print(f"  {rule.rule} -> {rule.endpoint}")
    
    port = int(os.environ.get('FLASK_PORT', '9002'))
    print(f"Tarayıcınızda şu adresi açın: http://127.0.0.1:{port}")
    print("Eğer bağlantı reddedilirse, Windows Defender'da Python.exe'yi izin verilenler listesine ekleyin")
    # Docker container için 0.0.0.0, normal kullanım için 127.0.0.1 kullan
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '9002'))
    app.run(debug=True, host=host, port=port, use_reloader=False, threaded=True)