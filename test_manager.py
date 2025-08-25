"""
PCBA Test System - Test Manager
This module provides high-level test management and execution capabilities.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging

from hardware_layer import (
    HardwareManager, TestEquipment, TestMeasurement, TestResult,
    Multimeter, PowerSupply, ConnectionConfig, ConnectionType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStepType(Enum):
    """Types of test steps"""
    SETUP = "setup"
    MEASUREMENT = "measurement"
    VERIFICATION = "verification"
    CLEANUP = "cleanup"

class TestStepStatus(Enum):
    """Status of test steps"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TestStep:
    """Individual test step definition"""
    
    def __init__(self, name: str, step_type: TestStepType, equipment_name: str, 
                 action: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.step_type = step_type
        self.equipment_name = equipment_name
        self.action = action
        self.parameters = parameters or {}
        self.status = TestStepStatus.PENDING
        self.result = None
        self.error_message = None
        self.execution_time = 0.0
        self.measurements: List[TestMeasurement] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary"""
        return {
            'name': self.name,
            'step_type': self.step_type.value,
            'equipment_name': self.equipment_name,
            'action': self.action,
            'parameters': self.parameters,
            'status': self.status.value,
            'result': self.result.value if self.result else None,
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'measurements': [m.__dict__ for m in self.measurements] if self.measurements else []
        }

class TestSequence:
    """Test sequence containing multiple test steps"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[TestStep] = []
        self.total_steps = 0
        self.completed_steps = 0
        self.failed_steps = 0
        self.start_time = None
        self.end_time = None
        
    def add_step(self, step: TestStep):
        """Add a test step to the sequence"""
        self.steps.append(step)
        self.total_steps = len(self.steps)
        
    def get_progress(self) -> float:
        """Get test progress percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert sequence to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'progress': self.get_progress(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'steps': [step.to_dict() for step in self.steps]
        }

class TestExecutionEngine:
    """Engine for executing test sequences"""
    
    def __init__(self, hardware_manager: HardwareManager):
        self.hardware_manager = hardware_manager
        self.current_sequence = None
        self.is_running = False
        self.stop_requested = False
        self.execution_thread = None
        self.progress_callback: Optional[Callable] = None
        self.step_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """Set callback for progress updates"""
        self.progress_callback = callback
        
    def set_step_callback(self, callback: Callable[[TestStep], None]):
        """Set callback for step completion"""
        self.step_callback = callback
    
    def execute_sequence(self, sequence: TestSequence) -> bool:
        """Execute a test sequence"""
        if self.is_running:
            logger.warning("Test execution already in progress")
            return False
            
        self.current_sequence = sequence
        self.is_running = True
        self.stop_requested = False
        
        # Start execution in separate thread
        self.execution_thread = threading.Thread(target=self._execute_sequence_thread)
        self.execution_thread.start()
        
        return True
    
    def stop_execution(self):
        """Request to stop current test execution"""
        self.stop_requested = True
        logger.info("Test execution stop requested")
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for test execution to complete"""
        if self.execution_thread:
            self.execution_thread.join(timeout)
            return not self.execution_thread.is_alive()
        return True
    
    def _execute_sequence_thread(self):
        """Execute test sequence in separate thread"""
        sequence = self.current_sequence
        sequence.start_time = datetime.now()
        
        try:
            logger.info(f"Starting test sequence: {sequence.name}")
            
            for i, step in enumerate(sequence.steps):
                if self.stop_requested:
                    logger.info("Test execution stopped by user request")
                    break
                
                # Execute step
                self._execute_step(step)
                
                # Update progress
                if step.status == TestStepStatus.COMPLETED:
                    sequence.completed_steps += 1
                elif step.status == TestStepStatus.FAILED:
                    sequence.failed_steps += 1
                    
                # Call callbacks
                if self.progress_callback:
                    self.progress_callback(sequence.get_progress(), step.name)
                if self.step_callback:
                    self.step_callback(step)
                
                # Check if we should continue on failure
                if step.status == TestStepStatus.FAILED and step.step_type != TestStepType.CLEANUP:
                    logger.error(f"Test step failed: {step.name}")
                    # Continue with remaining steps for now
                    
        except Exception as e:
            logger.error(f"Test sequence execution error: {e}")
        finally:
            sequence.end_time = datetime.now()
            self.is_running = False
            logger.info(f"Test sequence completed: {sequence.name}")
    
    def _execute_step(self, step: TestStep):
        """Execute a single test step"""
        step.status = TestStepStatus.RUNNING
        start_time = time.time()
        
        try:
            logger.info(f"Executing step: {step.name}")
            
            # Get equipment
            equipment = self.hardware_manager.get_equipment(step.equipment_name)
            if not equipment:
                raise Exception(f"Equipment not found: {step.equipment_name}")
            
            if not equipment.is_connected():
                raise Exception(f"Equipment not connected: {step.equipment_name}")
            
            # Execute action based on step type and action
            self._execute_action(step, equipment)
            
            step.status = TestStepStatus.COMPLETED
            step.result = TestResult.PASS
            
        except Exception as e:
            step.status = TestStepStatus.FAILED
            step.result = TestResult.FAIL
            step.error_message = str(e)
            logger.error(f"Step execution failed: {step.name} - {e}")
        finally:
            step.execution_time = time.time() - start_time
    
    def _execute_action(self, step: TestStep, equipment: TestEquipment):
        """Execute specific action on equipment"""
        action = step.action.lower()
        params = step.parameters
        
        if isinstance(equipment, Multimeter):
            self._execute_multimeter_action(step, equipment, action, params)
        elif isinstance(equipment, PowerSupply):
            self._execute_power_supply_action(step, equipment, action, params)
        else:
            # Generic equipment actions
            if action == "reset":
                equipment.reset()
            elif action == "self_test":
                result = equipment.self_test()
                if not result:
                    raise Exception("Equipment self-test failed")
            else:
                raise Exception(f"Unknown action: {action}")
    
    def _execute_multimeter_action(self, step: TestStep, dmm: Multimeter, action: str, params: Dict):
        """Execute multimeter-specific actions"""
        if action == "measure_voltage_dc":
            range_val = params.get('range')
            measurement = dmm.measure_voltage_dc(range_val)
            step.measurements.append(measurement)
            
            # Check limits if specified
            min_limit = params.get('min_limit')
            max_limit = params.get('max_limit')
            if min_limit is not None:
                measurement.min_limit = min_limit
            if max_limit is not None:
                measurement.max_limit = max_limit
            
            if not measurement.is_within_limits():
                raise Exception(f"Measurement out of limits: {measurement.value} {measurement.unit}")
                
        elif action == "measure_current_dc":
            range_val = params.get('range')
            measurement = dmm.measure_current_dc(range_val)
            step.measurements.append(measurement)
            
            # Check limits
            min_limit = params.get('min_limit')
            max_limit = params.get('max_limit')
            if min_limit is not None:
                measurement.min_limit = min_limit
            if max_limit is not None:
                measurement.max_limit = max_limit
            
            if not measurement.is_within_limits():
                raise Exception(f"Measurement out of limits: {measurement.value} {measurement.unit}")
                
        elif action == "measure_resistance":
            range_val = params.get('range')
            measurement = dmm.measure_resistance(range_val)
            step.measurements.append(measurement)
            
            # Check limits
            min_limit = params.get('min_limit')
            max_limit = params.get('max_limit')
            if min_limit is not None:
                measurement.min_limit = min_limit
            if max_limit is not None:
                measurement.max_limit = max_limit
            
            if not measurement.is_within_limits():
                raise Exception(f"Measurement out of limits: {measurement.value} {measurement.unit}")
        else:
            raise Exception(f"Unknown multimeter action: {action}")
    
    def _execute_power_supply_action(self, step: TestStep, psu: PowerSupply, action: str, params: Dict):
        """Execute power supply-specific actions"""
        if action == "set_voltage":
            voltage = params.get('voltage')
            if voltage is None:
                raise Exception("Voltage parameter required")
            if not psu.set_voltage(voltage):
                raise Exception("Failed to set voltage")
                
        elif action == "set_current_limit":
            current = params.get('current')
            if current is None:
                raise Exception("Current parameter required")
            if not psu.set_current_limit(current):
                raise Exception("Failed to set current limit")
                
        elif action == "enable_output":
            enable = params.get('enable', True)
            if not psu.enable_output(enable):
                raise Exception("Failed to enable/disable output")
                
        elif action == "measure_output_voltage":
            measurement = psu.measure_output_voltage()
            step.measurements.append(measurement)
            
        elif action == "measure_output_current":
            measurement = psu.measure_output_current()
            step.measurements.append(measurement)
        else:
            raise Exception(f"Unknown power supply action: {action}")

class TestSequenceBuilder:
    """Builder for creating test sequences"""
    
    def __init__(self, name: str, description: str = ""):
        self.sequence = TestSequence(name, description)
    
    def add_setup_step(self, name: str, equipment: str, action: str, **params) -> 'TestSequenceBuilder':
        """Add a setup step"""
        step = TestStep(name, TestStepType.SETUP, equipment, action, params)
        self.sequence.add_step(step)
        return self
    
    def add_measurement_step(self, name: str, equipment: str, action: str, **params) -> 'TestSequenceBuilder':
        """Add a measurement step"""
        step = TestStep(name, TestStepType.MEASUREMENT, equipment, action, params)
        self.sequence.add_step(step)
        return self
    
    def add_verification_step(self, name: str, equipment: str, action: str, **params) -> 'TestSequenceBuilder':
        """Add a verification step"""
        step = TestStep(name, TestStepType.VERIFICATION, equipment, action, params)
        self.sequence.add_step(step)
        return self
    
    def add_cleanup_step(self, name: str, equipment: str, action: str, **params) -> 'TestSequenceBuilder':
        """Add a cleanup step"""
        step = TestStep(name, TestStepType.CLEANUP, equipment, action, params)
        self.sequence.add_step(step)
        return self
    
    def build(self) -> TestSequence:
        """Build and return the test sequence"""
        return self.sequence

class TestManager:
    """High-level test manager"""
    
    def __init__(self):
        self.hardware_manager = HardwareManager()
        self.execution_engine = TestExecutionEngine(self.hardware_manager)
        self.test_templates: Dict[str, TestSequence] = {}
        self.active_tests: Dict[str, TestSequence] = {}
        
    def setup_hardware(self, config_list: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Setup hardware from configuration"""
        results = {}
        
        for config in config_list:
            try:
                # Create connection config
                conn_config = ConnectionConfig(
                    connection_type=ConnectionType(config['connection_type']),
                    address=config['address'],
                    port=config.get('port'),
                    baud_rate=config.get('baud_rate', 9600),
                    timeout=config.get('timeout', 5.0)
                )
                
                # Create hardware interface
                if conn_config.connection_type == ConnectionType.SERIAL_RTU:
                    from hardware_layer import SerialInterface
                    interface = SerialInterface(conn_config)
                elif conn_config.connection_type == ConnectionType.TCP_IP:
                    from hardware_layer import TCPInterface
                    interface = TCPInterface(conn_config)
                else:
                    raise Exception(f"Unsupported connection type: {conn_config.connection_type}")
                
                # Create equipment
                equipment_type = config['equipment_type']
                name = config['name']
                
                if equipment_type == 'multimeter':
                    equipment = Multimeter(name, interface)
                elif equipment_type == 'power_supply':
                    equipment = PowerSupply(name, interface)
                else:
                    raise Exception(f"Unsupported equipment type: {equipment_type}")
                
                # Add to hardware manager
                success = self.hardware_manager.add_equipment(equipment)
                results[name] = success
                
            except Exception as e:
                logger.error(f"Failed to setup hardware {config.get('name', 'unknown')}: {e}")
                results[config.get('name', 'unknown')] = False
        
        return results
    
    def connect_all_hardware(self) -> Dict[str, bool]:
        """Connect to all configured hardware"""
        return self.hardware_manager.connect_all()
    
    def disconnect_all_hardware(self) -> Dict[str, bool]:
        """Disconnect from all hardware"""
        return self.hardware_manager.disconnect_all()
    
    def create_voltage_test_sequence(self, name: str, voltage_points: List[Dict]) -> TestSequence:
        """Create a voltage measurement test sequence"""
        builder = TestSequenceBuilder(name, "Voltage measurement test sequence")
        
        # Setup steps
        builder.add_setup_step("Reset DMM", "dmm", "reset")
        builder.add_setup_step("Setup Power Supply", "psu", "set_voltage", voltage=0.0)
        builder.add_setup_step("Enable Power Supply", "psu", "enable_output", enable=True)
        
        # Measurement steps for each voltage point
        for i, point in enumerate(voltage_points):
            voltage = point['voltage']
            min_limit = point.get('min_limit')
            max_limit = point.get('max_limit')
            
            builder.add_setup_step(f"Set Voltage {voltage}V", "psu", "set_voltage", voltage=voltage)
            builder.add_measurement_step(
                f"Measure Voltage {voltage}V", "dmm", "measure_voltage_dc",
                min_limit=min_limit, max_limit=max_limit
            )
        
        # Cleanup steps
        builder.add_cleanup_step("Disable Power Supply", "psu", "enable_output", enable=False)
        builder.add_cleanup_step("Reset Power Supply", "psu", "reset")
        
        return builder.build()
    
    def create_current_test_sequence(self, name: str, current_points: List[Dict]) -> TestSequence:
        """Create a current measurement test sequence"""
        builder = TestSequenceBuilder(name, "Current measurement test sequence")
        
        # Setup steps
        builder.add_setup_step("Reset DMM", "dmm", "reset")
        builder.add_setup_step("Setup Power Supply", "psu", "set_voltage", voltage=5.0)
        builder.add_setup_step("Enable Power Supply", "psu", "enable_output", enable=True)
        
        # Measurement steps for each current point
        for i, point in enumerate(current_points):
            current_limit = point['current_limit']
            min_limit = point.get('min_limit')
            max_limit = point.get('max_limit')
            
            builder.add_setup_step(f"Set Current Limit {current_limit}A", "psu", "set_current_limit", current=current_limit)
            builder.add_measurement_step(
                f"Measure Current {current_limit}A", "dmm", "measure_current_dc",
                min_limit=min_limit, max_limit=max_limit
            )
        
        # Cleanup steps
        builder.add_cleanup_step("Disable Power Supply", "psu", "enable_output", enable=False)
        builder.add_cleanup_step("Reset Power Supply", "psu", "reset")
        
        return builder.build()
    
    def execute_test(self, sequence: TestSequence, test_id: str) -> bool:
        """Execute a test sequence"""
        if test_id in self.active_tests:
            logger.warning(f"Test {test_id} already active")
            return False
        
        self.active_tests[test_id] = sequence
        success = self.execution_engine.execute_sequence(sequence)
        
        if not success:
            del self.active_tests[test_id]
        
        return success
    
    def stop_test(self, test_id: str) -> bool:
        """Stop a running test"""
        if test_id not in self.active_tests:
            return False
        
        self.execution_engine.stop_execution()
        return True
    
    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a running test"""
        if test_id not in self.active_tests:
            return None
        
        sequence = self.active_tests[test_id]
        return sequence.to_dict()
    
    def get_connected_equipment(self) -> List[str]:
        """Get list of connected equipment names"""
        connected = self.hardware_manager.get_connected_equipment()
        return [eq.name for eq in connected]
    
    def perform_equipment_health_check(self) -> Dict[str, bool]:
        """Perform health check on all equipment"""
        return self.hardware_manager.perform_system_check()