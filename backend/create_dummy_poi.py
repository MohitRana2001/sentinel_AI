import requests

# 1. Create the PoI
url = "http://localhost:8000/api/v1/person-of-interest"
payload = {
    "name": "Lawrence Bishnoi",
    "details": {
        "Names": ["Lawrence Bishnoi", "Sopu Group", "Don],
        "Status": "Gangster",
        "State": ["Punjab", "Haryana"]
        "Father Name": "Lavinder Singh",
        "Resident Of": "Punjab",
        "Crimes": ["Extortion", "Murder", "Arms Act"]
    },
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
    print("Make sure python main.py is running!")
