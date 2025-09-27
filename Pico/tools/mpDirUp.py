import subprocess
import os
import sys

def run_mpremote_cmd(cmd_list):
    try:
        subprocess.run(["mpremote"] + cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd_list)}")

def upload_folder(local_folder, pico_folder=""):
    if not os.path.isdir(local_folder):
        print(f"'{local_folder}' is not a valid folder.")
        return

    for root, dirs, files in os.walk(local_folder):
        rel_path = os.path.relpath(root, local_folder)
        # Fix for ".": don't include it in the path
        if rel_path == ".":
            pico_path = pico_folder
        else:
            pico_path = os.path.join(pico_folder, rel_path).replace("\\", "/")

        if pico_path:
            run_mpremote_cmd(["fs", "mkdir", f":{pico_path}"])

        for file in files:
            local_file = os.path.join(root, file)
            remote_file = os.path.join(pico_path, file).replace("\\", "/")
            print(f"Uploading {local_file} -> :{remote_file}")
            run_mpremote_cmd(["fs", "cp", local_file, f":{remote_file}"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_pico.py <local_folder> [target_folder_on_pico]")
    else:
        local = sys.argv[1]
        remote = sys.argv[2] if len(sys.argv) > 2 else ""
        upload_folder(local, remote)