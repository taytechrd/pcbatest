#!/usr/bin/env python3
"""
Create Developer User and Role for PCBA Test System
This script creates a 'Developer' role with full permissions and a 'dev' user
for simulator and virtual port management.
"""

from app import app, db, User, Role, Permission
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_developer_permissions():
    """Create additional permissions specific to development and simulation"""
    print("Creating developer-specific permissions...")
    
    developer_permissions = [
        # Simulator management permissions
        ('manage_simulators', 'Simulator Management', 'Manage Modbus PLC simulators and virtual devices', 'development'),
        ('create_simulators', 'Create Simulators', 'Create and configure new simulators', 'development'),
        ('control_simulators', 'Control Simulators', 'Start, stop and control simulator operations', 'development'),
        ('debug_simulators', 'Debug Simulators', 'Access simulator debugging and diagnostic features', 'development'),
        
        # Virtual port management permissions
        ('manage_virtual_ports', 'Virtual Port Management', 'Manage virtual serial ports and connections', 'development'),
        ('create_virtual_ports', 'Create Virtual Ports', 'Create new virtual port pairs', 'development'),
        ('configure_virtual_ports', 'Configure Virtual Ports', 'Configure virtual port settings and parameters', 'development'),
        
        # Advanced development permissions
        ('manage_test_environment', 'Test Environment Management', 'Manage test environments and configurations', 'development'),
        ('access_debug_logs', 'Debug Log Access', 'Access detailed debug logs and diagnostics', 'development'),
        ('manage_modbus_communication', 'Modbus Communication', 'Manage Modbus RTU/TCP communication settings', 'development'),
        ('system_administration', 'System Administration', 'Full system administration access', 'development'),
        ('database_administration', 'Database Administration', 'Direct database access and management', 'development'),
        
        # Integration and testing permissions
        ('manage_integration_tests', 'Integration Test Management', 'Manage integration test suites', 'development'),
        ('run_diagnostic_tests', 'Diagnostic Tests', 'Run comprehensive diagnostic and validation tests', 'development'),
        ('access_raw_data', 'Raw Data Access', 'Access raw test data and communication logs', 'development'),
        
        # Advanced configuration permissions
        ('manage_hardware_configurations', 'Hardware Configuration', 'Manage hardware simulation configurations', 'development'),
        ('edit_system_configuration', 'System Configuration', 'Edit core system configuration files', 'development'),
        ('manage_communication_protocols', 'Communication Protocols', 'Manage and configure communication protocols', 'development'),
    ]
    
    created_count = 0
    for name, display_name, description, module in developer_permissions:
        permission = Permission.query.filter_by(name=name).first()
        if not permission:
            permission = Permission(
                name=name,
                description=description,
                module=module,
                created_at=datetime.utcnow()
            )
            db.session.add(permission)
            created_count += 1
            print(f"✓ Created permission: {display_name}")
        else:
            print(f"○ Permission already exists: {display_name}")
    
    if created_count > 0:
        db.session.commit()
        print(f"✅ Created {created_count} new developer permissions")
    
    return created_count

def create_developer_role():
    """Create Developer role with comprehensive permissions"""
    print("\nCreating Developer role...")
    
    # Check if Developer role already exists
    developer_role = Role.query.filter_by(name='Developer').first()
    if developer_role:
        print("○ Developer role already exists")
        return developer_role
    
    # Create Developer role
    developer_role = Role(
        name='Developer',
        description='Developer - Full system access for simulator and virtual port management, debugging, and system administration',
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(developer_role)
    db.session.commit()  # Commit to get role ID
    
    print("✓ Created Developer role")
    
    # Get ALL available permissions
    all_permissions = Permission.query.all()
    
    # Assign ALL permissions to Developer role
    developer_role.permissions.clear()  # Clear any existing permissions
    for permission in all_permissions:
        developer_role.permissions.append(permission)
    
    db.session.commit()
    
    print(f"✓ Assigned {len(all_permissions)} permissions to Developer role")
    print("✅ Developer role has complete system access")
    
    return developer_role

def create_dev_user():
    """Create dev user with Developer role"""
    print("\nCreating dev user...")
    
    # Check if dev user already exists
    dev_user = User.query.filter_by(username='dev').first()
    if dev_user:
        print("○ User 'dev' already exists")
        # Update existing user
        developer_role = Role.query.filter_by(name='Developer').first()
        if developer_role:
            dev_user.role_id = developer_role.id
            dev_user.role = 'admin'  # Keep legacy role as admin for compatibility
            dev_user.is_active = True
            # Update password if needed
            dev_user.set_password('dev12345')
            db.session.commit()
            print("✓ Updated existing dev user with Developer role")
        return dev_user
    
    # Get Developer role
    developer_role = Role.query.filter_by(name='Developer').first()
    if not developer_role:
        print("❌ Developer role not found")
        return None
    
    # Create dev user
    dev_user = User(
        username='dev',
        email='dev@pcbatest.local',
        role='admin',  # Keep legacy role as admin for compatibility
        role_id=developer_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    dev_user.set_password('dev12345')
    
    db.session.add(dev_user)
    db.session.commit()
    
    print("✓ Created dev user with credentials:")
    print("   Username: dev")
    print("   Password: dev12345")
    print("   Email: dev@pcbatest.local")
    print("   Role: Developer (full system access)")
    
    return dev_user

def verify_user_permissions():
    """Verify that the dev user has all required permissions"""
    print("\nVerifying dev user permissions...")
    
    dev_user = User.query.filter_by(username='dev').first()
    if not dev_user:
        print("❌ Dev user not found")
        return False
    
    # Check role assignment
    if not dev_user.assigned_role:
        print("❌ Dev user has no assigned role")
        return False
    
    if dev_user.assigned_role.name != 'Developer':
        print(f"⚠️ Dev user has role '{dev_user.assigned_role.name}' instead of 'Developer'")
    
    # Get user permissions
    user_permissions = dev_user.get_permissions()
    all_permissions = [p.name for p in Permission.query.all()]
    
    print(f"✓ Dev user has {len(user_permissions)} permissions")
    print(f"✓ Total system permissions: {len(all_permissions)}")
    
    # Check for key simulator and development permissions
    key_permissions = [
        'manage_simulators', 'manage_virtual_ports', 'manage_connections',
        'system_administration', 'manage_system_settings', 'manage_users',
        'access_debug_logs', 'manage_test_environment'
    ]
    
    missing_permissions = []
    for perm in key_permissions:
        if perm not in user_permissions:
            missing_permissions.append(perm)
    
    if missing_permissions:
        print(f"⚠️ Missing key permissions: {missing_permissions}")
    else:
        print("✅ All key development permissions are assigned")
    
    return len(missing_permissions) == 0

def display_user_info():
    """Display information about the created user and role"""
    print("\n" + "="*60)
    print("🎉 DEVELOPER USER AND ROLE SETUP COMPLETE")
    print("="*60)
    
    dev_user = User.query.filter_by(username='dev').first()
    developer_role = Role.query.filter_by(name='Developer').first()
    
    if dev_user and developer_role:
        print("\n👤 User Information:")
        print(f"   Username: {dev_user.username}")
        print(f"   Email: {dev_user.email}")
        print(f"   Password: dev12345")
        print(f"   Role: {developer_role.name}")
        print(f"   Status: {'Active' if dev_user.is_active else 'Inactive'}")
        print(f"   Created: {dev_user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n🔑 Role Information:")
        print(f"   Role Name: {developer_role.name}")
        print(f"   Description: {developer_role.description}")
        print(f"   Total Permissions: {len(developer_role.permissions)}")
        print(f"   Status: {'Active' if developer_role.is_active else 'Inactive'}")
        
        print(f"\n🛠️ Capabilities:")
        print("   ✅ Full system administration access")
        print("   ✅ Modbus PLC simulator management")
        print("   ✅ Virtual serial port management")
        print("   ✅ Hardware configuration management")
        print("   ✅ Test environment management")
        print("   ✅ Debug and diagnostic access")
        print("   ✅ Communication protocol management")
        print("   ✅ Database administration")
        print("   ✅ Integration test management")
        print("   ✅ User and role management")
        
        print(f"\n🔗 Login Information:")
        print("   URL: http://localhost:9002/login")
        print("   Username: dev")
        print("   Password: dev12345")
        
        print(f"\n📋 Next Steps:")
        print("   1. Login to the PCBA Test System with dev credentials")
        print("   2. Access simulator management features")
        print("   3. Configure virtual serial ports for testing")
        print("   4. Run integration tests with full permissions")
        print("   5. Manage Modbus RTU simulation environment")
        
    else:
        print("❌ Failed to create user or role")

def main():
    """Main function to create developer user and role"""
    print("🚀 PCBA Test System - Developer User Setup")
    print("="*50)
    
    try:
        with app.app_context():
            # Create developer-specific permissions
            create_developer_permissions()
            
            # Create Developer role with full permissions
            developer_role = create_developer_role()
            
            # Create dev user
            dev_user = create_dev_user()
            
            # Verify permissions
            verify_user_permissions()
            
            # Display final information
            display_user_info()
            
            return True
            
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)