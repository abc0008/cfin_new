#!/usr/bin/env python3
import subprocess
import time
import sys

# Start tailing the server log
print("Starting log monitoring...")
tail_process = subprocess.Popen(
    ["tail", "-f", "/Users/alexcardell/AlexCoding_Local/cfin/backend/server.log"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    universal_newlines=True
)

# Give it a moment to start
time.sleep(1)

# Run the WebSocket test in a separate process
print("Running WebSocket test...")
test_process = subprocess.Popen(
    [sys.executable, "/Users/alexcardell/AlexCoding_Local/cfin/test_citation_websocket_debug.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    universal_newlines=True
)

# Monitor logs for 10 seconds
print("Monitoring logs for citation activity...")
print("-" * 80)

start_time = time.time()
citation_logs = []

try:
    while time.time() - start_time < 10:
        # Check if there's output from tail
        line = tail_process.stdout.readline()
        if line and any(marker in line for marker in ["🔍", "citation", "Citation", "accumulated"]):
            citation_logs.append(line.strip())
            print(f"LOG: {line.strip()}")
            
        # Check if test is done
        if test_process.poll() is not None:
            print("\nTest completed")
            break
            
except KeyboardInterrupt:
    pass

# Clean up
tail_process.terminate()
test_process.terminate()

print("\nCitation-related logs found:")
for log in citation_logs:
    print(f"  - {log}")

# Get test output
test_output, test_error = test_process.communicate()
if test_output:
    print("\nTest output summary:")
    for line in test_output.split('\n'):
        if any(marker in line for marker in ["Citations in event:", "Citations received during stream:"]):
            print(f"  {line}")