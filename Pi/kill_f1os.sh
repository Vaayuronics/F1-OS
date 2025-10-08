#!/bin/bash
# Kill all F1-OS Python processes if they didn't shut down properly

echo "Checking for zombie F1-OS processes..."

# Find all python processes running main.py
PIDS=$(pgrep -f "python.*main.py")

if [ -z "$PIDS" ]; then
    echo "No F1-OS processes found."
else
    echo "Found F1-OS processes: $PIDS"
    echo "Killing processes..."
    
    # Try SIGTERM first (graceful)
    kill $PIDS 2>/dev/null
    sleep 2
    
    # Check if still alive
    STILL_ALIVE=$(pgrep -f "python.*main.py")
    if [ ! -z "$STILL_ALIVE" ]; then
        echo "Processes still alive, sending SIGKILL..."
        kill -9 $STILL_ALIVE 2>/dev/null
        sleep 1
    fi
    
    # Final check
    FINAL_CHECK=$(pgrep -f "python.*main.py")
    if [ -z "$FINAL_CHECK" ]; then
        echo "All F1-OS processes terminated successfully."
    else
        echo "WARNING: Some processes still running: $FINAL_CHECK"
        echo "Try: sudo kill -9 $FINAL_CHECK"
    fi
fi

# Also check for orphaned multiprocessing processes
echo ""
echo "Checking for orphaned Python multiprocessing processes..."
ps aux | grep python | grep -v grep | grep -v "kill_f1os.sh"
