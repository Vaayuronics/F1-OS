# Raspberry Pi GPU Acceleration Setup for F1-OS

This guide will help you enable GPU acceleration on your Raspberry Pi to improve UI performance for the F1-OS dashboard.

## Problem Description

The UI runs smoothly on a laptop but is very slow and laggy on the Raspberry Pi because:

1. GPU acceleration was not enabled
2. Qt was using software rendering instead of hardware acceleration
3. Anti-aliasing was disabled (now re-enabled)

## Solution

### 1. Install Required Packages

First, ensure you have the necessary OpenGL libraries installed:

```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    mesa-utils \
    python3-opengl
```

### 2. Install Qt OpenGL Support

Install PySide6 with OpenGL support:

```bash
pip3 install PySide6-Essentials PySide6-Addons
```

### 3. Verify GPU Support

Check if your Raspberry Pi GPU is working:

```bash
# Check OpenGL version
glxinfo | grep "OpenGL version"

# Check if vc4 driver is loaded (Raspberry Pi 4 and newer)
lsmod | grep vc4

# Check EGL support
eglinfo
```

### 4. Configure Qt Platform

The F1-OS application now automatically sets the correct environment variables for GPU acceleration. However, if you need to run it manually or troubleshoot, you can set these variables:

#### Option A: EGLFS (Recommended for best performance - fullscreen mode)

```bash
export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_ALWAYS_SET_MODE=1
export QSG_RENDER_LOOP=threaded
```

#### Option B: XCB (For windowed mode with X11)

```bash
export QT_QPA_PLATFORM=xcb
export QT_QPA_EGLFS_ALWAYS_SET_MODE=1
export QSG_RENDER_LOOP=threaded
```

### 5. Enable GPU Memory

Ensure your Raspberry Pi has enough GPU memory allocated:

```bash
sudo raspi-config
```

Navigate to: **Performance Options** → **GPU Memory**

Set GPU memory to at least **128MB** (256MB recommended for better performance)

Reboot after changing:

```bash
sudo reboot
```

### 6. Enable V3D Driver (Raspberry Pi 4 and newer)

For Raspberry Pi 4/5, ensure the V3D driver is enabled in `/boot/config.txt`:

```bash
sudo nano /boot/config.txt
```

Add or ensure these lines are present:

```
dtoverlay=vc4-kms-v3d
max_framebuffers=2
```

Reboot after changes:

```bash
sudo reboot
```

### 7. Test Performance

Run the dashboard and check GPU usage:

```bash
# In one terminal, monitor GPU usage
watch -n 1 vcgencmd measure_temp
watch -n 1 vcgencmd get_mem gpu

# In another terminal, run the application
cd ~/F1-OS/Pi
python3 main.py
```

## Performance Optimizations Applied

The following optimizations have been applied to the F1-OS UI:

1. **Anti-aliasing Re-enabled**: All UI components now use anti-aliasing for smooth graphics
2. **OpenGL Backend**: Qt is configured to use OpenGL ES 2.0 hardware acceleration
3. **EGLFS Platform**: Direct GPU rendering without X11 overhead (fullscreen mode)
4. **VSync Enabled**: Prevents screen tearing with swap interval
5. **4x MSAA**: Multi-sample anti-aliasing for smoother edges
6. **Threaded Rendering**: Uses separate thread for GPU operations

## Troubleshooting

### Issue: Black screen or no display

**Solution**: Try switching from EGLFS to XCB platform:

```bash
# In main.py, change:
os.environ['QT_QPA_PLATFORM'] = 'xcb'
```

### Issue: "Could not initialize egl display"

**Solution**:

1. Check if you're running in SSH without X11 forwarding
2. Ensure GPU memory is allocated (see step 5)
3. Verify V3D driver is loaded: `lsmod | grep vc4`

### Issue: Still slow performance

**Solution**:

1. Check CPU/GPU temperature: `vcgencmd measure_temp`
2. Ensure cooling is adequate (add heatsink/fan)
3. Reduce update frequency in `dashboard.py` (change `UPDATE_MS` from 33 to 50)
4. Monitor CPU usage: `top -d 1`

### Issue: Qt warnings about OpenGL

**Solution**: Install missing packages:

```bash
sudo apt-get install -y libgles2-mesa libgles2-mesa-dev
```

## Expected Performance

With GPU acceleration enabled:

- **Frame rate**: 30 FPS (33ms update interval)
- **CPU usage**: 20-40% (down from 80-100% without GPU)
- **GPU usage**: 60-80%
- **Temperature**: Should remain under 70°C with adequate cooling

## Additional Notes

- The application automatically detects and enables GPU acceleration on startup
- EGLFS mode requires the application to have exclusive access to the display
- For development with a desktop environment, use XCB mode instead
- VSync is enabled to prevent screen tearing

## References

- [Qt for Embedded Linux](https://doc.qt.io/qt-6/embedded-linux.html)
- [Raspberry Pi GPU Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#graphical-rendering)
- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
