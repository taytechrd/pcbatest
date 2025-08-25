#!/usr/bin/env python3
"""
Modbus RTU Test Client for PCBA Test System
Tests and validates the Modbus RTU PLC simulator functionality
"""

import serial
import struct
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ModbusTestResult:
    """Result of a Modbus test operation"""
    operation: str
    success: bool
    request_data: bytes
    response_data: Optional[bytes]
    values: Optional[Dict[str, Any]]
    error_message: Optional[str]
    duration: float
    timestamp: datetime

class ModbusRTUTestClient:
    """
    Modbus RTU test client for testing PLC simulator
    """
    
    def __init__(self, port: str = "COM11", baudrate: int = 9600, 
                 device_id: int = 1, timeout: float = 2.0):
        """
        Initialize Modbus RTU test client
        
        Args:
            port: Serial port (should be paired with simulator port)
            baudrate: Communication speed
            device_id: Target Modbus device ID
            timeout: Response timeout
        """
        self.port = port
        self.baudrate = baudrate
        self.device_id = device_id
        self.timeout = timeout
        self.serial_conn = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ModbusRTU_TestClient")
        
        # Test results storage
        self.test_results: List[ModbusTestResult] = []
        
        # PCBA-specific register mappings (matching simulator)
        self.register_map = {
            # Input registers (read-only sensor data)
            "voltage_3v3": 0,       # 3.3V rail (mV)
            "voltage_5v": 1,        # 5V rail (mV)
            "voltage_1v2": 2,       # 1.2V rail (mV)
            "voltage_2v5": 3,       # 2.5V reference (mV)
            "voltage_1v8": 4,       # 1.8V rail (mV)
            "current_total": 10,    # Total current (mA)
            "current_digital": 11,  # Digital section current (mA)
            "current_analog": 12,   # Analog section current (mA)
            "temp_ambient": 20,     # Ambient temperature (0.1°C)
            "temp_hotspot": 21,     # Hot spot temperature (0.1°C)
            
            # Holding registers (read/write control data)
            "test_mode": 0,         # Test mode (1=auto, 2=manual)
            "test_step": 1,         # Current test sequence step
            "test_timeout": 2,      # Test timeout (seconds)
            
            # Coils (digital outputs/status)
            "system_ready": 0,      # System ready flag
            "test_in_progress": 1,  # Test in progress flag
            "power_good": 2,        # Power supply good
            "alarm_active": 3,      # Alarm condition
            
            # Discrete inputs (digital inputs from DUT)
            "dut_power_on": 0,      # DUT power on status
            "dut_test_mode": 1,     # DUT in test mode
            "dut_ready": 2,         # DUT ready for test
        }
    
    def _calculate_crc(self, data: bytes) -> int:
        """Calculate Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _create_request(self, function_code: int, data: bytes) -> bytes:
        """Create Modbus request frame with CRC"""
        frame = struct.pack('BB', self.device_id, function_code) + data
        crc = self._calculate_crc(frame)
        frame += struct.pack('<H', crc)
        return frame
    
    def _verify_response(self, response: bytes) -> bool:
        """Verify CRC of response frame"""
        if len(response) < 4:
            return False
        
        data = response[:-2]
        received_crc = struct.unpack('<H', response[-2:])[0]
        calculated_crc = self._calculate_crc(data)
        
        return received_crc == calculated_crc
    
    def connect(self) -> bool:
        """Connect to Modbus device"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            self.logger.info(f"Connected to Modbus device on {self.port} at {self.baudrate} baud")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Modbus device"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.logger.info("Disconnected from Modbus device")
    
    def _send_request(self, request: bytes) -> Optional[bytes]:
        """Send request and receive response"""
        if not self.serial_conn or not self.serial_conn.is_open:
            raise ConnectionError("Not connected to Modbus device")
        
        try:
            # Clear input buffer
            self.serial_conn.reset_input_buffer()
            
            # Send request
            self.serial_conn.write(request)
            self.logger.debug(f"Sent: {request.hex()}")
            
            # Read response
            response = b""
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                if self.serial_conn.in_waiting > 0:
                    response += self.serial_conn.read(self.serial_conn.in_waiting)
                    # Check if we have a complete frame (minimum 5 bytes for error response)
                    if len(response) >= 5:
                        break
                time.sleep(0.01)
            
            self.logger.debug(f"Received: {response.hex()}")
            return response if response else None
            
        except Exception as e:
            self.logger.error(f"Communication error: {e}")
            return None
    
    def read_input_registers(self, start_addr: int, count: int) -> ModbusTestResult:
        """Read input registers (function code 0x04)"""
        operation = f"read_input_registers({start_addr}, {count})"
        start_time = time.time()
        
        try:
            # Create request
            data = struct.pack('>HH', start_addr, count)
            request = self._create_request(0x04, data)
            
            # Send request and get response
            response = self._send_request(request)
            duration = time.time() - start_time
            
            if not response:
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=None,
                    values=None,
                    error_message="No response received",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Verify response
            if not self._verify_response(response):
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message="Invalid CRC",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Parse response
            if len(response) < 5:
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message="Response too short",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Check for error response
            if response[1] & 0x80:
                error_code = response[2]
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message=f"Modbus error code: {error_code}",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Parse register values
            byte_count = response[2]
            values = {}
            
            for i in range(count):
                if 3 + i * 2 + 1 < len(response) - 2:  # Ensure we don't read past the data
                    reg_value = struct.unpack('>H', response[3 + i * 2:3 + i * 2 + 2])[0]
                    values[f"register_{start_addr + i}"] = reg_value
            
            result = ModbusTestResult(
                operation=operation,
                success=True,
                request_data=request,
                response_data=response,
                values=values,
                error_message=None,
                duration=duration,
                timestamp=datetime.now()
            )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return ModbusTestResult(
                operation=operation,
                success=False,
                request_data=request if 'request' in locals() else b'',
                response_data=response if 'response' in locals() else None,
                values=None,
                error_message=str(e),
                duration=duration,
                timestamp=datetime.now()
            )
    
    def read_holding_registers(self, start_addr: int, count: int) -> ModbusTestResult:
        """Read holding registers (function code 0x03)"""
        operation = f"read_holding_registers({start_addr}, {count})"
        start_time = time.time()
        
        try:
            data = struct.pack('>HH', start_addr, count)
            request = self._create_request(0x03, data)
            response = self._send_request(request)
            duration = time.time() - start_time
            
            if not response or not self._verify_response(response):
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message="Invalid response or CRC",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Parse values similar to input registers
            values = {}
            if len(response) >= 5 and not (response[1] & 0x80):
                byte_count = response[2]
                for i in range(count):
                    if 3 + i * 2 + 1 < len(response) - 2:
                        reg_value = struct.unpack('>H', response[3 + i * 2:3 + i * 2 + 2])[0]
                        values[f"register_{start_addr + i}"] = reg_value
            
            result = ModbusTestResult(
                operation=operation,
                success=True,
                request_data=request,
                response_data=response,
                values=values,
                error_message=None,
                duration=duration,
                timestamp=datetime.now()
            )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return ModbusTestResult(
                operation=operation,
                success=False,
                request_data=request if 'request' in locals() else b'',
                response_data=response if 'response' in locals() else None,
                values=None,
                error_message=str(e),
                duration=duration,
                timestamp=datetime.now()
            )
    
    def write_single_register(self, addr: int, value: int) -> ModbusTestResult:
        """Write single holding register (function code 0x06)"""
        operation = f"write_single_register({addr}, {value})"
        start_time = time.time()
        
        try:
            data = struct.pack('>HH', addr, value)
            request = self._create_request(0x06, data)
            response = self._send_request(request)
            duration = time.time() - start_time
            
            if not response or not self._verify_response(response):
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message="Invalid response or CRC",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # For write operations, response should echo the request
            success = (len(response) >= 8 and 
                      response[0] == self.device_id and 
                      response[1] == 0x06 and
                      not (response[1] & 0x80))
            
            values = {"written_value": value} if success else None
            
            result = ModbusTestResult(
                operation=operation,
                success=success,
                request_data=request,
                response_data=response,
                values=values,
                error_message=None if success else "Write operation failed",
                duration=duration,
                timestamp=datetime.now()
            )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return ModbusTestResult(
                operation=operation,
                success=False,
                request_data=request if 'request' in locals() else b'',
                response_data=response if 'response' in locals() else None,
                values=None,
                error_message=str(e),
                duration=duration,
                timestamp=datetime.now()
            )
    
    def read_coils(self, start_addr: int, count: int) -> ModbusTestResult:
        """Read coils (function code 0x01)"""
        operation = f"read_coils({start_addr}, {count})"
        start_time = time.time()
        
        try:
            data = struct.pack('>HH', start_addr, count)
            request = self._create_request(0x01, data)
            response = self._send_request(request)
            duration = time.time() - start_time
            
            if not response or not self._verify_response(response):
                return ModbusTestResult(
                    operation=operation,
                    success=False,
                    request_data=request,
                    response_data=response,
                    values=None,
                    error_message="Invalid response or CRC",
                    duration=duration,
                    timestamp=datetime.now()
                )
            
            # Parse coil values
            values = {}
            if len(response) >= 4 and not (response[1] & 0x80):
                byte_count = response[2]
                for byte_idx in range(byte_count):
                    if 3 + byte_idx < len(response) - 2:
                        byte_val = response[3 + byte_idx]
                        for bit_idx in range(8):
                            coil_idx = start_addr + byte_idx * 8 + bit_idx
                            if coil_idx < start_addr + count:
                                values[f"coil_{coil_idx}"] = bool(byte_val & (1 << bit_idx))
            
            result = ModbusTestResult(
                operation=operation,
                success=True,
                request_data=request,
                response_data=response,
                values=values,
                error_message=None,
                duration=duration,
                timestamp=datetime.now()
            )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return ModbusTestResult(
                operation=operation,
                success=False,
                request_data=request if 'request' in locals() else b'',
                response_data=response if 'response' in locals() else None,
                values=None,
                error_message=str(e),
                duration=duration,
                timestamp=datetime.now()
            )
    
    def run_pcba_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive PCBA-specific Modbus test suite"""
        self.logger.info("🧪 Starting comprehensive PCBA Modbus test suite...")
        
        test_suite_results = {
            "start_time": datetime.now(),
            "tests": {},
            "summary": {},
            "pcba_data": {}
        }
        
        # Test 1: Read voltage measurements
        self.logger.info("📊 Testing voltage measurements...")
        voltage_test = self.read_input_registers(0, 5)  # Voltages 0-4
        test_suite_results["tests"]["voltage_readings"] = voltage_test
        
        if voltage_test.success and voltage_test.values:
            test_suite_results["pcba_data"]["voltages"] = {
                "3V3_rail_mV": voltage_test.values.get("register_0", 0),
                "5V_rail_mV": voltage_test.values.get("register_1", 0),
                "1V2_rail_mV": voltage_test.values.get("register_2", 0),
                "2V5_ref_mV": voltage_test.values.get("register_3", 0),
                "1V8_rail_mV": voltage_test.values.get("register_4", 0)
            }
        
        # Test 2: Read current measurements
        self.logger.info("⚡ Testing current measurements...")
        current_test = self.read_input_registers(10, 3)  # Currents 10-12
        test_suite_results["tests"]["current_readings"] = current_test
        
        if current_test.success and current_test.values:
            test_suite_results["pcba_data"]["currents"] = {
                "total_current_mA": current_test.values.get("register_10", 0),
                "digital_current_mA": current_test.values.get("register_11", 0),
                "analog_current_mA": current_test.values.get("register_12", 0)
            }
        
        # Test 3: Read temperature measurements
        self.logger.info("🌡️ Testing temperature measurements...")
        temp_test = self.read_input_registers(20, 2)  # Temperatures 20-21
        test_suite_results["tests"]["temperature_readings"] = temp_test
        
        if temp_test.success and temp_test.values:
            test_suite_results["pcba_data"]["temperatures"] = {
                "ambient_temp_C": temp_test.values.get("register_20", 0) / 10.0,
                "hotspot_temp_C": temp_test.values.get("register_21", 0) / 10.0
            }
        
        # Test 4: Read system status coils
        self.logger.info("🚦 Testing system status...")
        status_test = self.read_coils(0, 4)  # Status coils 0-3
        test_suite_results["tests"]["system_status"] = status_test
        
        if status_test.success and status_test.values:
            test_suite_results["pcba_data"]["system_status"] = {
                "system_ready": status_test.values.get("coil_0", False),
                "test_in_progress": status_test.values.get("coil_1", False),
                "power_good": status_test.values.get("coil_2", False),
                "alarm_active": status_test.values.get("coil_3", False)
            }
        
        # Test 5: Read control registers
        self.logger.info("🎛️ Testing control registers...")
        control_test = self.read_holding_registers(0, 3)  # Control registers 0-2
        test_suite_results["tests"]["control_registers"] = control_test
        
        if control_test.success and control_test.values:
            test_suite_results["pcba_data"]["control"] = {
                "test_mode": control_test.values.get("register_0", 0),
                "test_step": control_test.values.get("register_1", 0),
                "test_timeout": control_test.values.get("register_2", 0)
            }
        
        # Test 6: Write test - Change test mode
        self.logger.info("✍️ Testing write operations...")
        write_test = self.write_single_register(0, 2)  # Set manual mode
        test_suite_results["tests"]["write_test_mode"] = write_test
        
        # Test 7: Verify write operation
        verify_test = self.read_holding_registers(0, 1)
        test_suite_results["tests"]["verify_write"] = verify_test
        
        # Calculate summary
        total_tests = len(test_suite_results["tests"])
        passed_tests = sum(1 for test in test_suite_results["tests"].values() if test.success)
        
        test_suite_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "end_time": datetime.now(),
            "duration": (datetime.now() - test_suite_results["start_time"]).total_seconds()
        }
        
        # Print summary
        self.logger.info(f"\n📋 Test Suite Summary:")
        self.logger.info(f"  Total tests: {total_tests}")
        self.logger.info(f"  Passed: {passed_tests}")
        self.logger.info(f"  Failed: {total_tests - passed_tests}")
        self.logger.info(f"  Success rate: {test_suite_results['summary']['success_rate']:.1f}%")
        self.logger.info(f"  Duration: {test_suite_results['summary']['duration']:.2f}s")
        
        return test_suite_results
    
    def save_test_results(self, filename: str = None):
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"modbus_test_results_{timestamp}.json"
        
        # Convert test results to serializable format
        serializable_results = []
        for result in self.test_results:
            serializable_results.append({
                "operation": result.operation,
                "success": result.success,
                "request_data": result.request_data.hex() if result.request_data else None,
                "response_data": result.response_data.hex() if result.response_data else None,
                "values": result.values,
                "error_message": result.error_message,
                "duration": result.duration,
                "timestamp": result.timestamp.isoformat()
            })
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        self.logger.info(f"Test results saved to {filename}")

def main():
    """Main function for testing"""
    # You can modify these settings based on your virtual port configuration
    client = ModbusRTUTestClient(
        port="COM11",  # Adjust to your virtual port pair
        baudrate=9600,
        device_id=1,
        timeout=2.0
    )
    
    print("🔧 Modbus RTU Test Client for PCBA System")
    print("=" * 50)
    
    try:
        # Connect to device
        if not client.connect():
            print("❌ Failed to connect to Modbus device")
            return
        
        # Run comprehensive test
        results = client.run_pcba_comprehensive_test()
        
        # Save results
        client.save_test_results()
        
        # Print PCBA data if available
        if "pcba_data" in results:
            print("\n📊 PCBA Test Data:")
            for category, data in results["pcba_data"].items():
                print(f"  {category.title()}:")
                for key, value in data.items():
                    print(f"    {key}: {value}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()