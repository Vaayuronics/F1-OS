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
        # CPU usage per core
        mpstat -P ALL 1 1 | grep -E "CPU|Average" >> "$LOG_FILE"
        # Memory usage
        free -m | grep "Mem:" >> "$LOG_FILE"
        # GPU temp
        vcgencmd measure_temp >> "$LOG_FILE"
        # Process-specific stats (only when app is running)
        if pgrep -f "python main.py" > /dev/null; then
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

# Run the application (no sudo needed - GPIO permissions already set up)
python main.py

# Stop monitoring when app exits
kill $MONITOR_PID 2>/dev/null

echo "Stopped: $(date)" >> "$LOG_FILE"
echo "Performance log saved to: $LOG_FILE"