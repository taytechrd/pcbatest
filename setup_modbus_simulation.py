#!/usr/bin/env python3
"""
Modbus RTU Simulation Setup Script
Installs required dependencies and configures the environment
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def install_python_packages():
    """Install required Python packages"""
    packages = [
        "pymodbus>=3.0.0",
        "pyserial>=3.5",
        "psutil>=5.8.0",
    ]
    
    print("📦 Installing Python packages...")
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                          check=True, capture_output=True)
            print(f"  ✅ {package}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install {package}: {e}")
            return False
    
    return True

def check_existing_installation():
    """Check if required packages are already installed"""
    try:
        import serial
        import psutil
        print("✅ Core packages already installed")
        return True
    except ImportError as e:
        print(f"❌ Missing packages: {e}")
        return False

def create_example_config():
    """Create example configuration files"""
    config_content = """# Modbus RTU Simulation Configuration
# Edit these settings based on your setup

[simulator]
port = COM10
baudrate = 9600
device_id = 1
timeout = 1.0

[client]
port = COM11
baudrate = 9600
device_id = 1
timeout = 2.0

[virtual_ports]
# Windows: use com0com
# Linux: use socat
auto_create = true
simulator_port = COM10
client_port = COM11

[pcba_test_data]
# Voltage rails (mV)
voltage_3v3 = 3300
voltage_5v = 5000
voltage_1v2 = 1200

# Current measurements (mA)
current_total = 150
current_digital = 50

# Temperature sensors (0.1°C)
temp_ambient = 250
temp_hotspot = 350
"""
    
    config_file = Path("modbus_config.ini")
    if not config_file.exists():
        with open(config_file, 'w') as f:
            f.write(config_content)
        print(f"✅ Created example configuration: {config_file}")
    else:
        print(f"📄 Configuration file already exists: {config_file}")

def setup_windows_virtual_ports():
    """Setup instructions for Windows virtual ports"""
    print("""
🪟 Windows Virtual Port Setup:

1. Download com0com from: https://sourceforge.net/projects/com0com/
2. Install as Administrator
3. Run setupc.exe and create port pair:
   > install PortName=COM10 PortName=COM11
   > list
   > quit

Alternative: HW VSP3 Virtual Serial Port
- Download from: https://www.hw-group.com/software/hw-vsp3-virtual-serial-port
- Create COM10 <-> COM11 pair

For testing without virtual ports:
- Use physical COM ports with null modem cable
- Use USB-to-Serial adapters with crossover connection
    """)

def setup_linux_virtual_ports():
    """Setup instructions for Linux virtual ports"""
    print("""
🐧 Linux Virtual Port Setup:

1. Install socat:
   sudo apt-get update
   sudo apt-get install socat

2. Create virtual port pair:
   socat pty,link=/tmp/ttyV0,raw,echo=0 pty,link=/tmp/ttyV1,raw,echo=0

3. Keep the socat terminal open during testing

Alternative for permanent setup:
- Create systemd service for socat
- Use udev rules for consistent port naming
    """)

def create_test_scripts():
    """Create convenient test scripts"""
    
    # Windows batch script
    windows_script = """@echo off
echo Starting Modbus RTU Simulation Test...
echo.

echo Starting PLC Simulator...
start "PLC Simulator" python modbus_plc_simulator.py --port COM10

echo Waiting 3 seconds for simulator to start...
timeout /t 3 /nobreak > nul

echo Starting Test Client...
python modbus_test_client.py

echo.
echo Test completed. Press any key to exit...
pause > nul
"""
    
    with open("run_modbus_test.bat", 'w') as f:
        f.write(windows_script)
    
    # Linux shell script
    linux_script = """#!/bin/bash
echo "Starting Modbus RTU Simulation Test..."
echo

echo "Starting PLC Simulator..."
python3 modbus_plc_simulator.py --port /tmp/ttyV0 &
SIMULATOR_PID=$!

echo "Waiting 3 seconds for simulator to start..."
sleep 3

echo "Starting Test Client..."
python3 modbus_test_client.py

echo
echo "Stopping simulator..."
kill $SIMULATOR_PID 2>/dev/null

echo "Test completed."
"""
    
    with open("run_modbus_test.sh", 'w') as f:
        f.write(linux_script)
    
    # Make shell script executable on Linux/Mac
    if platform.system() != "Windows":
        os.chmod("run_modbus_test.sh", 0o755)
    
    print("✅ Created test scripts:")
    print("  - run_modbus_test.bat (Windows)")
    print("  - run_modbus_test.sh (Linux)")

def main():
    """Main setup function"""
    print("🔧 Modbus RTU Simulation Setup")
    print("=" * 40)
    
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    print()
    
    # Check existing installation
    if not check_existing_installation():
        print("Installing required packages...")
        if not install_python_packages():
            print("❌ Failed to install packages")
            return 1
    
    # Create configuration files
    create_example_config()
    
    # Create test scripts
    create_test_scripts()
    
    # Platform-specific setup instructions
    if platform.system() == "Windows":
        setup_windows_virtual_ports()
    else:
        setup_linux_virtual_ports()
    
    print("\n✅ Setup completed!")
    print("\nNext steps:")
    print("1. Setup virtual serial ports (see instructions above)")
    print("2. Run integration test: python modbus_integration_test.py")
    print("3. Or use convenience scripts:")
    if platform.system() == "Windows":
        print("   - run_modbus_test.bat")
    else:
        print("   - ./run_modbus_test.sh")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())