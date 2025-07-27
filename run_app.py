# import os
# os.system("streamlit run home_page.py")

import subprocess
import threading
import webbrowser
import time

def launch_app():
    subprocess.call(["streamlit", "run", "home_page.py"])

if __name__ == "__main__":
    threading.Thread(target=launch_app).start()
    time.sleep(2)
    webbrowser.open("http://localhost:8501")