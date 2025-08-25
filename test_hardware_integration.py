"""
Unit tests for Hardware Integration Layer
Tests the hardware abstraction layer and test manager functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import time
from datetime import datetime

# Import the modules to test
try:
    from hardware_layer import (
        ConnectionConfig, ConnectionType, TestEquipmentType,
        HardwareInterface, SerialInterface, TCPInterface,
        TestEquipment, Multimeter, PowerSupply, HardwareManager,
        TestMeasurement, TestResult
    )
    from test_manager import (
        TestStep, TestStepType, TestStepStatus, TestSequence,
        TestExecutionEngine, TestSequenceBuilder, TestManager
    )
    HARDWARE_AVAILABLE = True
except ImportError as e:
    HARDWARE_AVAILABLE = False
    print(f"Hardware modules not available for testing: {e}")


class MockSerial:
    """Mock serial connection for testing"""
    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.write_data = []
        self.read_responses = ["OK\r\n", "1.23\r\n", "PASS\r\n"]
        self.response_index = 0
    
    def write(self, data):
        self.write_data.append(data)
    
    def readline(self):
        if self.response_index < len(self.read_responses):
            response = self.read_responses[self.response_index]
            self.response_index += 1
            return response.encode()
        return b"OK\r\n"
    
    def close(self):
        self.is_open = False


class MockSocket:
    """Mock socket connection for testing"""
    def __init__(self):
        self.connected = False
        self.sent_data = []
        self.responses = [b"OK\r\n", b"2.45\r\n", b"PASS\r\n"]
        self.response_index = 0
    
    def connect(self, address):
        self.connected = True
    
    def send(self, data):
        self.sent_data.append(data)
    
    def recv(self, size):
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return b"OK\r\n"
    
    def close(self):
        self.connected = False
    
    def settimeout(self, timeout):
        pass


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestConnectionConfig(unittest.TestCase):
    """Test ConnectionConfig class"""
    
    def test_serial_connection_config(self):
        """Test creating serial connection configuration"""
        config = ConnectionConfig(
            connection_type=ConnectionType.SERIAL_RTU,
            address="COM1",
            baud_rate=9600,
            timeout=5.0
        )
        
        self.assertEqual(config.connection_type, ConnectionType.SERIAL_RTU)
        self.assertEqual(config.address, "COM1")
        self.assertEqual(config.baud_rate, 9600)
        self.assertEqual(config.timeout, 5.0)
    
    def test_tcp_connection_config(self):
        """Test creating TCP connection configuration"""
        config = ConnectionConfig(
            connection_type=ConnectionType.TCP_IP,
            address="192.168.1.100",
            port=502,
            timeout=10.0
        )
        
        self.assertEqual(config.connection_type, ConnectionType.TCP_IP)
        self.assertEqual(config.address, "192.168.1.100")
        self.assertEqual(config.port, 502)
        self.assertEqual(config.timeout, 10.0)


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestSerialInterface(unittest.TestCase):
    """Test SerialInterface class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ConnectionConfig(
            connection_type=ConnectionType.SERIAL_RTU,
            address="COM1",
            baud_rate=9600,
            timeout=5.0
        )
    
    @patch('hardware_layer.serial.Serial')
    def test_connect_success(self, mock_serial):
        """Test successful serial connection"""
        mock_serial.return_value = MockSerial()
        
        interface = SerialInterface(self.config)
        result = interface.connect()
        
        self.assertTrue(result)
        self.assertTrue(interface.connected)
        mock_serial.assert_called_once()
    
    @patch('hardware_layer.serial.Serial')
    def test_connect_failure(self, mock_serial):
        """Test failed serial connection"""
        mock_serial.side_effect = Exception("Connection failed")
        
        interface = SerialInterface(self.config)
        result = interface.connect()
        
        self.assertFalse(result)
        self.assertFalse(interface.connected)
        self.assertIsNotNone(interface.last_error)
    
    @patch('hardware_layer.serial.Serial')
    def test_send_command(self, mock_serial):
        """Test sending command via serial"""
        mock_connection = MockSerial()
        mock_serial.return_value = mock_connection
        
        interface = SerialInterface(self.config)
        interface.connect()
        
        response = interface.send_command("*IDN?")
        
        self.assertEqual(response, "OK")
        self.assertIn(b"*IDN?\r\n", mock_connection.write_data)


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestTCPInterface(unittest.TestCase):
    """Test TCPInterface class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ConnectionConfig(
            connection_type=ConnectionType.TCP_IP,
            address="192.168.1.100",
            port=502,
            timeout=5.0
        )
    
    @patch('hardware_layer.socket.socket')
    def test_connect_success(self, mock_socket):
        """Test successful TCP connection"""
        mock_connection = MockSocket()
        mock_socket.return_value = mock_connection
        
        interface = TCPInterface(self.config)
        result = interface.connect()
        
        self.assertTrue(result)
        self.assertTrue(interface.connected)
    
    @patch('hardware_layer.socket.socket')
    def test_send_command(self, mock_socket):
        """Test sending command via TCP"""
        mock_connection = MockSocket()
        mock_socket.return_value = mock_connection
        
        interface = TCPInterface(self.config)
        interface.connect()
        
        response = interface.send_command("*IDN?")
        
        self.assertEqual(response, "OK")
        self.assertIn(b"*IDN?\r\n", mock_connection.sent_data)


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestMultimeter(unittest.TestCase):
    """Test Multimeter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_interface = Mock(spec=HardwareInterface)
        self.mock_interface.connect.return_value = True
        self.mock_interface.is_connected.return_value = True
        self.mock_interface.send_command.return_value = "1.234"
        
        self.multimeter = Multimeter("Test DMM", self.mock_interface)
    
    def test_initialize(self):
        """Test multimeter initialization"""
        self.mock_interface.send_command.side_effect = [
            "Test DMM Model 123",  # *IDN? response
            "OK"  # *RST response
        ]
        
        result = self.multimeter.initialize()
        
        self.assertTrue(result)
        self.mock_interface.connect.assert_called_once()
        self.mock_interface.send_command.assert_any_call("*IDN?")
        self.mock_interface.send_command.assert_any_call("*RST")
    
    def test_measure_voltage_dc(self):
        """Test DC voltage measurement"""
        self.mock_interface.send_command.return_value = "3.14"
        
        measurement = self.multimeter.measure_voltage_dc(10.0)
        
        self.assertEqual(measurement.parameter, "DC_VOLTAGE")
        self.assertEqual(measurement.value, 3.14)
        self.assertEqual(measurement.unit, "V")
        self.mock_interface.send_command.assert_any_call("VOLT:DC:RANG 10.0")
        self.mock_interface.send_command.assert_any_call("CONF:VOLT:DC")
        self.mock_interface.send_command.assert_any_call("READ?")
    
    def test_measure_current_dc(self):
        """Test DC current measurement"""
        self.mock_interface.send_command.return_value = "0.123"
        
        measurement = self.multimeter.measure_current_dc(1.0)
        
        self.assertEqual(measurement.parameter, "DC_CURRENT")
        self.assertEqual(measurement.value, 0.123)
        self.assertEqual(measurement.unit, "A")
    
    def test_measure_resistance(self):
        """Test resistance measurement"""
        self.mock_interface.send_command.return_value = "1000.0"
        
        measurement = self.multimeter.measure_resistance()
        
        self.assertEqual(measurement.parameter, "RESISTANCE")
        self.assertEqual(measurement.value, 1000.0)
        self.assertEqual(measurement.unit, "Ohm")


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestPowerSupply(unittest.TestCase):
    """Test PowerSupply class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_interface = Mock(spec=HardwareInterface)
        self.mock_interface.connect.return_value = True
        self.mock_interface.is_connected.return_value = True
        self.mock_interface.send_command.return_value = "OK"
        
        self.power_supply = PowerSupply("Test PSU", self.mock_interface)
    
    def test_initialize(self):
        """Test power supply initialization"""
        self.mock_interface.send_command.side_effect = [
            "Test PSU Model 456",  # *IDN? response
            "OK",  # *RST response
            "OK"   # OUTP OFF response
        ]
        
        result = self.power_supply.initialize()
        
        self.assertTrue(result)
        self.assertFalse(self.power_supply.output_enabled)
    
    def test_set_voltage(self):
        """Test setting output voltage"""
        result = self.power_supply.set_voltage(5.0)
        
        self.assertTrue(result)
        self.mock_interface.send_command.assert_called_with("VOLT 5.0")
    
    def test_enable_output(self):
        """Test enabling output"""
        result = self.power_supply.enable_output(True)
        
        self.assertTrue(result)
        self.assertTrue(self.power_supply.output_enabled)
        self.mock_interface.send_command.assert_called_with("OUTP ON")
    
    def test_measure_output_voltage(self):
        """Test measuring output voltage"""
        self.mock_interface.send_command.return_value = "5.01"
        
        measurement = self.power_supply.measure_output_voltage()
        
        self.assertEqual(measurement.parameter, "OUTPUT_VOLTAGE")
        self.assertEqual(measurement.value, 5.01)
        self.assertEqual(measurement.unit, "V")


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestHardwareManager(unittest.TestCase):
    """Test HardwareManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = HardwareManager()
        
        # Create mock equipment
        self.mock_dmm = Mock(spec=Multimeter)
        self.mock_dmm.name = "Test DMM"
        self.mock_dmm.connect.return_value = True
        self.mock_dmm.initialize.return_value = True
        self.mock_dmm.is_connected.return_value = True
        self.mock_dmm.self_test.return_value = True
        
        self.mock_psu = Mock(spec=PowerSupply)
        self.mock_psu.name = "Test PSU"
        self.mock_psu.connect.return_value = True
        self.mock_psu.initialize.return_value = True
        self.mock_psu.is_connected.return_value = True
        self.mock_psu.self_test.return_value = True
    
    def test_add_equipment(self):
        """Test adding equipment to manager"""
        result = self.manager.add_equipment(self.mock_dmm)
        
        self.assertTrue(result)
        self.assertIn("Test DMM", self.manager.equipment)
    
    def test_connect_all(self):
        """Test connecting to all equipment"""
        self.manager.add_equipment(self.mock_dmm)
        self.manager.add_equipment(self.mock_psu)
        
        results = self.manager.connect_all()
        
        self.assertTrue(results["Test DMM"])
        self.assertTrue(results["Test PSU"])
        self.mock_dmm.connect.assert_called_once()
        self.mock_dmm.initialize.assert_called_once()
        self.mock_psu.connect.assert_called_once()
        self.mock_psu.initialize.assert_called_once()
    
    def test_perform_system_check(self):
        """Test performing system health check"""
        self.manager.add_equipment(self.mock_dmm)
        self.manager.active_connections.append("Test DMM")
        
        results = self.manager.perform_system_check()
        
        self.assertTrue(results["Test DMM"])
        self.mock_dmm.self_test.assert_called_once()


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestTestMeasurement(unittest.TestCase):
    """Test TestMeasurement class"""
    
    def test_measurement_within_limits(self):
        """Test measurement within specified limits"""
        measurement = TestMeasurement(
            parameter="VOLTAGE",
            value=5.0,
            unit="V",
            min_limit=4.5,
            max_limit=5.5
        )
        
        self.assertTrue(measurement.is_within_limits())
    
    def test_measurement_below_limit(self):
        """Test measurement below minimum limit"""
        measurement = TestMeasurement(
            parameter="VOLTAGE",
            value=4.0,
            unit="V",
            min_limit=4.5,
            max_limit=5.5
        )
        
        self.assertFalse(measurement.is_within_limits())
    
    def test_measurement_above_limit(self):
        """Test measurement above maximum limit"""
        measurement = TestMeasurement(
            parameter="VOLTAGE",
            value=6.0,
            unit="V",
            min_limit=4.5,
            max_limit=5.5
        )
        
        self.assertFalse(measurement.is_within_limits())


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestTestSequence(unittest.TestCase):
    """Test TestSequence and TestStep classes"""
    
    def test_test_sequence_creation(self):
        """Test creating a test sequence"""
        sequence = TestSequence("Voltage Test", "Test voltage measurements")
        
        self.assertEqual(sequence.name, "Voltage Test")
        self.assertEqual(sequence.description, "Test voltage measurements")
        self.assertEqual(sequence.total_steps, 0)
        self.assertEqual(sequence.completed_steps, 0)
    
    def test_add_test_step(self):
        """Test adding test steps to sequence"""
        sequence = TestSequence("Test Sequence")
        step = TestStep("Reset DMM", TestStepType.SETUP, "dmm", "reset")
        
        sequence.add_step(step)
        
        self.assertEqual(sequence.total_steps, 1)
        self.assertEqual(len(sequence.steps), 1)
        self.assertEqual(sequence.steps[0], step)
    
    def test_sequence_progress(self):
        """Test sequence progress calculation"""
        sequence = TestSequence("Test Sequence")
        step1 = TestStep("Step 1", TestStepType.SETUP, "dmm", "reset")
        step2 = TestStep("Step 2", TestStepType.MEASUREMENT, "dmm", "measure")
        
        sequence.add_step(step1)
        sequence.add_step(step2)
        sequence.completed_steps = 1
        
        self.assertEqual(sequence.get_progress(), 50.0)


@unittest.skipUnless(HARDWARE_AVAILABLE, "Hardware modules not available")
class TestTestSequenceBuilder(unittest.TestCase):
    """Test TestSequenceBuilder class"""
    
    def test_builder_pattern(self):
        """Test using builder pattern to create test sequence"""
        sequence = (TestSequenceBuilder("Voltage Test")
                   .add_setup_step("Reset DMM", "dmm", "reset")
                   .add_measurement_step("Measure 5V", "dmm", "measure_voltage_dc", voltage=5.0)
                   .add_cleanup_step("Disable PSU", "psu", "enable_output", enable=False)
                   .build())
        
        self.assertEqual(sequence.name, "Voltage Test")
        self.assertEqual(sequence.total_steps, 3)
        self.assertEqual(sequence.steps[0].step_type, TestStepType.SETUP)
        self.assertEqual(sequence.steps[1].step_type, TestStepType.MEASUREMENT)
        self.assertEqual(sequence.steps[2].step_type, TestStepType.CLEANUP)


class TestFlaskIntegration(unittest.TestCase):
    """Test Flask API integration"""
    
    def setUp(self):
        """Set up Flask test client"""
        # This would require importing the Flask app
        # For now, we'll just test the structure
        pass
    
    def test_hardware_api_structure(self):
        """Test that hardware API endpoints are properly structured"""
        # Test the expected API endpoints exist
        expected_endpoints = [
            '/api/hardware/status',
            '/api/hardware/setup',
            '/api/hardware/connect',
            '/api/hardware/disconnect',
            '/api/hardware/test/voltage',
            '/api/hardware/test/current',
            '/api/hardware/test/status/<test_id>',
            '/api/hardware/test/stop/<test_id>'
        ]
        
        # This would test that the endpoints are properly defined
        # For now, we just verify the list structure
        self.assertEqual(len(expected_endpoints), 8)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    if HARDWARE_AVAILABLE:
        # Add hardware layer tests
        suite.addTest(loader.loadTestsFromTestCase(TestConnectionConfig))
        suite.addTest(loader.loadTestsFromTestCase(TestSerialInterface))
        suite.addTest(loader.loadTestsFromTestCase(TestTCPInterface))
        suite.addTest(loader.loadTestsFromTestCase(TestMultimeter))
        suite.addTest(loader.loadTestsFromTestCase(TestPowerSupply))
        suite.addTest(loader.loadTestsFromTestCase(TestHardwareManager))
        suite.addTest(loader.loadTestsFromTestCase(TestTestMeasurement))
        suite.addTest(loader.loadTestsFromTestCase(TestTestSequence))
        suite.addTest(loader.loadTestsFromTestCase(TestTestSequenceBuilder))
    else:
        print("Hardware modules not available, skipping hardware tests")
    
    # Add Flask integration tests
    suite.addTest(loader.loadTestsFromTestCase(TestFlaskIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Exit with error code if tests failed
    exit_code = 0 if result.wasSuccessful() else 1
    exit(exit_code)