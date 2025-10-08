#!/bin/bash

cd /home/kp101/Desktop/F1-OS/Pi/

##############################################
# CONFIGURATION
##############################################
ENABLE_LOGGING=false  # Set to true to enable performance logging
ENABLE_GPU=true       # Set to false to run without GPU acceleration

##############################################
# Global Variables
##############################################
MONITOR_PID=""
PYTHON_PID=""
LOG_FILE=""

##############################################
# Cleanup Function - Kills ALL processes
##############################################
cleanup() {
    local EXIT_CODE=$?
    echo ""
    echo "============================================"
    echo "Cleaning up F1-OS processes..."
    echo "============================================"
    
    # Stop performance monitoring
    if [ ! -z "$MONITOR_PID" ]; then
        echo "Stopping performance monitoring..."
        kill $MONITOR_PID 2>/dev/null
        wait $MONITOR_PID 2>/dev/null
        if [ "$ENABLE_LOGGING" = true ] && [ ! -z "$LOG_FILE" ]; then
            echo "Stopped: $(date)" >> "$LOG_FILE"
            echo "Performance log saved to: $LOG_FILE"
        fi
    fi
    
    # Kill all Python processes related to main.py
    echo "Searching for F1-OS Python processes..."
    PIDS=$(pgrep -f "python.*main.py")
    
    if [ ! -z "$PIDS" ]; then
        echo "Found Python processes: $PIDS"
        echo "Sending SIGTERM (graceful shutdown)..."
        kill $PIDS 2>/dev/null
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            sleep 1
            STILL_ALIVE=$(pgrep -f "python.*main.py")
            if [ -z "$STILL_ALIVE" ]; then
                echo "✓ All processes terminated gracefully"
                echo "============================================"
                exit $EXIT_CODE
            fi
            echo "  Waiting for processes to exit... ($i/5)"
        done
        
        # If still alive after 5 seconds, use SIGKILL
        STILL_ALIVE=$(pgrep -f "python.*main.py")
        if [ ! -z "$STILL_ALIVE" ]; then
            echo "Processes still running. Sending SIGKILL (force kill)..."
            kill -9 $STILL_ALIVE 2>/dev/null
            sleep 1
            
            # Final check
            FINAL_CHECK=$(pgrep -f "python.*main.py")
            if [ -z "$FINAL_CHECK" ]; then
                echo "✓ All processes force-killed successfully"
            else
                echo "✗ WARNING: Some processes still running: $FINAL_CHECK"
                echo "  Try manually: sudo kill -9 $FINAL_CHECK"
            fi
        fi
    else
        echo "✓ No Python processes found"
    fi
    
    echo "============================================"
    exit $EXIT_CODE
}

# Trap EXIT, SIGINT, SIGTERM to ensure cleanup runs
trap cleanup EXIT INT TERM

##############################################
# Performance Logging Setup
##############################################
if [ "$ENABLE_LOGGING" = true ]; then
    mkdir -p logging
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

    # Start background monitoring
    (
        while true; do
            echo "--- $(date +"%H:%M:%S") ---" >> "$LOG_FILE"
            vmstat 1 2 | tail -1 >> "$LOG_FILE"
            free -m | grep "Mem:" >> "$LOG_FILE"
            vcgencmd measure_temp >> "$LOG_FILE"
            vcgencmd measure_clock arm >> "$LOG_FILE"
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
fi

##############################################
# Update Code from Git
##############################################
source venv/bin/activate
echo "Updating code from Git..."
git fetch
git pull

##############################################
# GPU Detection and Setup
##############################################
GPU_AVAILABLE=false

if [ "$ENABLE_GPU" = true ]; then
    echo "Checking GPU availability..."
    
    # Load GPU kernel modules if not already loaded
    if ! lsmod | grep -q "vc4"; then
        echo "  Loading vc4 GPU module..."
        sudo modprobe vc4 2>/dev/null
    fi

    if ! lsmod | grep -q "v3d"; then
        echo "  Loading v3d GPU module..."
        sudo modprobe v3d 2>/dev/null
    fi

    # Check if DRM device exists
    if [ -e /dev/dri/card0 ]; then
        GPU_AVAILABLE=true
        echo "✓ GPU detected at /dev/dri/card0"
    else
        echo "✗ GPU not found at /dev/dri/card0"
        echo "  See GPU_SETUP.md for setup instructions"
    fi
else
    echo "GPU acceleration disabled in config"
fi

##############################################
# Detect if rpi-connect or X11 session is running
##############################################
AVOID_EGLFS=false

# Check if rpi-connect is running (it needs X11/Wayland)
if pgrep -f "rpi-connect" > /dev/null; then
    echo "⚠ rpi-connect detected - will avoid EGLFS to prevent conflicts"
    AVOID_EGLFS=true
fi

# Check if DISPLAY is set (X11 session active)
if [ ! -z "$DISPLAY" ]; then
    echo "ℹ X11 session detected (DISPLAY=$DISPLAY)"
    AVOID_EGLFS=true
fi

##############################################
# Start Application with Appropriate Settings
##############################################
echo ""
echo "Starting F1-OS..."
echo "============================================"

# Determine Qt platform to use
if [ "$GPU_AVAILABLE" = true ] && [ "$AVOID_EGLFS" = false ]; then
    # Use EGLFS for direct GPU rendering (best performance)
    echo "Mode: EGLFS (Direct GPU rendering, fullscreen)"
    QT_QPA_PLATFORM=eglfs \
    QT_QPA_EGLFS_INTEGRATION=eglfs_kms \
    QT_QPA_EGLFS_KMS_CONFIG=/home/kp101/Desktop/F1-OS/Pi/kms_config.json \
    QT_QUICK_BACKEND=software \
    QSG_RENDER_LOOP=basic \
    python main.py &
    PYTHON_PID=$!
    
elif [ "$GPU_AVAILABLE" = true ] && [ "$AVOID_EGLFS" = true ]; then
    # Use XCB (X11) with GPU acceleration when X11 is needed
    echo "Mode: XCB (X11 with GPU acceleration)"
    QT_QPA_PLATFORM=xcb \
    QT_XCB_GL_INTEGRATION=xcb_egl \
    python main.py &
    PYTHON_PID=$!
    
else
    # No GPU or fallback mode
    echo "Mode: Auto-detect (No GPU acceleration)"
    python main.py &
    PYTHON_PID=$!
fi

echo "Python PID: $PYTHON_PID"
echo "============================================"

# Wait for Python process to finish
wait $PYTHON_PID
EXIT_CODE=$?

echo ""
echo "Python process exited with code: $EXIT_CODE"

# Cleanup will be called automatically via trap