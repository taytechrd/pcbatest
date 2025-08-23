#!/usr/bin/env python3
"""
Automated Test Execution System Migration Script
Bu script otomatik test çalıştırma sistemi için gerekli veritabanı tablolarını oluşturur.
"""

from app import app, db, TestExecution, ScheduledTest, TestConfiguration
from datetime import datetime, time
import json

def create_tables():
    """Yeni tabloları oluştur"""
    print("Creating automated test execution tables...")
    
    with app.app_context():
        # Tabloları oluştur
        db.create_all()
        print("✓ Tables created successfully")

def insert_default_configurations():
    """Varsayılan test konfigürasyonlarını ekle"""
    print("Inserting default test configurations...")
    
    with app.app_context():
        default_configs = [
            # Timeout configurations
            {
                'key': 'test_timeout_seconds',
                'value': '300',
                'description': 'Maximum test execution timeout in seconds',
                'data_type': 'INTEGER',
                'category': 'TIMEOUT',
                'is_system': True
            },
            {
                'key': 'connection_timeout_seconds',
                'value': '30',
                'description': 'Connection timeout for hardware communication',
                'data_type': 'INTEGER',
                'category': 'TIMEOUT',
                'is_system': True
            },
            
            # Retry configurations
            {
                'key': 'max_retry_attempts',
                'value': '3',
                'description': 'Maximum number of retry attempts for failed tests',
                'data_type': 'INTEGER',
                'category': 'RETRY',
                'is_system': True
            },
            {
                'key': 'retry_delay_seconds',
                'value': '5',
                'description': 'Delay between retry attempts in seconds',
                'data_type': 'INTEGER',
                'category': 'RETRY',
                'is_system': True
            },
            
            # Notification configurations
            {
                'key': 'enable_email_notifications',
                'value': 'false',
                'description': 'Enable email notifications for test results',
                'data_type': 'BOOLEAN',
                'category': 'NOTIFICATION',
                'is_system': False
            },
            {
                'key': 'smtp_server',
                'value': 'localhost',
                'description': 'SMTP server for email notifications',
                'data_type': 'STRING',
                'category': 'NOTIFICATION',
                'is_system': False
            },
            {
                'key': 'smtp_port',
                'value': '587',
                'description': 'SMTP server port',
                'data_type': 'INTEGER',
                'category': 'NOTIFICATION',
                'is_system': False
            },
            {
                'key': 'notification_from_email',
                'value': 'noreply@taytech.com',
                'description': 'From email address for notifications',
                'data_type': 'STRING',
                'category': 'NOTIFICATION',
                'is_system': False
            },
            
            # Logging configurations
            {
                'key': 'log_level',
                'value': 'INFO',
                'description': 'Logging level (DEBUG, INFO, WARNING, ERROR)',
                'data_type': 'STRING',
                'category': 'LOGGING',
                'is_system': True
            },
            {
                'key': 'enable_detailed_logging',
                'value': 'true',
                'description': 'Enable detailed test execution logging',
                'data_type': 'BOOLEAN',
                'category': 'LOGGING',
                'is_system': False
            },
            
            # General configurations
            {
                'key': 'max_concurrent_tests',
                'value': '3',
                'description': 'Maximum number of concurrent test executions',
                'data_type': 'INTEGER',
                'category': 'GENERAL',
                'is_system': True
            },
            {
                'key': 'auto_cleanup_days',
                'value': '30',
                'description': 'Automatically cleanup test executions older than X days',
                'data_type': 'INTEGER',
                'category': 'GENERAL',
                'is_system': False
            },
            {
                'key': 'enable_real_time_monitoring',
                'value': 'true',
                'description': 'Enable real-time test monitoring via WebSocket',
                'data_type': 'BOOLEAN',
                'category': 'GENERAL',
                'is_system': False
            }
        ]
        
        for config_data in default_configs:
            # Check if config already exists
            existing_config = TestConfiguration.query.filter_by(key=config_data['key']).first()
            if not existing_config:
                config = TestConfiguration(**config_data)
                db.session.add(config)
                print(f"✓ Added configuration: {config_data['key']}")
            else:
                print(f"- Configuration already exists: {config_data['key']}")
        
        db.session.commit()
        print("✓ Default configurations inserted successfully")

def create_sample_scheduled_test():
    """Örnek zamanlanmış test oluştur"""
    print("Creating sample scheduled test...")
    
    with app.app_context():
        from app import TestScenario, PCBAModel, User
        
        # İlk test senaryosu ve PCBA modelini al
        test_scenario = TestScenario.query.first()
        pcba_model = PCBAModel.query.first()
        admin_user = User.query.filter_by(role='admin').first()
        
        if test_scenario and pcba_model and admin_user:
            # Örnek zamanlanmış test oluştur
            existing_scheduled = ScheduledTest.query.filter_by(name='Daily Quality Check').first()
            if not existing_scheduled:
                scheduled_test = ScheduledTest(
                    name='Daily Quality Check',
                    description='Günlük kalite kontrol testi - otomatik çalışır',
                    test_scenario_id=test_scenario.id,
                    pcba_model_id=pcba_model.id,
                    schedule_type='DAILY',
                    schedule_time=time(9, 0),  # 09:00
                    is_active=False,  # Başlangıçta pasif
                    created_by=admin_user.id,
                    notification_emails='admin@taytech.com',
                    serial_number_prefix='AUTO'
                )
                db.session.add(scheduled_test)
                db.session.commit()
                print("✓ Sample scheduled test created")
            else:
                print("- Sample scheduled test already exists")
        else:
            print("- Cannot create sample scheduled test: missing test scenario, PCBA model, or admin user")

def update_permissions():
    """Yeni yetkileri ekle"""
    print("Adding new permissions for automated test execution...")
    
    with app.app_context():
        from app import Permission, Role
        
        new_permissions = [
            # Test execution permissions
            {'name': 'start_manual_tests', 'description': 'Manuel test başlatma yetkisi', 'module': 'test_execution'},
            {'name': 'stop_tests', 'description': 'Çalışan testleri durdurma yetkisi', 'module': 'test_execution'},
            {'name': 'view_test_executions', 'description': 'Test çalıştırma geçmişini görüntüleme yetkisi', 'module': 'test_execution'},
            {'name': 'monitor_real_time_tests', 'description': 'Gerçek zamanlı test izleme yetkisi', 'module': 'test_execution'},
            
            # Scheduled test permissions
            {'name': 'view_scheduled_tests', 'description': 'Zamanlanmış testleri görüntüleme yetkisi', 'module': 'scheduled_tests'},
            {'name': 'manage_scheduled_tests', 'description': 'Zamanlanmış testleri yönetme yetkisi', 'module': 'scheduled_tests'},
            
            # Configuration permissions
            {'name': 'view_test_configurations', 'description': 'Test konfigürasyonlarını görüntüleme yetkisi', 'module': 'test_configuration'},
            {'name': 'manage_test_configurations', 'description': 'Test konfigürasyonlarını yönetme yetkisi', 'module': 'test_configuration'},
        ]
        
        for perm_data in new_permissions:
            existing_perm = Permission.query.filter_by(name=perm_data['name']).first()
            if not existing_perm:
                permission = Permission(**perm_data)
                db.session.add(permission)
                print(f"✓ Added permission: {perm_data['name']}")
            else:
                print(f"- Permission already exists: {perm_data['name']}")
        
        db.session.commit()
        
        # Admin rolüne tüm yetkileri ekle
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            for perm_data in new_permissions:
                permission = Permission.query.filter_by(name=perm_data['name']).first()
                if permission and permission not in admin_role.permissions:
                    admin_role.permissions.append(permission)
                    print(f"✓ Added permission '{perm_data['name']}' to admin role")
            
            db.session.commit()
        
        # Technician rolüne uygun yetkileri ekle
        technician_role = Role.query.filter_by(name='technician').first()
        if technician_role:
            technician_permissions = [
                'start_manual_tests', 'view_test_executions', 'monitor_real_time_tests',
                'view_scheduled_tests', 'view_test_configurations'
            ]
            
            for perm_name in technician_permissions:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission and permission not in technician_role.permissions:
                    technician_role.permissions.append(permission)
                    print(f"✓ Added permission '{perm_name}' to technician role")
            
            db.session.commit()
        
        print("✓ Permissions updated successfully")

def main():
    """Ana migration fonksiyonu"""
    print("=" * 60)
    print("AUTOMATED TEST EXECUTION SYSTEM MIGRATION")
    print("=" * 60)
    
    try:
        # 1. Tabloları oluştur
        create_tables()
        print()
        
        # 2. Varsayılan konfigürasyonları ekle
        insert_default_configurations()
        print()
        
        # 3. Örnek zamanlanmış test oluştur
        create_sample_scheduled_test()
        print()
        
        # 4. Yetkileri güncelle
        update_permissions()
        print()
        
        print("=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart the application")
        print("2. Check the new pages:")
        print("   - /test-execution (Manual test execution)")
        print("   - /test-monitoring (Real-time monitoring)")
        print("   - /scheduled-tests (Scheduled tests management)")
        print("   - /test-configuration (System configuration)")
        print("3. Test the new functionality")
        print()
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    main()