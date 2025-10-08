#!/bin/bash

cd /home/kp101/Desktop/F1-OS/Pi/

##############################################
# CONFIGURATION
##############################################
ENABLE_LOGGING=false  # Set to false to disable performance logging
ENABLE_GPU=true      # Set to false to run without GPU acceleration

##############################################
# Performance Logging Setup
##############################################
if [ "$ENABLE_LOGGING" = true ]; then
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
    echo "Performance logging enabled: $LOG_FILE"
else
    echo "Performance logging disabled"
    MONITOR_PID=""
fi

##############################################
# Cleanup Function
##############################################
cleanup() {
    echo "Stopping F1-OS..."
    if [ ! -z "$MONITOR_PID" ]; then
        echo "Stopping monitoring..."
        kill $MONITOR_PID 2>/dev/null
        wait $MONITOR_PID 2>/dev/null
        if [ "$ENABLE_LOGGING" = true ]; then
            echo "Stopped: $(date)" >> "$LOG_FILE"
            echo "Performance log saved to: $LOG_FILE"
        fi
    fi
    exit 0
}

# Trap EXIT, SIGINT, SIGTERM to ensure cleanup runs
trap cleanup EXIT INT TERM

##############################################
# Update Code from Git
##############################################
source venv/bin/activate
git fetch
git pull

##############################################
# GPU Acceleration Setup
##############################################
if [ "$ENABLE_GPU" = true ]; then
    # Load GPU kernel modules if not already loaded
    if ! lsmod | grep -q "vc4"; then
        echo "Loading vc4 GPU module..."
        sudo modprobe vc4
    fi

    if ! lsmod | grep -q "v3d"; then
        echo "Loading v3d GPU module..."
        sudo modprobe v3d
    fi

    # Check if DRM device exists
    if [ ! -e /dev/dri/card0 ]; then
        echo "WARNING: /dev/dri/card0 not found. GPU acceleration may not work."
        echo "Check GPU_SETUP.md for troubleshooting steps."
        echo "Continuing without GPU acceleration..."
    else
        echo "GPU detected, enabling hardware acceleration..."
    fi
else
    echo "GPU acceleration disabled"
fi

##############################################
# Start Application
##############################################
echo "Starting F1-OS..."

# Run Python with environment variables set ONLY for this process
# This prevents affecting other applications like rpi-connect
if [ "$ENABLE_GPU" = true ] && [ -e /dev/dri/card0 ]; then
    # EGLFS mode (direct GPU rendering, fullscreen only)
    QT_QPA_PLATFORM=eglfs \
    QT_QPA_EGLFS_INTEGRATION=eglfs_kms \
    QT_QPA_EGLFS_KMS_CONFIG=/home/kp101/Desktop/F1-OS/Pi/kms_config.json \
    QT_QUICK_BACKEND=software \
    QSG_RENDER_LOOP=basic \
    python main.py
else
    # No GPU acceleration, let Qt auto-detect platform
    python main.py
fi

# Cleanup will be called automatically via trap