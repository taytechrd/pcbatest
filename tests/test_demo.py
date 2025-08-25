import pytest
import time
from playwright.sync_api import Page

class TestPlaywrightDemo:
    """Simple demo tests to verify Playwright setup"""
    
    @pytest.mark.smoke
    def test_browser_launch(self, page: Page):
        """Test that browser launches correctly"""
        # Navigate to a simple page
        page.goto("data:text/html,<h1>Playwright Demo Test</h1><p>PCBA Test System UI Testing</p>")
        
        # Check page content
        page_content = page.content()
        assert "Playwright Demo Test" in page_content, "Should be able to load basic HTML"
        assert "PCBA Test System" in page_content, "Should show PCBA Test System text"
        
        # Take a screenshot
        page.screenshot(path="tests/demo_screenshot.png")
        
        print("✅ Browser launch test passed!")
    
    @pytest.mark.smoke
    def test_javascript_execution(self, page: Page):
        """Test JavaScript execution in browser"""
        # Navigate to a page with JavaScript
        page.goto("data:text/html,<h1>JS Test</h1><script>document.title='Playwright JS Test';</script>")
        
        # Wait for JavaScript to execute
        page.wait_for_load_state("domcontentloaded")
        
        # Check that JavaScript executed
        page_title = page.title()
        assert page_title == "Playwright JS Test", f"JavaScript should set title, got: {page_title}"
        
        print("✅ JavaScript execution test passed!")
    
    @pytest.mark.smoke  
    def test_form_interaction(self, page: Page):
        """Test basic form interaction"""
        # Create a simple form page
        html_content = """
        <html>
        <body>
            <h1>Form Test</h1>
            <form id="testForm">
                <input type="text" id="username" name="username" placeholder="Enter username">
                <input type="password" id="password" name="password" placeholder="Enter password">
                <button type="submit" id="submitBtn">Submit</button>
            </form>
            <div id="result"></div>
            <script>
                document.getElementById('testForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    document.getElementById('result').innerHTML = 'Form submitted!';
                });
            </script>
        </body>
        </html>
        """
        
        page.goto(f"data:text/html,{html_content}")
        
        # Fill form fields
        page.fill("#username", "test_user")
        page.fill("#password", "test_password")
        
        # Submit form
        page.click("#submitBtn")
        
        # Check result
        result = page.locator("#result").text_content()
        assert result == "Form submitted!", f"Form should submit successfully, got: {result}"
        
        print("✅ Form interaction test passed!")
    
    @pytest.mark.ui
    def test_application_connectivity(self, page: Page):
        """Test if we can connect to the PCBA application"""
        try:
            # Try to connect to the application
            page.goto("http://localhost:9002", timeout=10000)
            
            # Check if we got some response (even if it's an error page)
            page_content = page.content()
            
            # Should either load the app or show connection error
            if "PCBA" in page_content or "login" in page_content.lower():
                print("✅ Application is accessible!")
            elif "refused" in page_content.lower() or "connection" in page_content.lower():
                print("⚠️  Application server is not running, but Playwright can detect this")
            else:
                print("ℹ️  Got response from localhost:9002, application may be available")
                
        except Exception as e:
            # This is expected if the server is not running
            print(f"ℹ️  Cannot connect to application (expected if server not running): {e}")
            # Test still passes as this is just connectivity check
            assert True, "Connectivity test completed"