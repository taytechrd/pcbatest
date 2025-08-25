"""
PCBA Test System - Hardware Abstraction Layer
This module provides an abstraction layer for different test equipment types.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import serial
import socket
import time
import logging
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    """Supported connection types"""
    SERIAL_RTU = "serial_rtu"
    TCP_IP = "tcp_ip"
    USB = "usb"
    ETHERNET = "ethernet"

class TestEquipmentType(Enum):
    """Supported test equipment types"""
    MULTIMETER = "multimeter"
    POWER_SUPPLY = "power_supply"
    OSCILLOSCOPE = "oscilloscope"
    FUNCTION_GENERATOR = "function_generator"
    RELAY_BOARD = "relay_board"
    ICT_TESTER = "ict_tester"
    FCT_TESTER = "fct_tester"

class TestResult(Enum):
    """Test result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

@dataclass
class TestMeasurement:
    """Data structure for test measurements"""
    parameter: str
    value: float
    unit: str
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_within_limits(self) -> bool:
        """Check if measurement is within specified limits"""
        if self.min_limit is not None and self.value < self.min_limit:
            return False
        if self.max_limit is not None and self.value > self.max_limit:
            return False
        return True

@dataclass
class ConnectionConfig:
    """Configuration for equipment connections"""
    connection_type: ConnectionType
    address: str  # COM port, IP address, etc.
    port: Optional[int] = None
    baud_rate: Optional[int] = 9600
    timeout: float = 5.0
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}

class HardwareInterface(ABC):
    """Abstract base class for hardware interfaces"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connected = False
        self.last_error = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to equipment"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from equipment"""
        pass
    
    @abstractmethod
    def send_command(self, command: str) -> str:
        """Send command and get response"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status"""
        pass
    
    def get_last_error(self) -> Optional[str]:
        """Get last error message"""
        return self.last_error

class SerialInterface(HardwareInterface):
    """Serial port interface implementation"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.serial_connection = None
    
    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            self.serial_connection = serial.Serial(
                port=self.config.address,
                baudrate=self.config.baud_rate,
                timeout=self.config.timeout,
                bytesize=self.config.additional_params.get('bytesize', 8),
                parity=self.config.additional_params.get('parity', 'N'),
                stopbits=self.config.additional_params.get('stopbits', 1)
            )
            self.connected = True
            logger.info(f"Connected to serial port {self.config.address}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect to serial port {self.config.address}: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from serial port"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.connected = False
            logger.info(f"Disconnected from serial port {self.config.address}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to disconnect from serial port: {e}")
            return False
    
    def send_command(self, command: str) -> str:
        """Send command via serial and get response"""
        if not self.connected or not self.serial_connection:
            raise ConnectionError("Not connected to serial port")
        
        try:
            # Send command
            self.serial_connection.write((command + '\r\n').encode())
            
            # Read response
            response = self.serial_connection.readline().decode().strip()
            logger.debug(f"Sent: {command}, Received: {response}")
            return response
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Serial communication error: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if serial connection is active"""
        return self.connected and self.serial_connection and self.serial_connection.is_open

class TCPInterface(HardwareInterface):
    """TCP/IP interface implementation"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.socket_connection = None
    
    def connect(self) -> bool:
        """Connect via TCP/IP"""
        try:
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.settimeout(self.config.timeout)
            self.socket_connection.connect((self.config.address, self.config.port))
            self.connected = True
            logger.info(f"Connected to TCP {self.config.address}:{self.config.port}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect to TCP {self.config.address}:{self.config.port}: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect TCP connection"""
        try:
            if self.socket_connection:
                self.socket_connection.close()
            self.connected = False
            logger.info(f"Disconnected from TCP {self.config.address}:{self.config.port}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to disconnect from TCP: {e}")
            return False
    
    def send_command(self, command: str) -> str:
        """Send command via TCP and get response"""
        if not self.connected or not self.socket_connection:
            raise ConnectionError("Not connected to TCP port")
        
        try:
            # Send command
            self.socket_connection.send((command + '\r\n').encode())
            
            # Read response
            response = self.socket_connection.recv(1024).decode().strip()
            logger.debug(f"Sent: {command}, Received: {response}")
            return response
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"TCP communication error: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if TCP connection is active"""
        return self.connected and self.socket_connection

class TestEquipment(ABC):
    """Abstract base class for test equipment"""
    
    def __init__(self, name: str, equipment_type: TestEquipmentType, interface: HardwareInterface):
        self.name = name
        self.equipment_type = equipment_type
        self.interface = interface
        self.calibrated = False
        self.last_calibration = None
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize equipment"""
        pass
    
    @abstractmethod
    def reset(self) -> bool:
        """Reset equipment to default state"""
        pass
    
    @abstractmethod
    def self_test(self) -> bool:
        """Perform equipment self-test"""
        pass
    
    def connect(self) -> bool:
        """Connect to equipment"""
        return self.interface.connect()
    
    def disconnect(self) -> bool:
        """Disconnect from equipment"""
        return self.interface.disconnect()
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.interface.is_connected()

class Multimeter(TestEquipment):
    """Digital Multimeter implementation"""
    
    def __init__(self, name: str, interface: HardwareInterface):
        super().__init__(name, TestEquipmentType.MULTIMETER, interface)
    
    def initialize(self) -> bool:
        """Initialize multimeter"""
        try:
            if not self.connect():
                return False
            
            # Send identification query
            response = self.interface.send_command("*IDN?")
            logger.info(f"Multimeter identified: {response}")
            
            # Reset to known state
            self.interface.send_command("*RST")
            time.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize multimeter: {e}")
            return False
    
    def reset(self) -> bool:
        """Reset multimeter"""
        try:
            self.interface.send_command("*RST")
            return True
        except Exception as e:
            logger.error(f"Failed to reset multimeter: {e}")
            return False
    
    def self_test(self) -> bool:
        """Perform multimeter self-test"""
        try:
            response = self.interface.send_command("*TST?")
            return response.strip() == "0"  # 0 = pass, 1 = fail for most equipment
        except Exception as e:
            logger.error(f"Multimeter self-test failed: {e}")
            return False
    
    def measure_voltage_dc(self, range_value: Optional[float] = None) -> TestMeasurement:
        """Measure DC voltage"""
        try:
            if range_value:
                self.interface.send_command(f"VOLT:DC:RANG {range_value}")
            
            self.interface.send_command("CONF:VOLT:DC")
            response = self.interface.send_command("READ?")
            
            voltage = float(response.strip())
            return TestMeasurement("DC_VOLTAGE", voltage, "V")
        except Exception as e:
            logger.error(f"Failed to measure DC voltage: {e}")
            raise
    
    def measure_current_dc(self, range_value: Optional[float] = None) -> TestMeasurement:
        """Measure DC current"""
        try:
            if range_value:
                self.interface.send_command(f"CURR:DC:RANG {range_value}")
            
            self.interface.send_command("CONF:CURR:DC")
            response = self.interface.send_command("READ?")
            
            current = float(response.strip())
            return TestMeasurement("DC_CURRENT", current, "A")
        except Exception as e:
            logger.error(f"Failed to measure DC current: {e}")
            raise
    
    def measure_resistance(self, range_value: Optional[float] = None) -> TestMeasurement:
        """Measure resistance"""
        try:
            if range_value:
                self.interface.send_command(f"RES:RANG {range_value}")
            
            self.interface.send_command("CONF:RES")
            response = self.interface.send_command("READ?")
            
            resistance = float(response.strip())
            return TestMeasurement("RESISTANCE", resistance, "Ohm")
        except Exception as e:
            logger.error(f"Failed to measure resistance: {e}")
            raise

class PowerSupply(TestEquipment):
    """Programmable Power Supply implementation"""
    
    def __init__(self, name: str, interface: HardwareInterface):
        super().__init__(name, TestEquipmentType.POWER_SUPPLY, interface)
        self.output_enabled = False
    
    def initialize(self) -> bool:
        """Initialize power supply"""
        try:
            if not self.connect():
                return False
            
            # Send identification query
            response = self.interface.send_command("*IDN?")
            logger.info(f"Power supply identified: {response}")
            
            # Reset and turn off output
            self.interface.send_command("*RST")
            self.interface.send_command("OUTP OFF")
            self.output_enabled = False
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize power supply: {e}")
            return False
    
    def reset(self) -> bool:
        """Reset power supply"""
        try:
            self.interface.send_command("*RST")
            self.output_enabled = False
            return True
        except Exception as e:
            logger.error(f"Failed to reset power supply: {e}")
            return False
    
    def self_test(self) -> bool:
        """Perform power supply self-test"""
        try:
            response = self.interface.send_command("*TST?")
            return response.strip() == "0"
        except Exception as e:
            logger.error(f"Power supply self-test failed: {e}")
            return False
    
    def set_voltage(self, voltage: float) -> bool:
        """Set output voltage"""
        try:
            self.interface.send_command(f"VOLT {voltage}")
            return True
        except Exception as e:
            logger.error(f"Failed to set voltage: {e}")
            return False
    
    def set_current_limit(self, current: float) -> bool:
        """Set current limit"""
        try:
            self.interface.send_command(f"CURR {current}")
            return True
        except Exception as e:
            logger.error(f"Failed to set current limit: {e}")
            return False
    
    def enable_output(self, enable: bool = True) -> bool:
        """Enable or disable output"""
        try:
            command = "OUTP ON" if enable else "OUTP OFF"
            self.interface.send_command(command)
            self.output_enabled = enable
            return True
        except Exception as e:
            logger.error(f"Failed to set output state: {e}")
            return False
    
    def measure_output_voltage(self) -> TestMeasurement:
        """Measure actual output voltage"""
        try:
            response = self.interface.send_command("MEAS:VOLT?")
            voltage = float(response.strip())
            return TestMeasurement("OUTPUT_VOLTAGE", voltage, "V")
        except Exception as e:
            logger.error(f"Failed to measure output voltage: {e}")
            raise
    
    def measure_output_current(self) -> TestMeasurement:
        """Measure actual output current"""
        try:
            response = self.interface.send_command("MEAS:CURR?")
            current = float(response.strip())
            return TestMeasurement("OUTPUT_CURRENT", current, "A")
        except Exception as e:
            logger.error(f"Failed to measure output current: {e}")
            raise

class HardwareManager:
    """Manager class for handling multiple test equipment"""
    
    def __init__(self):
        self.equipment: Dict[str, TestEquipment] = {}
        self.active_connections: List[str] = []
    
    def add_equipment(self, equipment: TestEquipment) -> bool:
        """Add equipment to manager"""
        try:
            self.equipment[equipment.name] = equipment
            logger.info(f"Added equipment: {equipment.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add equipment: {e}")
            return False
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect to all equipment"""
        results = {}
        for name, equipment in self.equipment.items():
            try:
                success = equipment.connect() and equipment.initialize()
                results[name] = success
                if success:
                    self.active_connections.append(name)
                logger.info(f"Connection to {name}: {'Success' if success else 'Failed'}")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to connect to {name}: {e}")
        return results
    
    def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect from all equipment"""
        results = {}
        for name in self.active_connections:
            equipment = self.equipment[name]
            try:
                success = equipment.disconnect()
                results[name] = success
                logger.info(f"Disconnection from {name}: {'Success' if success else 'Failed'}")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to disconnect from {name}: {e}")
        self.active_connections.clear()
        return results
    
    def get_equipment(self, name: str) -> Optional[TestEquipment]:
        """Get equipment by name"""
        return self.equipment.get(name)
    
    def get_connected_equipment(self) -> List[TestEquipment]:
        """Get list of connected equipment"""
        return [self.equipment[name] for name in self.active_connections 
                if self.equipment[name].is_connected()]
    
    def perform_system_check(self) -> Dict[str, bool]:
        """Perform self-test on all connected equipment"""
        results = {}
        for name in self.active_connections:
            equipment = self.equipment[name]
            try:
                if equipment.is_connected():
                    results[name] = equipment.self_test()
                else:
                    results[name] = False
            except Exception as e:
                results[name] = False
                logger.error(f"Self-test failed for {name}: {e}")
        return results