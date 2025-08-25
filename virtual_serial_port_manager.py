#!/usr/bin/env python3
"""
Virtual Serial Port Manager for Modbus RTU Testing
Creates virtual COM port pairs for testing Modbus communication without physical hardware
"""

import subprocess
import os
import sys
import time
import psutil
from typing import Tuple, Optional, List
import logging

class VirtualSerialPortManager:
    """
    Manages virtual serial port pairs for testing
    Uses com0com on Windows or socat on Linux
    """
    
    def __init__(self):
        self.logger = logging.getLogger("VirtualSerialPort")
        self.created_ports = []
        self.is_windows = sys.platform.startswith('win')
        
    def check_prerequisites(self) -> bool:
        """Check if required tools are available"""
        if self.is_windows:
            return self._check_com0com()
        else:
            return self._check_socat()
    
    def _check_com0com(self) -> bool:
        """Check if com0com is installed on Windows"""
        try:
            # Check if com0com is installed
            result = subprocess.run(['reg', 'query', 'HKLM\\SYSTEM\\CurrentControlSet\\Services\\com0com'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✅ com0com detected")
                return True
            else:
                self.logger.warning("❌ com0com not found")
                return False
        except Exception as e:
            self.logger.error(f"Error checking com0com: {e}")
            return False
    
    def _check_socat(self) -> bool:
        """Check if socat is available on Linux"""
        try:
            result = subprocess.run(['which', 'socat'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✅ socat detected")
                return True
            else:
                self.logger.warning("❌ socat not found")
                return False
        except Exception as e:
            self.logger.error(f"Error checking socat: {e}")
            return False
    
    def install_prerequisites(self) -> bool:
        """Install required tools"""
        if self.is_windows:
            return self._install_com0com()
        else:
            return self._install_socat()
    
    def _install_com0com(self) -> bool:
        """Provide instructions for com0com installation"""
        print("""
🔧 COM0COM Installation Required

To create virtual serial ports on Windows, please install com0com:

1. Download from: https://sourceforge.net/projects/com0com/
2. Run setup as Administrator
3. After installation, create a port pair:
   - Open com0com setup
   - Add port pair (e.g., COM10 <-> COM11)

Alternative: Use HW VSP3 (Hardware Virtual Serial Port)
- Download from: https://www.hw-group.com/software/hw-vsp3-virtual-serial-port
        """)
        return False
    
    def _install_socat(self) -> bool:
        """Install socat on Linux"""
        try:
            # Try to install socat
            if os.path.exists('/usr/bin/apt-get'):
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'socat'], check=True)
            elif os.path.exists('/usr/bin/yum'):
                subprocess.run(['sudo', 'yum', 'install', '-y', 'socat'], check=True)
            else:
                self.logger.error("Package manager not found")
                return False
            
            return self._check_socat()
        except Exception as e:
            self.logger.error(f"Failed to install socat: {e}")
            return False
    
    def create_virtual_port_pair(self, port1: str = None, port2: str = None) -> Optional[Tuple[str, str]]:
        """Create a virtual serial port pair"""
        if self.is_windows:
            return self._create_windows_port_pair(port1, port2)
        else:
            return self._create_linux_port_pair(port1, port2)
    
    def _create_windows_port_pair(self, port1: str = None, port2: str = None) -> Optional[Tuple[str, str]]:
        """Create virtual port pair on Windows using com0com"""
        try:
            # For Windows, we'll use existing com0com pairs or suggest manual setup
            # Check for existing available ports
            available_ports = self._find_available_com_ports()
            
            if len(available_ports) >= 2:
                port1 = port1 or available_ports[0]
                port2 = port2 or available_ports[1]
                
                self.logger.info(f"Using existing COM ports: {port1} <-> {port2}")
                self.created_ports.append((port1, port2))
                return (port1, port2)
            else:
                self.logger.warning("Not enough available COM ports found")
                print("""
⚠️  Manual Setup Required:

1. Install com0com from: https://sourceforge.net/projects/com0com/
2. Run setupc.exe as Administrator
3. Add a new port pair (e.g., COM10 <-> COM11)
4. Use these ports for testing

Example commands in setupc:
> install PortName=COM10 PortName=COM11
> list
> quit
                """)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create Windows port pair: {e}")
            return None
    
    def _create_linux_port_pair(self, port1: str = None, port2: str = None) -> Optional[Tuple[str, str]]:
        """Create virtual port pair on Linux using socat"""
        try:
            if not self._check_socat():
                self.logger.error("socat not available")
                return None
            
            # Use default port names if not specified
            port1 = port1 or "/tmp/ttyV0"
            port2 = port2 or "/tmp/ttyV1"
            
            # Create virtual port pair using socat
            cmd = [
                'socat', 
                f'pty,link={port1},raw,echo=0',
                f'pty,link={port2},raw,echo=0'
            ]
            
            # Start socat in background
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a bit for ports to be created
            time.sleep(1)
            
            # Check if ports exist
            if os.path.exists(port1) and os.path.exists(port2):
                self.logger.info(f"Created virtual port pair: {port1} <-> {port2}")
                self.created_ports.append((port1, port2))
                return (port1, port2)
            else:
                self.logger.error("Failed to create virtual ports")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create Linux port pair: {e}")
            return None
    
    def _find_available_com_ports(self) -> List[str]:
        """Find available COM ports on Windows"""
        import serial.tools.list_ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            try:
                # Try to open the port briefly
                ser = serial.Serial(port.device, timeout=0.1)
                ser.close()
                ports.append(port.device)
            except:
                continue
        
        return ports
    
    def list_virtual_ports(self) -> List[Tuple[str, str]]:
        """List created virtual port pairs"""
        return self.created_ports
    
    def cleanup(self):
        """Clean up created virtual ports"""
        # For Linux, kill socat processes
        if not self.is_windows:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if proc.info['name'] == 'socat':
                        cmdline = proc.info['cmdline']
                        if cmdline and any('/tmp/ttyV' in arg for arg in cmdline):
                            proc.kill()
                            self.logger.info(f"Killed socat process {proc.info['pid']}")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
        
        self.created_ports.clear()
    
    def get_recommended_setup(self) -> dict:
        """Get recommended setup for PCBA testing"""
        if self.is_windows:
            return {
                "platform": "Windows",
                "tool": "com0com",
                "recommended_ports": ["COM10", "COM11"],
                "plc_simulator_port": "COM10",
                "pcba_test_port": "COM11",
                "installation_url": "https://sourceforge.net/projects/com0com/",
                "setup_instructions": [
                    "1. Download and install com0com as Administrator",
                    "2. Run setupc.exe",
                    "3. Execute: install PortName=COM10 PortName=COM11",
                    "4. Start PLC simulator on COM10",
                    "5. Configure PCBA system to use COM11"
                ]
            }
        else:
            return {
                "platform": "Linux",
                "tool": "socat",
                "recommended_ports": ["/tmp/ttyV0", "/tmp/ttyV1"],
                "plc_simulator_port": "/tmp/ttyV0",
                "pcba_test_port": "/tmp/ttyV1",
                "installation_cmd": "sudo apt-get install socat",
                "setup_instructions": [
                    "1. Install socat: sudo apt-get install socat",
                    "2. Create port pair with this manager",
                    "3. Start PLC simulator on /tmp/ttyV0",
                    "4. Configure PCBA system to use /tmp/ttyV1"
                ]
            }

def main():
    """Main function for testing virtual port manager"""
    logging.basicConfig(level=logging.INFO)
    
    manager = VirtualSerialPortManager()
    
    print("🔌 Virtual Serial Port Manager")
    print("=" * 40)
    
    # Check prerequisites
    if manager.check_prerequisites():
        print("✅ Prerequisites satisfied")
        
        # Try to create a port pair
        ports = manager.create_virtual_port_pair()
        if ports:
            print(f"✅ Created virtual port pair: {ports[0]} <-> {ports[1]}")
            print("\nYou can now use these ports for testing:")
            print(f"  - PLC Simulator: {ports[0]}")
            print(f"  - PCBA System: {ports[1]}")
        else:
            print("❌ Failed to create virtual ports")
    else:
        print("❌ Prerequisites not met")
        manager.install_prerequisites()
    
    # Show recommended setup
    setup = manager.get_recommended_setup()
    print(f"\n📋 Recommended Setup for {setup['platform']}:")
    print(f"Tool: {setup['tool']}")
    print(f"Ports: {setup['recommended_ports']}")
    print("\nSetup Instructions:")
    for instruction in setup['setup_instructions']:
        print(f"  {instruction}")

if __name__ == "__main__":
    main()