import os
import sys

print("Current Working Directory:", os.getcwd())
print("Python Executable:", sys.executable)
print("Python Path:", sys.path)

try:
    from app.utils.geocoder import GeoCoder
    print("GeoCoder Import Success")
except Exception as e:
    print("GeoCoder Import Failed:", e)

try:
    import dotenv
    dotenv.load_dotenv()
    print(".env Loaded")
    print("NAVER_CLIENT_ID:", os.getenv("NAVER_CLIENT_ID")[:5] + "...")
except Exception as e:
    print(".env Load Failed:", e)
