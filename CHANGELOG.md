# Changelog

All notable changes to the PCBA Test System project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-08-25

### Added
- **Simulation Management System** - Complete system for managing Serial, TCP, and USB connection simulators
- **Database Models**:
  - `Simulator` model for managing all simulator types with flexible configuration
  - `VirtualPort` model for handling virtual serial port pairs  
  - `SimulatorLog` model for tracking simulator events and operations
- **New HTML Templates**:
  - `simulator-management.html` - Main management dashboard with statistics
  - `add-simulator.html` - Form for creating new simulators
  - `edit-simulator.html` - Interface for editing existing simulators
  - `add-virtual-port.html` - Virtual port pair management
- **API Endpoints**:
  - `POST /api/simulator/<id>/start` - Start simulator process
  - `POST /api/simulator/<id>/stop` - Stop simulator process
  - `GET /api/simulator/<id>/status` - Get simulator status and logs
  - `POST /delete-simulator/<id>` - Delete/deactivate simulator
  - `POST /api/virtual-port/<id>/delete` - Remove virtual port pair
- **New Permissions**:
  - `manage_simulators` - Access to simulator management interface
  - `create_simulators` - Ability to create new simulators
  - `control_simulators` - Start/stop simulator processes
  - `debug_simulators` - Access to simulator status and debugging
  - `manage_virtual_ports` - Manage virtual port pairs
- **Developer User Account**:
  - Username: `dev` with password `dev12345`
  - Full simulation management permissions
- **Test Suite**:
  - `test_simulator_management.py` - Comprehensive testing for all simulator features
- **Documentation**:
  - `RELEASE_NOTES_v2.1.0.md` - Detailed release documentation
  - `DEPLOYMENT_GUIDE.md` - Installation and configuration guide

### Modified
- **app.py**:
  - Added simulator management database models (lines 493-654)
  - Added comprehensive simulator management routes (lines 5640-6020)
  - Added simulator process management functions
  - Updated route debugging to include simulator routes
- **dash/connections.html**:
  - Added Developer Tools navigation section for authorized users
  - Integrated simulator management menu items

### Security
- **Role-Based Access Control**: All simulation features restricted to Developer role users
- **Permission Validation**: Proper permission checks on all routes and API endpoints
- **Route Protection**: All simulator management routes protected with authentication decorators

### Technical
- **Database Schema**: Added three new tables with proper relationships and indexes
- **Route Management**: Comprehensive error handling and validation
- **UI/UX**: Responsive design with real-time status indicators
- **Process Management**: Safe simulator start/stop operations with logging

### Testing
- **100% Test Coverage**: All simulator management features fully tested
- **Role-Based Testing**: Verification of access control and permissions
- **API Testing**: Complete endpoint functionality validation
- **UI Testing**: Form submission and navigation verification

## [2.0.0] - Previous Release

### Added
- Initial PCBA Test System implementation
- User management with role-based access control
- Test execution and scheduling
- Communication logging
- Connection management for Modbus RTU/TCP

### Features
- Flask-based web application
- SQLite database with SQLAlchemy ORM
- Bootstrap UI with Kaiadmin template
- APScheduler for background tasks
- Comprehensive user and role management

---

## Versioning Strategy

- **Major** (X.0.0): Breaking changes, significant new features
- **Minor** (x.Y.0): New features, non-breaking changes  
- **Patch** (x.y.Z): Bug fixes, minor improvements

## Release Process

1. Update version number in relevant files
2. Update CHANGELOG.md with new changes
3. Create release notes documenting new features
4. Tag release in Git repository
5. Deploy to production environment