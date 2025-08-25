import pytest
import time
import json
from playwright.sync_api import Page
from tests.mcp_playwright_integration import MCPPlaywrightTestRunner, PlaywrightMCPClient

class TestPCBAWithMCP:
    """
    PCBA Test System tests using MCP Playwright integration
    Demonstrates the full capabilities of MCP server integration
    """
    
    @pytest.fixture(scope="function")
    def mcp_test_runner(self, page: Page):
        """Setup MCP Playwright test runner"""
        runner = MCPPlaywrightTestRunner(page)
        yield runner
        runner.cleanup()
    
    @pytest.mark.smoke
    @pytest.mark.mcp
    def test_mcp_login_functionality(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test PCBA login with full MCP integration"""
        print("\n🚀 Starting MCP-integrated login test...")
        
        # Run the comprehensive login test
        success = mcp_test_runner.run_pcba_login_test()
        
        assert success, "Login test should pass with MCP integration"
        print("✅ MCP login test completed successfully!")
    
    @pytest.mark.ui
    @pytest.mark.mcp
    def test_mcp_dashboard_functionality(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test PCBA dashboard with MCP integration"""
        print("\n📊 Starting MCP-integrated dashboard test...")
        
        # First ensure we're logged in
        login_success = mcp_test_runner.run_pcba_login_test()
        assert login_success, "Must be logged in to test dashboard"
        
        # Run dashboard test
        dashboard_success = mcp_test_runner.run_pcba_dashboard_test()
        
        assert dashboard_success, "Dashboard test should pass with MCP integration"
        print("✅ MCP dashboard test completed successfully!")
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_comprehensive_pcba_workflow(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Run comprehensive PCBA test workflow with MCP integration"""
        print("\n🔬 Starting comprehensive MCP test workflow...")
        
        # Run the full test suite
        results = mcp_test_runner.run_comprehensive_pcba_test()
        
        print(f"\n📋 Test Results Summary:")
        print(f"   Session ID: {results['session_id']}")
        print(f"   Duration: {results['duration']:.2f} seconds")
        print(f"   Pass Rate: {results['pass_rate']:.1f}%")
        print(f"   Overall Success: {results['overall_success']}")
        
        for test_name, success in results["tests"].items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        # Save results to file
        results_file = f"tests/reports/mcp_test_results_{int(time.time())}.json"
        import os
        os.makedirs("tests/reports", exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to: {results_file}")
        
        # Assert overall success
        assert results["overall_success"], f"Comprehensive test should pass. Pass rate: {results['pass_rate']:.1f}%"
        print("✅ Comprehensive MCP test workflow completed successfully!")
    
    @pytest.mark.mcp
    def test_mcp_screenshot_capability(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test MCP screenshot functionality"""
        print("\n📸 Testing MCP screenshot capability...")
        
        # Navigate to application
        mcp_test_runner.mcp_navigate("/")
        
        # Take multiple screenshots with different configurations
        screenshot1 = mcp_test_runner.mcp_screenshot("mcp_test_full_page.png", full_page=True)
        screenshot2 = mcp_test_runner.mcp_screenshot("mcp_test_viewport.png", full_page=False)
        
        # Verify screenshots were created
        from pathlib import Path
        assert Path(screenshot1).exists(), f"Full page screenshot should exist: {screenshot1}"
        assert Path(screenshot2).exists(), f"Viewport screenshot should exist: {screenshot2}"
        
        print(f"✅ Screenshots created: {screenshot1}, {screenshot2}")
    
    @pytest.mark.mcp
    def test_mcp_form_interaction(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test MCP form interaction capabilities"""
        print("\n📝 Testing MCP form interaction...")
        
        # Navigate to login page
        success = mcp_test_runner.mcp_navigate("/login")
        assert success, "Should navigate to login page"
        
        # Test form filling with MCP
        username_success = mcp_test_runner.mcp_fill("input[name='username']", "test_user")
        password_success = mcp_test_runner.mcp_fill("input[name='password']", "test_password")
        
        assert username_success, "Should fill username field"
        assert password_success, "Should fill password field"
        
        # Get form values to verify
        username_value = mcp_test_runner.mcp_evaluate("document.querySelector('input[name=\"username\"]').value")
        password_value = mcp_test_runner.mcp_evaluate("document.querySelector('input[name=\"password\"]').value")
        
        assert username_value == "test_user", f"Username should be filled correctly, got: {username_value}"
        assert password_value == "test_password", f"Password should be filled correctly, got: {password_value}"
        
        print("✅ MCP form interaction test completed successfully!")
    
    @pytest.mark.mcp
    def test_mcp_text_extraction(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test MCP text extraction capabilities"""
        print("\n📖 Testing MCP text extraction...")
        
        # Navigate to application
        mcp_test_runner.mcp_navigate("/")
        
        # Extract text from different elements
        page_text = mcp_test_runner.mcp_get_visible_text("body")
        title_text = mcp_test_runner.mcp_get_visible_text("h1")
        
        assert len(page_text) > 0, "Should extract page text"
        print(f"   Page text length: {len(page_text)} characters")
        print(f"   Title text: {title_text}")
        
        # Check for PCBA-related content
        pcba_keywords = ["pcba", "test", "system", "dashboard"]
        found_keywords = [keyword for keyword in pcba_keywords 
                         if keyword.lower() in page_text.lower()]
        
        assert len(found_keywords) > 0, f"Should find PCBA-related content. Found: {found_keywords}"
        print(f"✅ Found PCBA keywords: {found_keywords}")
    
    @pytest.mark.mcp
    def test_mcp_javascript_evaluation(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test MCP JavaScript evaluation capabilities"""
        print("\n🔧 Testing MCP JavaScript evaluation...")
        
        # Navigate to application
        mcp_test_runner.mcp_navigate("/")
        
        # Test various JavaScript evaluations
        page_title = mcp_test_runner.mcp_evaluate("document.title")
        page_url = mcp_test_runner.mcp_evaluate("window.location.href")
        form_count = mcp_test_runner.mcp_evaluate("document.forms.length")
        link_count = mcp_test_runner.mcp_evaluate("document.links.length")
        
        assert page_title is not None, "Should get page title"
        assert page_url is not None, "Should get page URL"
        assert isinstance(form_count, int), "Form count should be integer"
        assert isinstance(link_count, int), "Link count should be integer"
        
        print(f"   Page title: {page_title}")
        print(f"   Page URL: {page_url}")
        print(f"   Forms on page: {form_count}")
        print(f"   Links on page: {link_count}")
        
        # Test custom JavaScript
        custom_result = mcp_test_runner.mcp_evaluate("""
            {
                hasBootstrap: typeof bootstrap !== 'undefined',
                hasJQuery: typeof $ !== 'undefined',
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight
            }
        """)
        
        assert custom_result is not None, "Custom JavaScript should execute"
        print(f"   Custom evaluation result: {custom_result}")
        
        print("✅ MCP JavaScript evaluation test completed successfully!")
    
    @pytest.mark.slow
    @pytest.mark.mcp
    def test_mcp_performance_monitoring(self, mcp_test_runner: MCPPlaywrightTestRunner):
        """Test MCP performance monitoring capabilities"""
        print("\n⏱️ Testing MCP performance monitoring...")
        
        start_time = time.time()
        
        # Perform various operations and measure timing
        operations = [
            ("navigate_home", lambda: mcp_test_runner.mcp_navigate("/")),
            ("navigate_login", lambda: mcp_test_runner.mcp_navigate("/login")),
            ("take_screenshot", lambda: mcp_test_runner.mcp_screenshot("performance_test.png")),
            ("extract_text", lambda: mcp_test_runner.mcp_get_visible_text()),
            ("evaluate_js", lambda: mcp_test_runner.mcp_evaluate("document.readyState"))
        ]
        
        timings = {}
        
        for operation_name, operation_func in operations:
            op_start = time.time()
            result = operation_func()
            op_end = time.time()
            
            timings[operation_name] = {
                "duration": op_end - op_start,
                "success": result is not False and result is not None
            }
        
        total_time = time.time() - start_time
        
        print(f"   Total test duration: {total_time:.2f} seconds")
        for op_name, timing in timings.items():
            status = "✅" if timing["success"] else "❌"
            print(f"   {op_name}: {timing['duration']:.2f}s {status}")
        
        # Assert reasonable performance
        assert total_time < 30, f"Total test time should be reasonable, got {total_time:.2f}s"
        
        # Check that all operations succeeded
        failed_operations = [name for name, timing in timings.items() if not timing["success"]]
        assert len(failed_operations) == 0, f"All operations should succeed. Failed: {failed_operations}"
        
        print("✅ MCP performance monitoring test completed successfully!")

class TestMCPClientDirect:
    """
    Direct tests for the MCP client functionality
    """
    
    @pytest.mark.mcp
    def test_mcp_client_initialization(self):
        """Test MCP client can be initialized"""
        client = PlaywrightMCPClient()
        
        assert client.auto_approve_actions is not None
        assert len(client.auto_approve_actions) > 0
        assert "playwright_navigate" in client.auto_approve_actions
        assert client.base_url == "http://localhost:9002"
        
        print("✅ MCP client initialization test passed!")
    
    @pytest.mark.mcp
    def test_mcp_session_management(self):
        """Test MCP session creation and management"""
        client = PlaywrightMCPClient()
        
        # Test session creation
        session_id = client.create_test_session("test_session")
        assert session_id is not None
        assert "test_session" in session_id
        
        # Test logging
        client.log_test_action("test_action", "success", {"test": "data"})
        
        print(f"✅ Session management test passed! Session ID: {session_id}")
    
    def teardown_class(self):
        """Cleanup after all tests"""
        print("\n🧹 Cleaning up MCP test resources...")
        
        # Clean up any remaining resources
        import os
        import glob
        
        # Clean up test screenshots
        screenshot_files = glob.glob("tests/screenshots/mcp_*.png")
        for file in screenshot_files:
            try:
                os.remove(file)
                print(f"   Cleaned up: {file}")
            except:
                pass
        
        print("✅ Cleanup completed!")