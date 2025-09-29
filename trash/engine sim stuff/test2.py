import time
from engine import EngineSim

sim = EngineSim()

try:
    while True:
        sim.update(0.3)
        time.sleep(0.05)
except KeyboardInterrupt:
    sim.stop()
