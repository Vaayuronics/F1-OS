import os

def rmtree(path):
    for entry in os.listdir(path):
        full = path + "/" + entry
        mode = os.stat(full)[0]
        if mode & 0x4000:  # stat.S_IFDIR
            rmtree(full)
        else:
            os.remove(full)
    os.rmdir(path)

rmtree("lib")