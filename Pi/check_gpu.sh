#!/bin/bash
# Quick GPU status check for Raspberry Pi 4

echo "=== Raspberry Pi GPU Status Check ==="
echo ""

echo "1. GPU Memory Allocation:"
vcgencmd get_mem gpu
echo ""

echo "2. GPU Driver Modules:"
lsmod | grep -E "vc4|v3d" || echo "   No GPU modules loaded!"
echo ""

echo "3. DRM Devices:"
ls -l /dev/dri/ 2>/dev/null || echo "   /dev/dri not found!"
echo ""

echo "4. Config.txt GPU Settings:"
grep -E "vc4|gpu_mem" /boot/firmware/config.txt 2>/dev/null || grep -E "vc4|gpu_mem" /boot/config.txt 2>/dev/null || echo "   No GPU settings found"
echo ""

echo "5. Mesa DRI Drivers:"
ls -l /usr/lib/arm-linux-gnueabihf/dri/ 2>/dev/null | grep -E "vc4|v3d" || \
ls -l /usr/lib/aarch64-linux-gnu/dri/ 2>/dev/null | grep -E "vc4|v3d" || \
echo "   No Mesa DRI drivers found"
echo ""

echo "6. Qt Environment:"
echo "   QT_QPA_PLATFORM = ${QT_QPA_PLATFORM:-not set}"
echo "   QT_QPA_EGLFS_INTEGRATION = ${QT_QPA_EGLFS_INTEGRATION:-not set}"
echo ""

echo "7. GPU Temperature & Clock:"
vcgencmd measure_temp
vcgencmd measure_clock core
vcgencmd measure_clock v3d 2>/dev/null || echo "   v3d clock: Not available"
echo ""

if [ -e /dev/dri/card0 ] && lsmod | grep -q "vc4"; then
    echo "✅ GPU appears to be properly configured!"
else
    echo "❌ GPU is NOT properly configured. See GPU_SETUP.md"
fi
