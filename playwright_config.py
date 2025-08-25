import os
from playwright.sync_api import Playwright, BrowserType
from typing import Dict, Any

# Playwright Configuration for PCBA Test System
PLAYWRIGHT_CONFIG: Dict[str, Any] = {
    # Browser settings
    "browser": {
        "headless": os.getenv("HEADLESS", "false").lower() == "true",
        "slow_mo": int(os.getenv("SLOW_MO", "0")),  # Slow down operations for debugging
        "timeout": int(os.getenv("TIMEOUT", "30000")),  # 30 seconds default
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--allow-running-insecure-content"
        ]
    },
    
    # Test application settings
    "app": {
        "base_url": os.getenv("BASE_URL", "http://localhost:9002"),
        "username": os.getenv("TEST_USERNAME", "admin"),
        "password": os.getenv("TEST_PASSWORD", "admin123"),
        "timeout": int(os.getenv("APP_TIMEOUT", "10000"))
    },
    
    # Viewport settings
    "viewport": {
        "width": int(os.getenv("VIEWPORT_WIDTH", "1920")),
        "height": int(os.getenv("VIEWPORT_HEIGHT", "1080"))
    },
    
    # Screenshot and video settings
    "capture": {
        "screenshot": os.getenv("SCREENSHOT", "only-on-failure"),  # always, never, only-on-failure
        "video": os.getenv("VIDEO", "retain-on-failure"),  # on, off, retain-on-failure
        "trace": os.getenv("TRACE", "retain-on-failure")  # on, off, retain-on-failure
    },
    
    # Test data and paths
    "paths": {
        "screenshots": "tests/screenshots",
        "videos": "tests/videos", 
        "traces": "tests/traces",
        "downloads": "tests/downloads"
    },
    
    # Database settings for testing
    "database": {
        "test_db": "test_pcba.db",
        "backup_db": "pcba_test_backup.db"
    },
    
    # Network settings
    "network": {
        "offline": False,
        "slow_network": False,
        "block_resources": ["image", "stylesheet", "font"]  # Block to speed up tests
    }
}

def get_browser_context_options():
    """Get browser context options for Playwright"""
    return {
        "viewport": PLAYWRIGHT_CONFIG["viewport"],
        "ignore_https_errors": True,
        "record_video_dir": PLAYWRIGHT_CONFIG["paths"]["videos"] if PLAYWRIGHT_CONFIG["capture"]["video"] != "off" else None,
        "record_video_size": PLAYWRIGHT_CONFIG["viewport"]
    }

def get_browser_options():
    """Get browser launch options"""
    return {
        "headless": PLAYWRIGHT_CONFIG["browser"]["headless"],
        "slow_mo": PLAYWRIGHT_CONFIG["browser"]["slow_mo"],
        "args": PLAYWRIGHT_CONFIG["browser"]["args"]
    }