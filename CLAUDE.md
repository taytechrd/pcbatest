# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **PCBA Test System** built with **Python Flask** backend and **Kaiadmin Lite** Bootstrap 5 frontend. The system provides a complete web interface for managing PCBA (Printed Circuit Board Assembly) testing operations, user management, and test result tracking.

**Key characteristics:**
- Flask-powered backend with SQLite database
- Bootstrap 5 based UI components  
- User authentication and role-based access control
- PCBA test data management and reporting
- RESTful API endpoints for frontend integration
- Responsive design with dark/light theme support

## Project Structure

```
dash/                          # Main dashboard directory
├── assets/                    # All static assets
│   ├── css/                   # Stylesheets (Bootstrap, Kaiadmin theme, plugins)
│   ├── js/                    # JavaScript files (jQuery, Bootstrap, plugins)
│   ├── img/                   # Images, icons, demo content
│   └── fonts/                 # Font files (FontAwesome, Simple Line Icons)
├── components/                # Component demo pages
├── charts/                    # Chart examples
├── forms/                     # Form examples  
├── tables/                    # Table examples
├── maps/                      # Map integration examples
├── index.html                 # Main dashboard page
└── starter-template.html      # Clean template for new pages
```

## Core Architecture

### CSS Architecture
- **bootstrap.min.css** - Bootstrap 5 framework
- **kaiadmin.min.css** - Main theme stylesheet
- **plugins.min.css** - All plugin styles bundled
- **demo.css** - Demo-specific styles (remove in production)

### JavaScript Architecture  
- **jQuery 3.7.1** - Core JavaScript library
- **Bootstrap 5** - UI component interactions
- **kaiadmin.js** - Main theme functionality (sidebar, tooltips, scrollbars)
- **demo.js** - Demo showcase modal and navigation
- **Plugin ecosystem** - Various plugins for charts, forms, maps, etc.

### Layout System
- **Wrapper-based layout** - Main container with sidebar and content area
- **Responsive sidebar** - Collapsible navigation with custom scrollbars
- **Header bar** - Top navigation with search and user menu
- **Content panel** - Main content area with breadcrumbs

## Common Development Tasks

### Starting Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Flask development server
python app.py

# Access the application:
# http://localhost:5000 - Main dashboard
# Login: admin / admin123
```

### Database Operations
```bash
# Database is automatically created on first run with demo data
# SQLite database file: pcba_test.db
# Reset database: rm pcba_test.db && python app.py
# Demo data includes: 1 admin user + 25 test results
```

### Creating New Pages
1. Copy `dash/starter-template.html` as your base
2. Modify the `<title>` and page content
3. Update navigation links in sidebar
4. Add page-specific CSS/JS if needed

### Customizing Theme
- Edit `assets/css/kaiadmin.css` for theme modifications
- Use `data-background-color` attributes for dynamic theming
- Modify `assets/js/kaiadmin.js` for behavior changes

### Adding New Components
1. Reference existing component pages in `components/` directory
2. Include necessary plugin CSS/JS files
3. Follow Bootstrap 5 markup patterns
4. Initialize plugins in document.ready

## Key Files to Understand

### Core Theme Files
- `assets/js/kaiadmin.js` - Main theme JavaScript (sidebar, tooltips, custom scrollbars)
- `assets/css/kaiadmin.css` - Theme-specific styles and customizations
- `index.html` - Complete dashboard example with all components

### Template Structure
- `starter-template.html` - Clean starting point for new pages
- `sidebar-style-2.html` - Alternative sidebar layout example

### Plugin Integration
- Plugin files are in `assets/js/plugin/` and `assets/css/` (bundled in plugins.min.css)
- Charts: Chart.js for main charts, Sparkline for mini charts
- Forms: Select2, Bootstrap DateTimePicker, Summernote editor
- Tables: DataTables for enhanced table functionality
- Maps: Google Maps and jsVectorMap integration

## Development Notes

### Asset Dependencies
- All CSS must be loaded before JavaScript
- jQuery must be loaded before Bootstrap and other plugins
- WebFont loader handles custom font loading
- Plugin order matters - check existing pages for correct sequence

### Responsive Design
- Mobile-first Bootstrap 5 approach
- Sidebar collapses on mobile devices
- All components are responsive by default
- Use Bootstrap utility classes for spacing and layout

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Bootstrap 5 requires IE11+ (though template optimized for modern browsers)
- All plugins included are compatible with supported browsers

### Performance Considerations
- CSS/JS files are minified for production
- Use `demo.css` and `demo.js` for development only
- Consider removing unused plugin files for production builds
- Images are optimized but can be further compressed if needed