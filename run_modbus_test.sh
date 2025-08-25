#!/bin/bash
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
