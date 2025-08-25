#!/usr/bin/env python3
"""
Detailed formatting check for edit-connection page
"""
import sys
sys.path.append('.')

from playwright.sync_api import sync_playwright
from tests.mcp_playwright_integration import MCPPlaywrightTestRunner
import time

def detailed_formatting_check():
    """Detailed check of edit-connection page formatting issues"""
    
    try:
        print("🔍 Detailed formatting check for edit-connection page...")
        
        with sync_playwright() as p:
            # Launch browser with viewport
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # Create MCP test runner
            runner = MCPPlaywrightTestRunner(page)
            
            # Login first
            print("1. Logging in...")
            login_success = runner.run_pcba_login_test("admin", "admin123")
            print(f"   Login result: {login_success}")
            
            # Navigate to edit-connection page
            print("2. Navigating to edit-connection page...")
            nav_success = runner.mcp_navigate('/edit-connection/1')
            print(f"   Navigation result: {nav_success}")
            
            # Wait for page to fully load
            time.sleep(3)
            
            print("3. Taking initial screenshot...")
            runner.mcp_screenshot('edit_connection_formatting_check.png')
            
            # Check if CSS files are actually loading
            print("4. Checking CSS file loading...")
            
            # Get all stylesheets and their status
            css_info = page.evaluate('''
                () => {
                    const info = {
                        stylesheets: [],
                        errors: []
                    };
                    
                    // Check link elements
                    const links = document.querySelectorAll('link[rel="stylesheet"]');
                    links.forEach((link, index) => {
                        const href = link.href;
                        const disabled = link.disabled;
                        
                        info.stylesheets.push({
                            index: index,
                            href: href,
                            filename: href ? href.split('/').pop() : 'unknown',
                            disabled: disabled,
                            loaded: link.sheet !== null
                        });
                    });
                    
                    return info;
                }
            ''')
            
            print("   CSS Files loaded:")
            for css in css_info['stylesheets']:
                status = "✅ LOADED" if css['loaded'] else "❌ FAILED"
                print(f"     {css['filename']}: {status}")
                if 'dropdown-fix.css' in css['filename']:
                    print(f"       → Dropdown CSS found: {css['href']}")
            
            # Check if specific CSS rules are applied
            print("5. Checking CSS rule application...")
            
            dropdown_styles = page.evaluate('''
                () => {
                    const dropdown = document.querySelector('.topbar-user .dropdown-menu');
                    if (!dropdown) return { error: 'Dropdown menu not found' };
                    
                    const styles = window.getComputedStyle(dropdown);
                    return {
                        position: styles.position,
                        zIndex: styles.zIndex,
                        display: styles.display,
                        right: styles.right,
                        top: styles.top,
                        visibility: styles.visibility
                    };
                }
            ''')
            
            print(f"   Dropdown menu styles: {dropdown_styles}")
            
            # Check navbar overflow
            navbar_styles = page.evaluate('''
                () => {
                    const navbar = document.querySelector('.navbar');
                    if (!navbar) return { error: 'Navbar not found' };
                    
                    const styles = window.getComputedStyle(navbar);
                    return {
                        overflow: styles.overflow,
                        overflowX: styles.overflowX,
                        overflowY: styles.overflowY,
                        position: styles.position,
                        zIndex: styles.zIndex
                    };
                }
            ''')
            
            print(f"   Navbar styles: {navbar_styles}")
            
            # Check form layout
            print("6. Checking form layout...")
            
            form_layout = page.evaluate('''
                () => {
                    const form = document.querySelector('#connectionForm');
                    if (!form) return { error: 'Form not found' };
                    
                    const formRect = form.getBoundingClientRect();
                    const rows = document.querySelectorAll('#connectionForm .row');
                    
                    return {
                        formVisible: formRect.width > 0 && formRect.height > 0,
                        formWidth: formRect.width,
                        formHeight: formRect.height,
                        rowCount: rows.length,
                        formClasses: Array.from(form.classList)
                    };
                }
            ''')
            
            print(f"   Form layout: {form_layout}")
            
            # Check Bootstrap loading
            print("7. Checking Bootstrap framework...")
            
            bootstrap_check = page.evaluate('''
                () => {
                    return {
                        jQuery: typeof $ !== 'undefined',
                        bootstrap: typeof bootstrap !== 'undefined',
                        bootstrapVersion: typeof bootstrap !== 'undefined' ? 'loaded' : 'not loaded',
                        dropdownClass: typeof bootstrap !== 'undefined' && typeof bootstrap.Dropdown !== 'undefined'
                    };
                }
            ''')
            
            print(f"   Bootstrap status: {bootstrap_check}")
            
            # Test dropdown interaction
            print("8. Testing dropdown interaction...")
            
            try:
                # Click dropdown toggle
                dropdown_toggle = page.locator('.topbar-user .dropdown-toggle').first
                dropdown_toggle.click()
                time.sleep(1)
                
                # Check dropdown state after click
                dropdown_state = page.evaluate('''
                    () => {
                        const menu = document.querySelector('.topbar-user .dropdown-menu');
                        if (!menu) return { error: 'Dropdown menu not found' };
                        
                        const rect = menu.getBoundingClientRect();
                        const styles = window.getComputedStyle(menu);
                        
                        return {
                            visible: rect.width > 0 && rect.height > 0,
                            display: styles.display,
                            visibility: styles.visibility,
                            opacity: styles.opacity,
                            transform: styles.transform,
                            classes: Array.from(menu.classList),
                            position: {
                                top: rect.top,
                                right: rect.right,
                                bottom: rect.bottom,
                                left: rect.left
                            }
                        };
                    }
                ''')
                
                print(f"   Dropdown state after click: {dropdown_state}")
                
                # Take screenshot with dropdown open
                runner.mcp_screenshot('edit_connection_dropdown_open.png')
                
            except Exception as e:
                print(f"   Dropdown test failed: {e}")
            
            # Check JavaScript errors
            print("9. Checking JavaScript errors...")
            
            js_errors = page.evaluate('''
                () => {
                    // Capture console errors
                    const errors = window.jsErrors || [];
                    
                    // Check if global dropdown init function exists
                    const hasGlobalDropdown = typeof window.initializeDropdowns === 'function';
                    
                    return {
                        errors: errors,
                        hasGlobalDropdown: hasGlobalDropdown,
                        jQueryLoaded: typeof $ !== 'undefined',
                        documentReady: document.readyState
                    };
                }
            ''')
            
            print(f"   JavaScript status: {js_errors}")
            
            # Check viewport and responsive layout
            print("10. Checking responsive layout...")
            
            layout_check = page.evaluate('''
                () => {
                    const container = document.querySelector('.container');
                    const sidebar = document.querySelector('.sidebar');
                    const mainPanel = document.querySelector('.main-panel');
                    
                    return {
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight
                        },
                        container: container ? {
                            width: container.offsetWidth,
                            classes: Array.from(container.classList)
                        } : null,
                        sidebar: sidebar ? {
                            width: sidebar.offsetWidth,
                            visible: window.getComputedStyle(sidebar).display !== 'none'
                        } : null,
                        mainPanel: mainPanel ? {
                            width: mainPanel.offsetWidth,
                            marginLeft: window.getComputedStyle(mainPanel).marginLeft
                        } : null
                    };
                }
            ''')
            
            print(f"   Layout information: {layout_check}")
            
            # Final summary
            print("\n📊 FORMATTING ISSUES SUMMARY:")
            issues = []
            
            # Check for specific problems
            if not any(css['loaded'] and 'dropdown-fix.css' in css['filename'] for css in css_info['stylesheets']):
                issues.append("❌ Dropdown CSS (dropdown-fix.css) not properly loaded")
            
            if not bootstrap_check.get('bootstrap'):
                issues.append("❌ Bootstrap JavaScript not loaded")
            
            if navbar_styles.get('overflow') not in ['visible', 'initial']:
                issues.append(f"❌ Navbar overflow issue: {navbar_styles.get('overflow')}")
            
            if not form_layout.get('formVisible'):
                issues.append("❌ Form layout not visible")
            
            if dropdown_styles.get('error'):
                issues.append(f"❌ Dropdown menu issue: {dropdown_styles['error']}")
            
            if js_errors.get('errors'):
                issues.append(f"❌ JavaScript errors: {len(js_errors['errors'])} errors")
            
            if issues:
                print("🚨 FOUND ISSUES:")
                for issue in issues:
                    print(f"   {issue}")
            else:
                print("✅ No obvious formatting issues detected")
            
            # Take final screenshot
            runner.mcp_screenshot('edit_connection_final_check.png')
            
            browser.close()
            return len(issues) == 0
        
    except Exception as e:
        print(f"❌ Error during detailed check: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = detailed_formatting_check()
    print(f"\n{'✅ Formatting check passed' if result else '❌ Formatting issues found'}")
    sys.exit(0 if result else 1)