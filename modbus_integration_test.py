#!/usr/bin/env python3
"""
Modbus RTU Integration Test Suite
Demonstrates complete simulation setup for PCBA Test System
"""

import time
import threading
import subprocess
import sys
import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import json

# Import our custom modules
from modbus_plc_simulator import ModbusRTUSimulator
from modbus_test_client import ModbusRTUTestClient
from virtual_serial_port_manager import VirtualSerialPortManager

class ModbusIntegrationTestSuite:
    """
    Complete integration test suite for Modbus RTU simulation
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ModbusIntegration")
        self.virtual_port_manager = VirtualSerialPortManager()
        self.plc_simulator = None
        self.test_client = None
        self.simulator_thread = None
        self.virtual_ports = None
        
        # Test configuration
        self.config = {
            "baudrate": 9600,
            "device_id": 1,
            "timeout": 2.0,
            "test_duration": 30,  # seconds
            "simulator_port": None,
            "client_port": None
        }
    
    def setup_virtual_ports(self) -> bool:
        """Setup virtual serial port pair"""
        self.logger.info("🔌 Setting up virtual serial ports...")
        
        # Check prerequisites
        if not self.virtual_port_manager.check_prerequisites():
            self.logger.warning("Virtual port prerequisites not met")
            # Try manual setup
            return self._setup_manual_ports()
        
        # Create virtual port pair
        self.virtual_ports = self.virtual_port_manager.create_virtual_port_pair()
        
        if self.virtual_ports:
            self.config["simulator_port"] = self.virtual_ports[0]
            self.config["client_port"] = self.virtual_ports[1]
            self.logger.info(f"✅ Virtual ports created: {self.virtual_ports[0]} <-> {self.virtual_ports[1]}")
            return True
        else:
            self.logger.error("❌ Failed to create virtual ports")
            return self._setup_manual_ports()
    
    def _setup_manual_ports(self) -> bool:
        """Setup ports manually for testing"""
        # For manual testing, use common COM port pairs
        if sys.platform.startswith('win'):
            # Common virtual port pairs on Windows
            test_pairs = [
                ("COM10", "COM11"),
                ("COM20", "COM21"),
                ("COM3", "COM4"),
            ]
        else:
            # Linux virtual ports
            test_pairs = [
                ("/tmp/ttyV0", "/tmp/ttyV1"),
                ("/dev/pts/1", "/dev/pts/2"),
            ]
        
        for port_pair in test_pairs:
            self.config["simulator_port"] = port_pair[0]
            self.config["client_port"] = port_pair[1]
            
            self.logger.info(f"Trying manual port pair: {port_pair[0]} <-> {port_pair[1]}")
            
            # Test if ports are available
            try:
                import serial
                # Quick test of port availability
                test_serial = serial.Serial(port_pair[0], timeout=0.1)
                test_serial.close()
                self.logger.info(f"✅ Using manual port pair: {port_pair[0]} <-> {port_pair[1]}")
                return True
            except:
                continue
        
        # If no working pairs found, show setup instructions
        self._show_setup_instructions()
        return False
    
    def _show_setup_instructions(self):
        """Show setup instructions for virtual ports"""
        self.logger.info("""
🛠️  MANUAL SETUP REQUIRED

For Windows:
1. Install com0com from: https://sourceforge.net/projects/com0com/
2. Run setupc.exe as Administrator
3. Create port pair: install PortName=COM10 PortName=COM11
4. Restart this test

For Linux:
1. Install socat: sudo apt-get install socat
2. Run in terminal: socat pty,link=/tmp/ttyV0,raw,echo=0 pty,link=/tmp/ttyV1,raw,echo=0
3. Keep that terminal open and restart this test

Alternative for testing:
- Use two physical COM ports connected with a null modem cable
- Use USB-to-Serial adapters with a crossover cable
        """)
    
    def start_plc_simulator(self) -> bool:
        """Start the PLC simulator in a separate thread"""
        if not self.config["simulator_port"]:
            self.logger.error("No simulator port configured")
            return False
        
        try:
            self.logger.info(f"🏭 Starting PLC simulator on {self.config['simulator_port']}...")
            
            # Create simulator instance
            self.plc_simulator = ModbusRTUSimulator(
                port=self.config["simulator_port"],
                baudrate=self.config["baudrate"],
                device_id=self.config["device_id"],
                timeout=self.config["timeout"]
            )
            
            # Start simulator in separate thread
            self.simulator_thread = threading.Thread(target=self.plc_simulator.start)
            self.simulator_thread.daemon = True
            self.simulator_thread.start()
            
            # Wait a bit for simulator to start
            time.sleep(2)
            
            if self.plc_simulator.running:
                self.logger.info("✅ PLC simulator started successfully")
                return True
            else:
                self.logger.error("❌ PLC simulator failed to start")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start PLC simulator: {e}")
            return False
    
    def create_test_client(self) -> bool:
        """Create and connect test client"""
        if not self.config["client_port"]:
            self.logger.error("No client port configured")
            return False
        
        try:
            self.logger.info(f"🔍 Creating test client on {self.config['client_port']}...")
            
            # Create test client
            self.test_client = ModbusRTUTestClient(
                port=self.config["client_port"],
                baudrate=self.config["baudrate"],
                device_id=self.config["device_id"],
                timeout=self.config["timeout"]
            )
            
            # Connect to simulator
            if self.test_client.connect():
                self.logger.info("✅ Test client connected successfully")
                return True
            else:
                self.logger.error("❌ Test client failed to connect")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to create test client: {e}")
            return False
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        self.logger.info("🧪 Starting Modbus RTU integration tests...")
        
        test_results = {
            "start_time": time.time(),
            "setup": {},
            "basic_tests": {},
            "comprehensive_tests": {},
            "performance_tests": {},
            "stress_tests": {},
            "summary": {}
        }
        
        # Basic connectivity test
        self.logger.info("📡 Testing basic connectivity...")
        basic_result = self.test_client.read_input_registers(0, 1)
        test_results["basic_tests"]["connectivity"] = {
            "success": basic_result.success,
            "duration": basic_result.duration,
            "error": basic_result.error_message
        }
        
        if not basic_result.success:
            self.logger.error("❌ Basic connectivity test failed")
            test_results["summary"]["early_termination"] = "Basic connectivity failed"
            return test_results
        
        # Comprehensive PCBA test suite
        self.logger.info("🔬 Running comprehensive PCBA test suite...")
        pcba_results = self.test_client.run_pcba_comprehensive_test()
        test_results["comprehensive_tests"] = pcba_results
        
        # Performance test - multiple rapid reads
        self.logger.info("⚡ Running performance tests...")
        performance_results = self._run_performance_tests()
        test_results["performance_tests"] = performance_results
        
        # Stress test - continuous operation
        self.logger.info("💪 Running stress tests...")
        stress_results = self._run_stress_tests()
        test_results["stress_tests"] = stress_results
        
        # Calculate overall summary
        test_results["end_time"] = time.time()
        test_results["total_duration"] = test_results["end_time"] - test_results["start_time"]
        
        # Count successes
        total_tests = 0
        passed_tests = 0
        
        # Basic tests
        if test_results["basic_tests"]["connectivity"]["success"]:
            passed_tests += 1
        total_tests += 1
        
        # Comprehensive tests
        if "summary" in test_results["comprehensive_tests"]:
            comp_summary = test_results["comprehensive_tests"]["summary"]
            total_tests += comp_summary["total_tests"]
            passed_tests += comp_summary["passed_tests"]
        
        # Performance tests
        if "summary" in test_results["performance_tests"]:
            perf_summary = test_results["performance_tests"]["summary"]
            total_tests += perf_summary["total_tests"]
            passed_tests += perf_summary["passed_tests"]
        
        test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
        }
        
        return test_results
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance-focused tests"""
        perf_results = {
            "rapid_reads": [],
            "write_read_cycles": [],
            "summary": {}
        }
        
        # Rapid read test
        start_time = time.time()
        for i in range(10):
            result = self.test_client.read_input_registers(0, 5)
            perf_results["rapid_reads"].append({
                "iteration": i,
                "success": result.success,
                "duration": result.duration
            })
        
        # Write-read cycle test
        for i in range(5):
            write_result = self.test_client.write_single_register(1, i)
            read_result = self.test_client.read_holding_registers(1, 1)
            
            perf_results["write_read_cycles"].append({
                "iteration": i,
                "write_success": write_result.success,
                "read_success": read_result.success,
                "write_duration": write_result.duration,
                "read_duration": read_result.duration,
                "total_duration": write_result.duration + read_result.duration
            })
        
        # Calculate summary
        rapid_successes = sum(1 for r in perf_results["rapid_reads"] if r["success"])
        cycle_successes = sum(1 for r in perf_results["write_read_cycles"] 
                             if r["write_success"] and r["read_success"])
        
        perf_results["summary"] = {
            "total_tests": len(perf_results["rapid_reads"]) + len(perf_results["write_read_cycles"]),
            "passed_tests": rapid_successes + cycle_successes,
            "rapid_read_success_rate": (rapid_successes / len(perf_results["rapid_reads"])) * 100,
            "cycle_success_rate": (cycle_successes / len(perf_results["write_read_cycles"])) * 100 if perf_results["write_read_cycles"] else 0,
            "avg_read_duration": sum(r["duration"] for r in perf_results["rapid_reads"] if r["success"]) / rapid_successes if rapid_successes > 0 else 0
        }
        
        return perf_results
    
    def _run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests with continuous operation"""
        stress_results = {
            "continuous_reads": [],
            "error_recovery": [],
            "summary": {}
        }
        
        # Continuous read test for 10 seconds
        self.logger.info("Running 10-second continuous read test...")
        start_time = time.time()
        read_count = 0
        error_count = 0
        
        while time.time() - start_time < 10:
            result = self.test_client.read_input_registers(0, 1)
            read_count += 1
            
            if not result.success:
                error_count += 1
            
            stress_results["continuous_reads"].append({
                "timestamp": time.time() - start_time,
                "success": result.success,
                "duration": result.duration
            })
            
            time.sleep(0.1)  # 10 reads per second
        
        stress_results["summary"] = {
            "total_tests": read_count,
            "passed_tests": read_count - error_count,
            "error_rate": (error_count / read_count) * 100 if read_count > 0 else 0,
            "reads_per_second": read_count / 10.0
        }
        
        return stress_results
    
    def generate_report(self, test_results: Dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_filename = f"modbus_integration_test_report_{timestamp}.json"
        
        # Add configuration to results
        test_results["configuration"] = self.config
        test_results["environment"] = {
            "platform": sys.platform,
            "python_version": sys.version,
            "simulator_port": self.config["simulator_port"],
            "client_port": self.config["client_port"]
        }
        
        # Save detailed results
        with open(report_filename, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        # Create summary report
        summary_filename = f"modbus_test_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write("MODBUS RTU INTEGRATION TEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {test_results['total_duration']:.2f} seconds\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Simulator Port: {self.config['simulator_port']}\n")
            f.write(f"Client Port: {self.config['client_port']}\n\n")
            
            f.write("SUMMARY\n")
            f.write("-" * 20 + "\n")
            summary = test_results["summary"]
            f.write(f"Total Tests: {summary['total_tests']}\n")
            f.write(f"Passed: {summary['passed_tests']}\n")
            f.write(f"Failed: {summary['failed_tests']}\n")
            f.write(f"Success Rate: {summary['success_rate']:.1f}%\n")
            f.write(f"Overall Status: {summary['overall_status']}\n\n")
            
            # Performance metrics
            if "performance_tests" in test_results and "summary" in test_results["performance_tests"]:
                perf = test_results["performance_tests"]["summary"]
                f.write("PERFORMANCE METRICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Average Read Duration: {perf['avg_read_duration']:.3f}s\n")
                f.write(f"Rapid Read Success Rate: {perf['rapid_read_success_rate']:.1f}%\n\n")
            
            # PCBA Data Sample
            if ("comprehensive_tests" in test_results and 
                "pcba_data" in test_results["comprehensive_tests"]):
                pcba_data = test_results["comprehensive_tests"]["pcba_data"]
                f.write("PCBA SIMULATION DATA SAMPLE\n")
                f.write("-" * 30 + "\n")
                
                for category, data in pcba_data.items():
                    f.write(f"{category.title()}:\n")
                    for key, value in data.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
        
        self.logger.info(f"📄 Detailed report saved: {report_filename}")
        self.logger.info(f"📋 Summary report saved: {summary_filename}")
        
        return report_filename
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("🧹 Cleaning up...")
        
        # Stop test client
        if self.test_client:
            self.test_client.disconnect()
        
        # Stop PLC simulator
        if self.plc_simulator:
            self.plc_simulator.stop()
        
        # Wait for simulator thread
        if self.simulator_thread and self.simulator_thread.is_alive():
            self.simulator_thread.join(timeout=5)
        
        # Cleanup virtual ports
        if self.virtual_port_manager:
            self.virtual_port_manager.cleanup()
        
        self.logger.info("✅ Cleanup completed")
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite"""
        self.logger.info("🚀 Starting Modbus RTU Integration Test Suite")
        self.logger.info("=" * 60)
        
        try:
            # Step 1: Setup virtual ports
            if not self.setup_virtual_ports():
                return {"error": "Failed to setup virtual ports"}
            
            # Step 2: Start PLC simulator
            if not self.start_plc_simulator():
                return {"error": "Failed to start PLC simulator"}
            
            # Step 3: Create test client
            if not self.create_test_client():
                return {"error": "Failed to create test client"}
            
            # Step 4: Run integration tests
            test_results = self.run_integration_tests()
            
            # Step 5: Generate report
            report_file = self.generate_report(test_results)
            test_results["report_file"] = report_file
            
            # Print summary
            self.logger.info("\n" + "=" * 60)
            self.logger.info("📊 TEST SUITE COMPLETED")
            self.logger.info("=" * 60)
            summary = test_results["summary"]
            self.logger.info(f"Total Tests: {summary['total_tests']}")
            self.logger.info(f"Passed: {summary['passed_tests']}")
            self.logger.info(f"Failed: {summary['failed_tests']}")
            self.logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
            self.logger.info(f"Overall Status: {summary['overall_status']}")
            self.logger.info(f"Duration: {test_results['total_duration']:.2f}s")
            self.logger.info("=" * 60)
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {e}")
            return {"error": str(e)}
        
        finally:
            self.cleanup()

def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run test suite
    test_suite = ModbusIntegrationTestSuite()
    
    try:
        results = test_suite.run_full_test_suite()
        
        if "error" in results:
            print(f"\n❌ Test suite failed: {results['error']}")
            return 1
        else:
            print(f"\n✅ Test suite completed successfully!")
            print(f"Report file: {results.get('report_file', 'N/A')}")
            return 0
            
    except KeyboardInterrupt:
        print("\n⏹️ Test suite interrupted by user")
        test_suite.cleanup()
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        test_suite.cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())