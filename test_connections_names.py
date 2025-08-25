#!/usr/bin/env python3
"""
Test script to verify connection names display correctly in connections page
"""
import sys
sys.path.append('.')

from playwright.sync_api import sync_playwright
from tests.mcp_playwright_integration import MCPPlaywrightTestRunner
import time

def test_connections_page_names():
    """Test that connection names display correctly in the connections page"""
    
    try:
        print("🔍 Testing connections page name display...")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Create MCP test runner
            runner = MCPPlaywrightTestRunner(page)
            
            # Login first
            print("1. Logging in...")
            login_success = runner.run_pcba_login_test("admin", "admin123")
            print(f"   Login result: {login_success}")
            
            if not login_success:
                print("❌ Login failed")
                return False
            
            # Navigate to connections page
            print("2. Navigating to connections page...")
            nav_success = runner.mcp_navigate('/connections')
            print(f"   Navigation result: {nav_success}")
            
            # Wait for page to load
            time.sleep(2)
            
            # Take screenshot
            print("3. Taking screenshot...")
            runner.mcp_screenshot('connections_page_names_test.png')
            
            # Check for connection records and their names
            print("4. Checking connection names...")
            
            connection_info = page.evaluate('''
                () => {
                    const rows = document.querySelectorAll('#connectionsTable tbody tr');
                    const connections = [];
                    
                    rows.forEach((row, index) => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const id = cells[0].textContent.trim();
                            const nameCell = cells[1];
                            const nameDiv = nameCell.querySelector('.fw-bold');
                            const name = nameDiv ? nameDiv.textContent.trim() : 'NO NAME FOUND';
                            
                            connections.push({
                                id: id,
                                name: name,
                                hasNameDiv: !!nameDiv,
                                nameCellHTML: nameCell.innerHTML.trim()
                            });
                        }
                    });
                    
                    return {
                        totalRows: rows.length,
                        connections: connections,
                        tableExists: !!document.querySelector('#connectionsTable'),
                        tbodyExists: !!document.querySelector('#connectionsTable tbody')
                    };
                }
            ''')
            
            print(f"   Table info: {connection_info}")
            
            # Analysis
            print("\n📊 Connection Name Analysis:")
            if connection_info['tableExists']:
                print("   ✅ Connections table found")
                
                if connection_info['totalRows'] > 0:
                    print(f"   ✅ Found {connection_info['totalRows']} connection record(s)")
                    
                    empty_names = 0
                    for conn in connection_info['connections']:
                        print(f"   Connection ID {conn['id']}:")
                        print(f"     - Name: '{conn['name']}'")
                        print(f"     - Has name div: {conn['hasNameDiv']}")
                        
                        if not conn['name'] or conn['name'] == 'NO NAME FOUND':
                            empty_names += 1
                            print(f"     ❌ Empty or missing name")
                            print(f"     - Cell HTML: {conn['nameCellHTML']}")
                        else:
                            print(f"     ✅ Name displays correctly")
                    
                    if empty_names == 0:
                        print(f"\n🎉 SUCCESS: All {len(connection_info['connections'])} connection names display correctly!")
                        result = True
                    else:
                        print(f"\n❌ ISSUE: {empty_names} connection(s) have empty names")
                        result = False
                else:
                    print("   ⚠️  No connection records found in table")
                    result = True  # Not an error if no connections exist
            else:
                print("   ❌ Connections table not found")
                result = False
            
            browser.close()
            return result
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_connections_page_names()
    print(f"\n{'✅ Test passed' if result else '❌ Test failed'}")
    sys.exit(0 if result else 1)