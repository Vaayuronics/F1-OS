# Quick Reference: GPU Acceleration Setup

## One-Line Install (Copy & Paste)

```bash
sudo apt-get update && sudo apt-get install -y libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev mesa-utils python3-opengl && pip3 install PySide6-Essentials PySide6-Addons
```

## Quick GPU Memory Setup

```bash
sudo raspi-config
```

- Navigate to: **Performance Options** → **GPU Memory** → Set to **256**
- Reboot: `sudo reboot`

## Enable V3D Driver (Pi 4/5)

```bash
echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
echo "max_framebuffers=2" | sudo tee -a /boot/config.txt
sudo reboot
```

## Test GPU

```bash
# Check OpenGL
glxinfo | grep "OpenGL version"

# Check driver
lsmod | grep vc4

# Monitor GPU while running
watch -n 1 vcgencmd measure_temp
```

## Platform Options

Edit `Pi/main.py`:

**EGLFS (Best performance, fullscreen):**

```python
os.environ['QT_QPA_PLATFORM'] = 'eglfs'
```

**XCB (Windowed mode):**

```python
os.environ['QT_QPA_PLATFORM'] = 'xcb'
```

## Performance Check

**Expected Results:**

- CPU: 20-40%
- GPU: 60-80%
- FPS: 30 (stable)
- Temp: <70°C

## Troubleshooting

| Issue         | Solution                 |
| ------------- | ------------------------ |
| Black screen  | Switch to XCB platform   |
| OpenGL errors | Install missing packages |
| Still slow    | Check GPU memory (256MB) |
| Too hot       | Add heatsink/fan         |

## Full Documentation

See [`RASPBERRY_PI_GPU_SETUP.md`](RASPBERRY_PI_GPU_SETUP.md) for complete guide.
