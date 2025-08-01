from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Flask uygulaması oluştur
app = Flask(__name__, 
            static_folder='dash/assets',
            template_folder='dash')

# Konfigürasyon
app.config['SECRET_KEY'] = 'pcba-test-system-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pcba_test_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Uzantıları başlat
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Kullanıcı yükleme callback'i
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Veritabanı Modelleri
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')  # admin, technician, operator
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
@login_required
def system_settings():
    # Sadece admin kullanıcıları görebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('system-settings.html')

@app.route('/test-parameters')
@login_required
def test_parameters():
    # Admin ve technician kullanıcıları görebilir
    if current_user.role not in ['admin', 'technician']:
        return redirect(url_for('dashboard'))
    pcba_models = PCBAModel.query.filter_by(is_active=True).all()
    return render_template('test-parameters.html', pcba_models=pcba_models)

# Test Type Management Routes
@app.route('/test-types')
@login_required
def test_types():
    # Sadece admin kullanıcıları görebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    test_types = TestType.query.all()
    return render_template('test-types.html', test_types=test_types)

@app.route('/add-test-type', methods=['GET', 'POST'])
@login_required
def add_test_type():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
@login_required
def edit_test_type(test_type_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
@login_required
def delete_test_type(test_type_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
@login_required
def users():
    # Sadece admin kullanıcıları görebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    # Sadece admin kullanıcıları görebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
@login_required
def edit_user(user_id):
    # Sadece admin kullanıcıları görebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
@login_required
def delete_user(user_id):
    # Sadece admin kullanıcıları silebilir
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
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
    
    tests = TestResult.query.order_by(TestResult.test_date.desc()).paginate(
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
def api_dashboard_stats():
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
            print("Veritabanı başlatıldı ve varsayılan veriler eklendi.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)