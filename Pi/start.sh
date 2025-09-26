sudo udevadm control --reload-rules
sudo udevadm trigger
cd /home/kp101/Desktop/F1-OS/Pi/
source venv/bin/activate
git fetch
git pull
sudo python main.py