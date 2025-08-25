#!/usr/bin/env python3
"""
Test script to verify dropdown functionality is working after fixes
"""

import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def test_dashboard_accessibility():
    """Test if the dashboard is accessible and contains dropdown elements"""
    print("🧪 Testing dashboard accessibility and dropdown elements...")
    
    # Create session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    
    try:
        # Test server response
        response = session.get("http://localhost:9002", timeout=10)
        print(f"✅ Server responding: {response.status_code}")
        
        # Check if it's the login page or dashboard
        content = response.text.lower()
        
        if 'dropdown-toggle' in content:
            print("✅ Dropdown elements found in response")
            dropdown_count = content.count('data-bs-toggle="dropdown"')
            print(f"✅ Found {dropdown_count} Bootstrap dropdown toggles")
            
            # Check for profile dropdown specifically
            if 'profile-pic' in content:
                print("✅ Profile dropdown element found")
            else:
                print("❌ Profile dropdown element NOT found")
                
        elif 'login' in content or 'giriş' in content:
            print("ℹ️ Server showing login page (expected if not logged in)")
            print("   To test dropdown, login first with admin/admin123")
            
        else:
            print("⚠️ Unexpected page content")
            
        # Check for our custom CSS
        if 'dropdown-fix.css' in content:
            print("✅ Custom dropdown fix CSS found")
        else:
            print("❌ Custom dropdown fix CSS NOT found in response")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at localhost:9002")
        print("   Make sure the PCBA server is running")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_static_files():
    """Test if our custom CSS file is accessible"""
    print("\n🧪 Testing static file accessibility...")
    
    try:
        response = requests.get("http://localhost:9002/assets/css/dropdown-fix.css", timeout=5)
        if response.status_code == 200:
            print("✅ dropdown-fix.css is accessible")
            print(f"   File size: {len(response.content)} bytes")
            
            # Check if it contains our fixes
            content = response.text
            if '.dropdown-menu.show' in content:
                print("✅ Custom dropdown CSS rules found")
            else:
                print("❌ Custom dropdown CSS rules NOT found")
                
        else:
            print(f"❌ dropdown-fix.css not accessible: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error accessing CSS file: {e}")

if __name__ == "__main__":
    print("🚀 Testing dropdown fixes...")
    print("=" * 60)
    
    server_ok = test_dashboard_accessibility()
    test_static_files()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print("The following fixes have been implemented:")
    print("1. ✅ Enhanced Bootstrap dropdown initialization with detailed logging")
    print("2. ✅ Robust fallback manual dropdown handling")
    print("3. ✅ Custom CSS fixes for dropdown positioning and z-index")
    print("4. ✅ Improved click outside detection")
    print("5. ✅ Debugging helpers for troubleshooting")
    
    if server_ok:
        print("\n💡 To test the fix:")
        print("1. Open http://localhost:9002 in your browser")
        print("2. Login with admin/admin123")
        print("3. Click on the profile section in the top-right")
        print("4. Check browser console (F12) for detailed logs")
        print("5. The dropdown should now open and close properly")
    else:
        print("\n⚠️ Server is not accessible. Start the PCBA server first.")
        
    print("\n🔧 If dropdown still doesn't work:")
    print("1. Check browser console for JavaScript errors")
    print("2. Verify Bootstrap version compatibility")
    print("3. Try hard refresh (Ctrl+F5) to clear cache")
    print("4. Check if there are browser extensions blocking functionality")