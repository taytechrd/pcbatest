#!/usr/bin/env python3
"""
Test script to check edit-connection page formatting using Playwright
"""
import sys
import asyncio
import os
sys.path.append('.')

from playwright.sync_api import sync_playwright
from tests.mcp_playwright_integration import MCPPlaywrightTestRunner
import time

def test_edit_connection_formatting():
    """Test the edit-connection page formatting and functionality"""
    
    try:
        print("🔍 Testing edit-connection page formatting...")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)  # Set to True for headless
            context = browser.new_context()
            page = context.new_page()
            
            # Create MCP test runner
            runner = MCPPlaywrightTestRunner(page)
            
            # Setup test session
            session_id = runner.setup_test_session("edit_connection_formatting")
            print(f"📋 Test session: {session_id}")
            
            # Navigate to the connections page first
            print("1. Navigating to connections page...")
            nav_result = runner.mcp_navigate('/connections')
            print(f"   Navigation result: {nav_result}")
            
            # Take screenshot of connections page
            print("2. Taking screenshot of connections page...")
            screenshot_path = runner.mcp_screenshot('connections_page.png')
            print(f"   Screenshot saved: {screenshot_path}")
            
            # Check if there are any connections available and get edit link
            print("3. Checking for available connections...")
            edit_link_script = '''
                const editLinks = document.querySelectorAll('a[href*="edit-connection"]');
                if (editLinks.length > 0) {
                    return {
                        found: true,
                        href: editLinks[0].href,
                        count: editLinks.length
                    };
                } else {
                    return { found: false, count: 0 };
                }
            '''
            
            connections_check = runner.mcp_evaluate(edit_link_script)
            print(f"   Available connections: {connections_check}")
            
            # Navigate to edit-connection page
            if connections_check and connections_check.get('found'):
                edit_url = connections_check['href']
                print(f"4. Navigating to edit-connection page: {edit_url}")
                edit_nav_result = runner.mcp_navigate(edit_url)
            else:
                # Try with a default connection ID
                print("4. No connections found, trying with default ID...")
                edit_nav_result = runner.mcp_navigate('/edit-connection/1')
            
            print(f"   Navigation result: {edit_nav_result}")
            
            # Take screenshot of edit-connection page
            print("5. Taking screenshot of edit-connection page...")
            edit_screenshot = runner.mcp_screenshot('edit_connection_page.png')
            print(f"   Screenshot saved: {edit_screenshot}")
            
            # Check page content and formatting
            print("6. Checking page content and formatting...")
            page_check_script = '''
                return {
                    title: document.title,
                    url: window.location.href,
                    hasForm: !!document.querySelector('#connectionForm'),
                    hasDropdownCSS: !!Array.from(document.styleSheets).find(sheet => 
                        sheet.href && sheet.href.includes('dropdown-fix.css')),
                    hasDropdownJS: typeof window.initializeDropdowns === 'function',
                    profileImageSrc: document.querySelector('.topbar-user img')?.src || 'No image found',
                    profileImageExists: !!document.querySelector('.topbar-user img'),
                    hasConnectionName: !!document.querySelector('#connection_name'),
                    hasProtocolRadios: document.querySelectorAll('input[name="protocol_type"]').length,
                    formErrors: document.querySelectorAll('.alert').length,
                    hasSubmitButton: !!document.querySelector('button[type="submit"]'),
                    cssFiles: Array.from(document.styleSheets).map(sheet => ({
                        href: sheet.href ? sheet.href.split('/').pop() : 'inline',
                        disabled: sheet.disabled
                    })).filter(sheet => sheet.href !== 'inline'),
                    javascriptErrors: window.jsErrors || [],
                    dropdownElements: {
                        profileDropdown: !!document.querySelector('.topbar-user .dropdown-toggle'),
                        dropdownMenu: !!document.querySelector('.topbar-user .dropdown-menu'),
                        dropdownItems: document.querySelectorAll('.topbar-user .dropdown-menu .dropdown-item').length
                    }
                };
            '''
            
            page_content = runner.mcp_evaluate(page_check_script)
            print(f"   Page content check:")
            for key, value in page_content.items():
                print(f"     {key}: {value}")
            
            # Test form interactions
            print("7. Testing form interactions...")
            if page_content.get('hasConnectionName'):
                form_test_result = runner.mcp_fill('#connection_name', 'Test Connection Name')
                print(f"   Form fill test: {form_test_result}")
            
            # Check dropdown functionality
            print("8. Testing dropdown functionality...")
            dropdown_test_script = '''
                const dropdownToggle = document.querySelector('.topbar-user .dropdown-toggle');
                if (dropdownToggle) {
                    // Test click event
                    dropdownToggle.click();
                    
                    // Wait a moment for dropdown to appear
                    setTimeout(() => {
                        const dropdownMenu = document.querySelector('.topbar-user .dropdown-menu');
                        const isVisible = dropdownMenu && (dropdownMenu.style.display !== 'none' && 
                                         !dropdownMenu.classList.contains('d-none'));
                        
                        return {
                            clicked: true,
                            dropdownVisible: isVisible,
                            dropdownClasses: dropdownMenu ? Array.from(dropdownMenu.classList) : []
                        };
                    }, 500);
                } else {
                    return { error: 'Dropdown toggle not found' };
                }
            '''
            
            dropdown_result = runner.mcp_evaluate(dropdown_test_script)
            print(f"   Dropdown test: {dropdown_result}")
            
            # Final screenshot after tests
            print("9. Taking final screenshot...")
            final_screenshot = runner.mcp_screenshot('edit_connection_final.png')
            print(f"   Final screenshot saved: {final_screenshot}")
            
            # Summary
            print("\n📊 Test Summary:")
            issues_found = []
            
            if not page_content.get('hasDropdownCSS'):
                issues_found.append("❌ Dropdown CSS not loaded")
            else:
                print("✅ Dropdown CSS loaded")
                
            if not page_content.get('hasDropdownJS'):
                issues_found.append("❌ Dropdown JS not loaded")
            else:
                print("✅ Dropdown JS loaded")
                
            if 'user.png' not in page_content.get('profileImageSrc', ''):
                issues_found.append(f"❌ Profile image issue: {page_content.get('profileImageSrc')}")
            else:
                print("✅ Profile image correctly using user.png")
                
            if not page_content.get('hasForm'):
                issues_found.append("❌ Connection form not found")
            else:
                print("✅ Connection form found")
                
            if page_content.get('formErrors', 0) > 0:
                issues_found.append(f"❌ Form errors detected: {page_content.get('formErrors')}")
            else:
                print("✅ No form errors detected")
            
            if issues_found:
                print("\n🚨 Issues Found:")
                for issue in issues_found:
                    print(f"   {issue}")
            else:
                print("\n🎉 No issues found! Page formatting looks good.")
            
            browser.close()
            print("\n✅ Edit-connection page formatting test completed!")
            return len(issues_found) == 0
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_edit_connection_formatting()
    sys.exit(0 if result else 1)