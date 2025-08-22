#!/usr/bin/env python3
"""
PCBA Test System - Database Migration Script
Bu script veritabanı şemasını güncellemek için kullanılır.
"""

import os
import sys
from datetime import datetime
from app import app, db, User, Role, Permission

def create_default_roles():
    """Varsayılan rolleri oluştur"""
    print("Varsayılan roller oluşturuluyor...")
    
    # Admin rolü
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            display_name='Yönetici',
            description='Sistem yöneticisi - Tüm yetkilere sahip'
        )
        db.session.add(admin_role)
        print("✓ Admin rolü oluşturuldu")
    
    # Operator rolü
    operator_role = Role.query.filter_by(name='operator').first()
    if not operator_role:
        operator_role = Role(
            name='operator',
            display_name='Operatör',
            description='Test operatörü - Test çalıştırma yetkisi'
        )
        db.session.add(operator_role)
        print("✓ Operator rolü oluşturuldu")
    
    # Viewer rolü
    viewer_role = Role.query.filter_by(name='viewer').first()
    if not viewer_role:
        viewer_role = Role(
            name='viewer',
            display_name='Görüntüleyici',
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
    ]
    
    for perm_name, display_name, description in permissions:
        permission = Permission.query.filter_by(name=perm_name).first()
        if not permission:
            permission = Permission(
                name=perm_name,
                display_name=display_name,
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
            assign_permissions_to_roles()
            update_existing_users()
            create_default_admin()
            
            print("\n" + "=" * 50)
            print("✅ Migration başarıyla tamamlandı!")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ Migration sırasında hata oluştu: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    main()