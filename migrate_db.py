#!/usr/bin/env python3
"""
PCBA Test System - Database Migration Script
Bu script veritabanı şemasını güncellemek için kullanılır.
"""

import os
import sys
from datetime import datetime, timedelta
from app import app, db, User, Role, Permission

def create_default_roles():
    """Varsayılan rolleri oluştur"""
    print("Varsayılan roller oluşturuluyor...")
    
    # Admin rolü
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            description='Sistem yöneticisi - Tüm yetkilere sahip'
        )
        db.session.add(admin_role)
        print("✓ Admin rolü oluşturuldu")
    
    # Operator rolü
    operator_role = Role.query.filter_by(name='operator').first()
    if not operator_role:
        operator_role = Role(
            name='operator',
            description='Test operatörü - Test çalıştırma yetkisi'
        )
        db.session.add(operator_role)
        print("✓ Operator rolü oluşturuldu")
    
    # Viewer rolü
    viewer_role = Role.query.filter_by(name='viewer').first()
    if not viewer_role:
        viewer_role = Role(
            name='viewer',
            description='Sadece görüntüleme yetkisi'
        )
        db.session.add(viewer_role)
        print("✓ Viewer rolü oluşturuldu")
    
    db.session.commit()

def create_default_permissions():
    """Varsayılan yetkileri oluştur"""
    print("Varsayılan yetkiler oluşturuluyor...")
    
    permissions = [
        ('user_management', 'Kullanıcı Yönetimi', 'Kullanıcı ekleme, düzenleme, silme'),
        ('role_management', 'Rol Yönetimi', 'Rol ekleme, düzenleme, silme'),
        ('test_run', 'Test Çalıştırma', 'Test çalıştırma yetkisi'),
        ('test_view', 'Test Görüntüleme', 'Test sonuçlarını görüntüleme'),
        ('report_generate', 'Rapor Oluşturma', 'Rapor oluşturma ve dışa aktarma'),
        ('system_settings', 'Sistem Ayarları', 'Sistem ayarlarını değiştirme'),
        ('manage_hardware', 'Donanım Yönetimi', 'Test donanımı yapılandırma ve yönetimi'),
        ('run_hardware_tests', 'Donanım Testleri', 'Gerçek donanım ile test çalıştırma'),
        ('manage_test_types', 'Test Tipi Yönetimi', 'Test tiplerini ekleme, düzenleme, silme'),
        ('manage_test_parameters', 'Test Parametre Yönetimi', 'Test parametrelerini yönetme'),
        ('manage_system_settings', 'Sistem Ayarları Yönetimi', 'Sistem ayarlarını değiştirme yetkisi')
    ]
    
    for perm_name, display_name, description in permissions:
        permission = Permission.query.filter_by(name=perm_name).first()
        if not permission:
            permission = Permission(
                name=perm_name,
                description=description
            )
            db.session.add(permission)
            print(f"✓ {display_name} yetkisi oluşturuldu")
    
    db.session.commit()

def assign_permissions_to_roles():
    """Rollere yetkileri ata"""
    print("Rollere yetkiler atanıyor...")
    
    admin_role = Role.query.filter_by(name='admin').first()
    operator_role = Role.query.filter_by(name='operator').first()
    viewer_role = Role.query.filter_by(name='viewer').first()
    
    # Admin'e tüm yetkileri ver
    if admin_role:
        all_permissions = Permission.query.all()
        for permission in all_permissions:
            if permission not in admin_role.permissions:
                admin_role.permissions.append(permission)
        print("✓ Admin rolüne tüm yetkiler atandı")
    
    # Operator'e test yetkilerini ver
    if operator_role:
        test_permissions = Permission.query.filter(
            Permission.name.in_(['test_run', 'test_view', 'report_generate'])
        ).all()
        for permission in test_permissions:
            if permission not in operator_role.permissions:
                operator_role.permissions.append(permission)
        print("✓ Operator rolüne test yetkileri atandı")
    
    # Viewer'a sadece görüntüleme yetkisi ver
    if viewer_role:
        view_permission = Permission.query.filter_by(name='test_view').first()
        if view_permission and view_permission not in viewer_role.permissions:
            viewer_role.permissions.append(view_permission)
        print("✓ Viewer rolüne görüntüleme yetkisi atandı")
    
    db.session.commit()

def update_existing_users():
    """Mevcut kullanıcıları güncelle"""
    print("Mevcut kullanıcılar güncelleniyor...")
    
    admin_role = Role.query.filter_by(name='admin').first()
    operator_role = Role.query.filter_by(name='operator').first()
    
    users = User.query.all()
    for user in users:
        if user.role_id is None:
            if user.role == 'admin':
                user.role_id = admin_role.id if admin_role else None
                print(f"✓ {user.username} admin rolüne atandı")
            elif user.role == 'operator':
                user.role_id = operator_role.id if operator_role else None
                print(f"✓ {user.username} operator rolüne atandı")
        
        if user.is_active is None:
            user.is_active = True
            print(f"✓ {user.username} aktif olarak işaretlendi")
    
    db.session.commit()

def create_default_admin():
    """Varsayılan admin kullanıcısı oluştur"""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        print("Varsayılan admin kullanıcısı oluşturuluyor...")
        admin_role = Role.query.filter_by(name='admin').first()
        
        admin_user = User(
            username='admin',
            email='admin@taytech.com',
            role='admin',
            role_id=admin_role.id if admin_role else None,
            is_active=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("✓ Varsayılan admin kullanıcısı oluşturuldu (admin/admin123)")

def create_communication_permissions():
    """Communication logging için gerekli izinleri oluştur"""
    print("Communication logging izinleri oluşturuluyor...")
    
    comm_permissions = [
        ('communication_view', 'Haberleşme Loglarını Görüntüleme', 'Haberleşme loglarını görüntüleyebilir'),
        ('communication_manage', 'Bağlantı Yönetimi', 'Test cihazı bağlantılarını yönetebilir'),
        ('communication_export', 'Log Dışa Aktarma', 'Haberleşme loglarını dışa aktarabilir'),
        ('communication_admin', 'Haberleşme Yöneticisi', 'Tüm haberleşme özelliklerine erişim')
    ]
    
    for name, display_name, description in comm_permissions:
        permission = Permission.query.filter_by(name=name).first()
        if not permission:
            permission = Permission(
                name=name,
                description=description
            )
            db.session.add(permission)
            print(f"✓ {display_name} izni oluşturuldu")
    
    db.session.commit()

def create_default_connections():
    """Varsayılan bağlantı konfigürasyonları oluştur"""
    print("Varsayılan bağlantı konfigürasyonları oluşturuluyor...")
    
    from app import ConnectionConfig
    
    # Örnek seri port bağlantısı
    serial_conn = ConnectionConfig.query.filter_by(name='Test DMM (Serial)').first()
    if not serial_conn:
        serial_conn = ConnectionConfig(
            name='Test DMM (Serial)',
            connection_type='serial',
            port='COM3',
            baud_rate=9600,
            data_bits=8,
            stop_bits=1,
            parity='none',
            timeout=5000,
            is_active=True
        )
        db.session.add(serial_conn)
        print("✓ Örnek seri port bağlantısı oluşturuldu")
    
    # Örnek TCP bağlantısı
    tcp_conn = ConnectionConfig.query.filter_by(name='Power Supply (TCP)').first()
    if not tcp_conn:
        tcp_conn = ConnectionConfig(
            name='Power Supply (TCP)',
            connection_type='tcp',
            ip_address='192.168.1.100',
            tcp_port=5025,
            timeout=5000,
            is_active=True
        )
        db.session.add(tcp_conn)
        print("✓ Örnek TCP bağlantısı oluşturuldu")
    
    db.session.commit()

def create_sample_communication_logs():
    """Test için örnek haberleşme logları oluştur"""
    print("Örnek haberleşme logları oluşturuluyor...")
    
    from app import CommunicationLog, ConnectionConfig
    import uuid
    
    # Bağlantıları al
    serial_conn = ConnectionConfig.query.filter_by(connection_type='serial').first()
    tcp_conn = ConnectionConfig.query.filter_by(connection_type='tcp').first()
    
    if serial_conn and tcp_conn:
        sample_logs = [
            {
                'connection_id': serial_conn.id,
                'direction': 'sent',
                'data_hex': '2A49444E3F0D0A',
                'data_ascii': '*IDN?\\r\\n',
                'data_size': 7,
                'is_error': False,
                'response_time': 45.2,
                'timestamp': datetime.utcnow() - timedelta(minutes=5)
            },
            {
                'connection_id': serial_conn.id,
                'direction': 'received',
                'data_hex': '4B657973696768742054656368...',
                'data_ascii': 'Keysight Technologies,34465A,MY61234567,A.03.02\\r\\n',
                'data_size': 58,
                'is_error': False,
                'response_time': None,
                'timestamp': datetime.utcnow() - timedelta(minutes=4, seconds=58)
            },
            {
                'connection_id': tcp_conn.id,
                'direction': 'sent',
                'data_hex': '4D4541533A564F4C543A44433F0D0A',
                'data_ascii': 'MEAS:VOLT:DC?\\r\\n',
                'data_size': 15,
                'is_error': False,
                'response_time': 123.7,
                'timestamp': datetime.utcnow() - timedelta(minutes=2)
            },
            {
                'connection_id': tcp_conn.id,
                'direction': 'received',
                'data_hex': '2B312E32333435363738394530310D0A',
                'data_ascii': '+1.23456789E01\\r\\n',
                'data_size': 17,
                'is_error': False,
                'response_time': None,
                'timestamp': datetime.utcnow() - timedelta(minutes=1, seconds=58)
            },
            {
                'connection_id': serial_conn.id,
                'direction': 'sent',
                'data_hex': '544553543A53544152540D0A',
                'data_ascii': 'TEST:START\\r\\n',
                'data_size': 12,
                'is_error': True,
                'error_message': 'Device timeout - No response received',
                'response_time': 5000.0,
                'timestamp': datetime.utcnow() - timedelta(minutes=1)
            }
        ]
        
        for log_data in sample_logs:
            log = CommunicationLog(**log_data)
            db.session.add(log)
        
        db.session.commit()
        print("✓ Örnek haberleşme logları oluşturuldu")

def main():
    """Ana migration fonksiyonu"""
    print("=" * 50)
    print("PCBA Test System - Database Migration")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Tabloları oluştur
            print("Veritabanı tabloları kontrol ediliyor...")
            db.create_all()
            print("✓ Veritabanı tabloları hazır")
            
            # Varsayılan verileri oluştur
            create_default_roles()
            create_default_permissions()
            create_communication_permissions()  # Communication izinleri ekle
            assign_permissions_to_roles()
            update_existing_users()
            create_default_admin()
            
            # Communication verileri oluştur
            create_default_connections()
            create_sample_communication_logs()
            
            print("\n" + "=" * 50)
            print("✅ Migration başarıyla tamamlandı!")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ Migration sırasında hata oluştu: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    main()