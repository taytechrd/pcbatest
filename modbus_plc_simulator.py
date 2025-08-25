#!/usr/bin/env python3
"""
Modbus RTU PLC Simulator for PCBA Test System
Simulates a real PLC with Modbus RTU communication over serial port
"""

import serial
import time
import threading
import struct
from typing import Dict, List, Optional
import logging
from datetime import datetime
import json

class ModbusRTUSimulator:
    """
    Simulates a Modbus RTU PLC with configurable registers and realistic responses
    """
    
    def __init__(self, port: str = "COM3", baudrate: int = 9600, 
                 device_id: int = 1, timeout: float = 1.0):
        """
        Initialize Modbus RTU Simulator
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Communication speed
            device_id: Modbus slave address
            timeout: Response timeout
        """
        self.port = port
        self.baudrate = baudrate
        self.device_id = device_id
        self.timeout = timeout
        self.running = False
        self.serial_conn = None
        
        # Simulated PLC Memory
        self.coils = [False] * 1000  # Discrete outputs (0x01, 0x05, 0x0F)
        self.discrete_inputs = [False] * 1000  # Discrete inputs (0x02)
        self.holding_registers = [0] * 1000  # Holding registers (0x03, 0x06, 0x10)
        self.input_registers = [0] * 1000  # Input registers (0x04)
        
        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ModbusRTU_PLC_Sim")
        
        # Initialize with test data
        self._initialize_test_data()
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": None
        }
    
    def _initialize_test_data(self):
        """Initialize PLC with realistic test data for PCBA testing"""
        
        # Voltage measurements (in mV) - Registers 0-9
        self.input_registers[0] = 3300  # 3.3V rail
        self.input_registers[1] = 5000  # 5V rail  
        self.input_registers[2] = 1200  # 1.2V rail
        self.input_registers[3] = 2500  # 2.5V reference
        self.input_registers[4] = 1800  # 1.8V rail
        
        # Current measurements (in mA) - Registers 10-19
        self.input_registers[10] = 150  # Total current
        self.input_registers[11] = 50   # Digital section current
        self.input_registers[12] = 100  # Analog section current
        
        # Temperature readings (in 0.1°C) - Registers 20-29
        self.input_registers[20] = 250  # 25.0°C ambient
        self.input_registers[21] = 350  # 35.0°C hot spot
        
        # Test status flags - Coils 0-99
        self.coils[0] = True   # System ready
        self.coils[1] = False  # Test in progress
        self.coils[2] = True   # Power good
        self.coils[3] = False  # Alarm active
        
        # Discrete inputs - Status from DUT
        self.discrete_inputs[0] = True   # DUT power on
        self.discrete_inputs[1] = False  # DUT test mode
        self.discrete_inputs[2] = True   # DUT ready
        
        # Control registers - Holding registers 0-99
        self.holding_registers[0] = 1  # Test mode (1=auto, 2=manual)
        self.holding_registers[1] = 0  # Test sequence step
        self.holding_registers[2] = 100  # Test timeout (seconds)
        
        self.logger.info("PLC simulator initialized with PCBA test data")
    
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
    
    def _verify_crc(self, frame: bytes) -> bool:
        """Verify CRC of received frame"""
        if len(frame) < 4:
            return False
        
        data = frame[:-2]
        received_crc = struct.unpack('<H', frame[-2:])[0]
        calculated_crc = self._calculate_crc(data)
        
        return received_crc == calculated_crc
    
    def _create_response(self, slave_id: int, function_code: int, data: bytes) -> bytes:
        """Create Modbus response frame with CRC"""
        frame = struct.pack('BB', slave_id, function_code) + data
        crc = self._calculate_crc(frame)
        frame += struct.pack('<H', crc)
        return frame
    
    def _create_error_response(self, slave_id: int, function_code: int, error_code: int) -> bytes:
        """Create Modbus error response"""
        error_function = function_code | 0x80
        data = struct.pack('B', error_code)
        return self._create_response(slave_id, error_function, data)
    
    def _handle_read_coils(self, start_addr: int, count: int) -> bytes:
        """Handle Read Coils (0x01)"""
        if start_addr + count > len(self.coils):
            return self._create_error_response(self.device_id, 0x01, 0x02)  # Illegal data address
        
        # Pack coils into bytes
        byte_count = (count + 7) // 8
        coil_bytes = []
        
        for byte_idx in range(byte_count):
            byte_val = 0
            for bit_idx in range(8):
                coil_idx = start_addr + byte_idx * 8 + bit_idx
                if coil_idx < start_addr + count and coil_idx < len(self.coils):
                    if self.coils[coil_idx]:
                        byte_val |= (1 << bit_idx)
            coil_bytes.append(byte_val)
        
        data = struct.pack('B', byte_count) + bytes(coil_bytes)
        return self._create_response(self.device_id, 0x01, data)
    
    def _handle_read_discrete_inputs(self, start_addr: int, count: int) -> bytes:
        """Handle Read Discrete Inputs (0x02)"""
        if start_addr + count > len(self.discrete_inputs):
            return self._create_error_response(self.device_id, 0x02, 0x02)
        
        byte_count = (count + 7) // 8
        input_bytes = []
        
        for byte_idx in range(byte_count):
            byte_val = 0
            for bit_idx in range(8):
                input_idx = start_addr + byte_idx * 8 + bit_idx
                if input_idx < start_addr + count and input_idx < len(self.discrete_inputs):
                    if self.discrete_inputs[input_idx]:
                        byte_val |= (1 << bit_idx)
            input_bytes.append(byte_val)
        
        data = struct.pack('B', byte_count) + bytes(input_bytes)
        return self._create_response(self.device_id, 0x02, data)
    
    def _handle_read_holding_registers(self, start_addr: int, count: int) -> bytes:
        """Handle Read Holding Registers (0x03)"""
        if start_addr + count > len(self.holding_registers):
            return self._create_error_response(self.device_id, 0x03, 0x02)
        
        data = struct.pack('B', count * 2)  # Byte count
        for i in range(count):
            reg_value = self.holding_registers[start_addr + i]
            data += struct.pack('>H', reg_value)  # Big-endian 16-bit
        
        return self._create_response(self.device_id, 0x03, data)
    
    def _handle_read_input_registers(self, start_addr: int, count: int) -> bytes:
        """Handle Read Input Registers (0x04)"""
        if start_addr + count > len(self.input_registers):
            return self._create_error_response(self.device_id, 0x04, 0x02)
        
        data = struct.pack('B', count * 2)  # Byte count
        for i in range(count):
            reg_value = self.input_registers[start_addr + i]
            data += struct.pack('>H', reg_value)  # Big-endian 16-bit
        
        return self._create_response(self.device_id, 0x04, data)
    
    def _handle_write_single_coil(self, addr: int, value: int) -> bytes:
        """Handle Write Single Coil (0x05)"""
        if addr >= len(self.coils):
            return self._create_error_response(self.device_id, 0x05, 0x02)
        
        # Modbus coil values: 0x0000 = OFF, 0xFF00 = ON
        if value == 0xFF00:
            self.coils[addr] = True
        elif value == 0x0000:
            self.coils[addr] = False
        else:
            return self._create_error_response(self.device_id, 0x05, 0x03)  # Illegal data value
        
        # Echo back the request
        data = struct.pack('>HH', addr, value)
        return self._create_response(self.device_id, 0x05, data)
    
    def _handle_write_single_register(self, addr: int, value: int) -> bytes:
        """Handle Write Single Register (0x06)"""
        if addr >= len(self.holding_registers):
            return self._create_error_response(self.device_id, 0x06, 0x02)
        
        self.holding_registers[addr] = value
        
        # Echo back the request
        data = struct.pack('>HH', addr, value)
        return self._create_response(self.device_id, 0x06, data)
    
    def _process_frame(self, frame: bytes) -> Optional[bytes]:
        """Process received Modbus frame and return response"""
        try:
            if len(frame) < 4:
                return None
            
            # Verify CRC
            if not self._verify_crc(frame):
                self.logger.warning("Invalid CRC received")
                self.stats["errors"] += 1
                return None
            
            # Parse frame
            slave_id = frame[0]
            function_code = frame[1]
            
            # Check if this message is for us
            if slave_id != self.device_id:
                return None
            
            self.stats["messages_received"] += 1
            
            # Process based on function code
            if function_code == 0x01:  # Read Coils
                start_addr, count = struct.unpack('>HH', frame[2:6])
                response = self._handle_read_coils(start_addr, count)
                
            elif function_code == 0x02:  # Read Discrete Inputs
                start_addr, count = struct.unpack('>HH', frame[2:6])
                response = self._handle_read_discrete_inputs(start_addr, count)
                
            elif function_code == 0x03:  # Read Holding Registers
                start_addr, count = struct.unpack('>HH', frame[2:6])
                response = self._handle_read_holding_registers(start_addr, count)
                
            elif function_code == 0x04:  # Read Input Registers
                start_addr, count = struct.unpack('>HH', frame[2:6])
                response = self._handle_read_input_registers(start_addr, count)
                
            elif function_code == 0x05:  # Write Single Coil
                addr, value = struct.unpack('>HH', frame[2:6])
                response = self._handle_write_single_coil(addr, value)
                
            elif function_code == 0x06:  # Write Single Register
                addr, value = struct.unpack('>HH', frame[2:6])
                response = self._handle_write_single_register(addr, value)
                
            else:
                # Unsupported function code
                response = self._create_error_response(self.device_id, function_code, 0x01)
            
            self.stats["messages_sent"] += 1
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            self.stats["errors"] += 1
            return None
    
    def _simulate_dynamic_data(self):
        """Simulate changing data like a real PLC"""
        while self.running:
            try:
                # Simulate voltage fluctuations (±2%)
                base_voltages = [3300, 5000, 1200, 2500, 1800]
                for i, base_voltage in enumerate(base_voltages):
                    variation = int(base_voltage * 0.02 * (0.5 - time.time() % 1))
                    self.input_registers[i] = base_voltage + variation
                
                # Simulate current changes
                base_current = 150
                current_variation = int(20 * (0.5 - (time.time() % 2) / 2))
                self.input_registers[10] = base_current + current_variation
                
                # Simulate temperature rise
                ambient_temp = 250 + int(10 * (time.time() % 60) / 60)  # Slowly rising
                self.input_registers[20] = ambient_temp
                
                # Toggle test status periodically
                if int(time.time()) % 10 == 0:
                    self.coils[1] = not self.coils[1]  # Test in progress
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in dynamic simulation: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the Modbus RTU simulator"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            self.running = True
            self.stats["start_time"] = datetime.now()
            
            # Start dynamic data simulation thread
            sim_thread = threading.Thread(target=self._simulate_dynamic_data)
            sim_thread.daemon = True
            sim_thread.start()
            
            self.logger.info(f"Modbus RTU PLC Simulator started on {self.port} at {self.baudrate} baud")
            self.logger.info(f"Device ID: {self.device_id}")
            self.logger.info("Simulating PCBA test equipment...")
            
            # Main communication loop
            while self.running:
                try:
                    # Read data from serial port
                    if self.serial_conn.in_waiting > 0:
                        frame = b""
                        start_time = time.time()
                        
                        # Read frame with timeout
                        while time.time() - start_time < self.timeout:
                            if self.serial_conn.in_waiting > 0:
                                frame += self.serial_conn.read(self.serial_conn.in_waiting)
                                time.sleep(0.01)  # Small delay to collect complete frame
                            else:
                                if len(frame) > 0:
                                    break
                                time.sleep(0.01)
                        
                        if frame:
                            self.logger.debug(f"Received: {frame.hex()}")
                            
                            # Process frame and send response
                            response = self._process_frame(frame)
                            if response:
                                self.serial_conn.write(response)
                                self.logger.debug(f"Sent: {response.hex()}")
                    
                    time.sleep(0.001)  # Small delay to prevent CPU overload
                    
                except serial.SerialException as e:
                    self.logger.error(f"Serial communication error: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Failed to start simulator: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.logger.info("Modbus RTU PLC Simulator stopped")
        self._print_statistics()
    
    def _print_statistics(self):
        """Print communication statistics"""
        if self.stats["start_time"]:
            duration = datetime.now() - self.stats["start_time"]
            self.logger.info(f"\nSimulator Statistics:")
            self.logger.info(f"  Runtime: {duration}")
            self.logger.info(f"  Messages received: {self.stats['messages_received']}")
            self.logger.info(f"  Messages sent: {self.stats['messages_sent']}")
            self.logger.info(f"  Errors: {self.stats['errors']}")
    
    def get_status(self) -> Dict:
        """Get current simulator status"""
        return {
            "running": self.running,
            "port": self.port,
            "baudrate": self.baudrate,
            "device_id": self.device_id,
            "stats": self.stats,
            "sample_data": {
                "voltages": {
                    "3V3_rail": self.input_registers[0],
                    "5V_rail": self.input_registers[1],
                    "1V2_rail": self.input_registers[2]
                },
                "currents": {
                    "total_current": self.input_registers[10],
                    "digital_current": self.input_registers[11]
                },
                "temperatures": {
                    "ambient": self.input_registers[20] / 10.0,
                    "hotspot": self.input_registers[21] / 10.0
                },
                "status": {
                    "system_ready": self.coils[0],
                    "test_in_progress": self.coils[1],
                    "power_good": self.coils[2]
                }
            }
        }

def main():
    """Main function for running the simulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Modbus RTU PLC Simulator for PCBA Testing")
    parser.add_argument("--port", default="COM3", help="Serial port (default: COM3)")
    parser.add_argument("--baudrate", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--device-id", type=int, default=1, help="Modbus device ID (default: 1)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Response timeout (default: 1.0)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start simulator
    simulator = ModbusRTUSimulator(
        port=args.port,
        baudrate=args.baudrate,
        device_id=args.device_id,
        timeout=args.timeout
    )
    
    try:
        simulator.start()
    except KeyboardInterrupt:
        print("\nShutting down simulator...")
        simulator.stop()

if __name__ == "__main__":
    main()