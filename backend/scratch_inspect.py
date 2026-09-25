import subprocess
import os

res = subprocess.run(["C:\\Windows\\System32\\tasklist.exe"], capture_output=True, text=True)
for line in res.stdout.splitlines():
    if "python" in line.lower() or "uvicorn" in line.lower():
        print(line)
