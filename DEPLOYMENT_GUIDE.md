# Simulation Management System - Deployment Guide

## 🚀 **Quick Start Guide**

### **Prerequisites**
- Python 3.11+
- Flask 2.3.3+
- SQLAlchemy 3.0.5+
- All dependencies from `requirements.txt`

### **Installation Steps**

1. **Update Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Migration**
   ```bash
   # The new tables will be created automatically
   python app.py
   ```

3. **Verify Installation**
   ```bash
   # Run the comprehensive test suite
   python test_simulator_management.py
   ```

### **Default User Setup**

The system includes a pre-configured Developer user:
- **Username**: `dev`
- **Password**: `dev12345`  
- **Permissions**: Full simulation management access

### **Access URLs**

Once the server is running on port 9002:
- Main Dashboard: http://127.0.0.1:9002/simulator-management
- Add Simulator: http://127.0.0.1:9002/add-simulator
- Virtual Ports: http://127.0.0.1:9002/add-virtual-port

## 🔐 **Security Configuration**

### **Role-Based Access**
- Only Developer role users can access simulation features
- Permissions are automatically assigned to Developer role
- Non-developer users will not see the simulation menu

### **Permission System**
The following permissions control access:
- `manage_simulators` - Main interface access
- `create_simulators` - Create new simulators
- `control_simulators` - Start/stop operations
- `debug_simulators` - Status and logging access
- `manage_virtual_ports` - Virtual port management

## 🗄️ **Database Schema**

### **New Tables Created**
1. **simulators** - Core simulator configuration
2. **virtual_ports** - Virtual port pair management  
3. **simulator_logs** - Event and operation logging

### **Automatic Migration**
- Tables are created automatically on first run
- No manual database setup required
- Existing data remains unchanged

## 🧪 **Testing & Verification**

### **Run Test Suite**
```bash
python test_simulator_management.py
```

**Expected Output:**
```
✅ Dev user login: SUCCESS
✅ Simulator management access: SUCCESS
✅ Add simulator access: SUCCESS  
✅ Add virtual port access: SUCCESS
✅ Developer navigation menu: SUCCESS
✅ Role-based access control: SUCCESS
🎉 Simulation Management System Test PASSED!
```

### **Manual Verification**
1. Login with dev user credentials
2. Check for "Developer Tools" in navigation menu
3. Access simulator management pages
4. Create a test simulator
5. Verify permissions are working

## 🔧 **Configuration Options**

### **Simulator Types Supported**
- **Serial (RTU)**: COM ports, baud rates, Modbus addressing
- **TCP/IP**: Network configuration, IP/port settings
- **USB**: Vendor/Product IDs, interface selection

### **Customization**
- Modify permissions in the User Management interface
- Add new Modbus function codes as needed
- Extend virtual port functionality

## 🐛 **Troubleshooting**

### **Common Issues**

**1. Navigation Menu Not Showing**
- Verify user has Developer role
- Check permissions are properly assigned
- Clear browser cache (Ctrl+F5)

**2. Database Errors**
- Ensure proper write permissions
- Check SQLite database file location
- Verify all dependencies are installed

**3. Permission Denied**
- Confirm user role assignment
- Check permission configuration
- Verify route decorators are working

### **Debug Commands**
```bash
# Check user permissions
python -c "from app import *; app.app_context().push(); u=User.query.filter_by(username='dev').first(); print(f'Permissions: {u.get_permissions()}')"

# Verify database tables
python -c "from app import *; app.app_context().push(); print([table.name for table in db.Model.metadata.tables.values()])"
```

## 📊 **Monitoring**

### **System Health Checks**
- Monitor simulator process status
- Check virtual port availability  
- Review simulator logs for errors
- Verify database connectivity

### **Performance Metrics**
- Simulator start/stop response times
- Database query performance
- Memory usage during simulation
- Connection stability metrics

## 🔄 **Backup & Recovery**

### **Database Backup**
```bash
# Backup SQLite database
cp pcba_test_new.db pcba_test_backup_$(date +%Y%m%d).db
```

### **Configuration Export**
- Simulator configurations are stored in database
- Export via simulator management interface
- Virtual port settings can be recreated as needed

---

**For additional support**: Check the comprehensive test suite and inline code documentation
**Version**: v2.1.0  
**Last Updated**: August 25, 2025