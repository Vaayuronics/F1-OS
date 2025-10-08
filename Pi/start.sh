cd /home/kp101/Desktop/F1-OS/Pi/

# Create logging directory if it doesn't exist
mkdir -p logging

# Start performance monitoring in background
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logging/performance_${TIMESTAMP}.log"

echo "=== F1-OS Performance Log ===" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# System info
echo "=== System Info ===" >> "$LOG_FILE"
cat /proc/cpuinfo | grep "Model" >> "$LOG_FILE"
vcgencmd get_mem gpu >> "$LOG_FILE"
vcgencmd measure_temp >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Start background monitoring (samples every 2 seconds)
(
    while true; do
        echo "--- $(date +"%H:%M:%S") ---" >> "$LOG_FILE"
        # CPU usage (simple vmstat output)
        vmstat 1 2 | tail -1 >> "$LOG_FILE"
        # Memory usage
        free -m | grep "Mem:" >> "$LOG_FILE"
        # GPU temp and usage
        vcgencmd measure_temp >> "$LOG_FILE"
        vcgencmd measure_clock arm >> "$LOG_FILE"
        # Process-specific stats (only when app is running)
        if pgrep -f "python main.py" > /dev/null; then
            echo "Python processes:" >> "$LOG_FILE"
            ps aux | grep "python main.py" | grep -v grep >> "$LOG_FILE"
            top -b -n 1 -H -p $(pgrep -f "python main.py" | head -1) | head -20 >> "$LOG_FILE"
        fi
        echo "" >> "$LOG_FILE"
        sleep 2
    done
) &
MONITOR_PID=$!

# Activate venv and start application
source venv/bin/activate
git fetch
git pull

# Run the application with environment variables scoped to just this command
# This prevents Qt settings from affecting other applications
QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_egl python main.py

# Stop monitoring when app exits
kill $MONITOR_PID 2>/dev/null

echo "Stopped: $(date)" >> "$LOG_FILE"
echo "Performance log saved to: $LOG_FILE"