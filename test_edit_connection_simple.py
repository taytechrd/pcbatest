#!/usr/bin/env python3
"""
Simple test script to check edit-connection page formatting with login
"""
import sys
sys.path.append('.')

from playwright.sync_api import sync_playwright
from tests.mcp_playwright_integration import MCPPlaywrightTestRunner
import time

def test_edit_connection_with_login():
    """Test the edit-connection page formatting after login"""
    
    try:
        print("🔍 Testing edit-connection page formatting with login...")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Create MCP test runner
            runner = MCPPlaywrightTestRunner(page)
            
            print("1. Performing login test...")
            login_success = runner.run_pcba_login_test("admin", "admin123")
            print(f"   Login result: {login_success}")
            
            if not login_success:
                print("❌ Login failed, trying to navigate to edit-connection anyway...")
            
            # Navigate to edit-connection page
            print("2. Navigating to edit-connection page...")
            edit_nav_result = runner.mcp_navigate('/edit-connection/1')
            print(f"   Navigation result: {edit_nav_result}")
            
            # Wait a moment for page to load
            time.sleep(2)
            
            # Take screenshot
            print("3. Taking screenshot...")
            screenshot_path = runner.mcp_screenshot('edit_connection_after_login.png')
            print(f"   Screenshot saved: {screenshot_path}")
            
            # Check current URL
            current_url = page.url
            page_title = page.title()
            print(f"   Current URL: {current_url}")
            print(f"   Page title: {page_title}")
            
            # Simple checks without complex evaluation
            print("4. Checking page elements...")
            
            # Check if we're on the right page
            is_edit_page = "edit-connection" in current_url and "login" not in current_url
            print(f"   Is edit-connection page: {is_edit_page}")
            
            if is_edit_page:
                # Check for form elements
                form_exists = page.locator('#connectionForm').count() > 0
                name_input_exists = page.locator('#connection_name').count() > 0
                submit_button_exists = page.locator('button[type="submit"]').count() > 0
                
                print(f"   Form exists: {form_exists}")
                print(f"   Name input exists: {name_input_exists}")
                print(f"   Submit button exists: {submit_button_exists}")
                
                # Check profile dropdown
                profile_dropdown_exists = page.locator('.topbar-user .dropdown-toggle').count() > 0
                profile_image_exists = page.locator('.topbar-user img').count() > 0
                
                print(f"   Profile dropdown exists: {profile_dropdown_exists}")
                print(f"   Profile image exists: {profile_image_exists}")
                
                if profile_image_exists:
                    # Get image src
                    img_src = page.locator('.topbar-user img').get_attribute('src')
                    print(f"   Profile image src: {img_src}")
                    has_user_png = img_src and 'user.png' in img_src
                    print(f"   Uses user.png: {has_user_png}")
                
                # Check CSS files by looking at link tags
                css_links = page.locator('link[rel="stylesheet"]').all()
                css_files = []
                for link in css_links:
                    href = link.get_attribute('href')
                    if href:
                        css_files.append(href)
                
                print(f"   CSS files loaded: {len(css_files)}")
                
                has_dropdown_css = any('dropdown-fix.css' in css for css in css_files)
                has_bootstrap_css = any('bootstrap' in css for css in css_files)
                has_kaiadmin_css = any('kaiadmin' in css for css in css_files)
                
                print(f"   Has dropdown-fix.css: {has_dropdown_css}")
                print(f"   Has bootstrap CSS: {has_bootstrap_css}")
                print(f"   Has kaiadmin CSS: {has_kaiadmin_css}")
                
                # Test dropdown click
                if profile_dropdown_exists:
                    print("5. Testing dropdown functionality...")
                    try:
                        page.locator('.topbar-user .dropdown-toggle').click()
                        time.sleep(1)  # Wait for dropdown to appear
                        
                        dropdown_menu_visible = page.locator('.topbar-user .dropdown-menu').is_visible()
                        print(f"   Dropdown opens: {dropdown_menu_visible}")
                        
                        # Take screenshot with dropdown open
                        runner.mcp_screenshot('edit_connection_dropdown_open.png')
                        
                    except Exception as e:
                        print(f"   Dropdown test failed: {e}")
                
                # Summary
                print("\n📊 Summary:")
                issues = []
                
                if not form_exists:
                    issues.append("❌ Connection form not found")
                else:
                    print("✅ Connection form found")
                
                if not has_dropdown_css:
                    issues.append("❌ Dropdown CSS not loaded")
                else:
                    print("✅ Dropdown CSS loaded")
                
                if not profile_image_exists:
                    issues.append("❌ Profile image not found")
                elif not has_user_png:
                    issues.append("❌ Profile image not using user.png")
                else:
                    print("✅ Profile image using user.png")
                
                if not has_bootstrap_css:
                    issues.append("❌ Bootstrap CSS not loaded")
                else:
                    print("✅ Bootstrap CSS loaded")
                
                if issues:
                    print("\n🚨 Issues found:")
                    for issue in issues:
                        print(f"   {issue}")
                    result = False
                else:
                    print("\n🎉 No formatting issues found!")
                    result = True
                    
            else:
                print("❌ Could not access edit-connection page (still on login or error page)")
                result = False
            
            browser.close()
            return result
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_edit_connection_with_login()
    print(f"\n{'✅ Test passed' if result else '❌ Test failed'}")
    sys.exit(0 if result else 1)