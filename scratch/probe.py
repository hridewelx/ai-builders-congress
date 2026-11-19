import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8077/login", timeout=3) as res:
        print("Status:", res.status)
except Exception as e:
    print("Error:", e)

