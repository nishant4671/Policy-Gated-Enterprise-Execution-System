import subprocess
import time

api = subprocess.Popen([r".\venv\Scripts\python.exe", "mock_systems/api.py"])
time.sleep(3)
try:
    subprocess.run([r".\venv\Scripts\pytest.exe", "tests/test_edge_cases.py", "-v"])
finally:
    api.terminate()
