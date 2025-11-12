import requests
import sys
import json

# API Configuration
API_URL = "http://localhost:8000/api/v1/person-of-interest"

payload = {
    "name": "Lawrence Bishnoi",
    "details": {
        "Names": ["Lawrence Bishnoi", "Sopu Group", "Don"],
        "Status": "Gangster",
        "State": ["Punjab", "Haryana", "Rajasthan", "Delhi"],
        "Father Name": "Lavinder Singh",
        "Resident Of": "Punjab",
        "Crimes": ["Extortion", "Murder", "Arms Act"]
    },
    "photograph_base64": "" 
}

print(f"🚀 Sending request to: {API_URL}")

try:
    response = requests.post(API_URL, json=payload)
    print(f"Status Code: {response.status_code}")
    
    # Try to print JSON, if that fails, print Raw Text
    try:
        print("Response JSON:", response.json())
    except json.JSONDecodeError:
        print("⚠️ Server did NOT return JSON. Here is the raw response:")
        print("-" * 20)
        print(response.text)
        print("-" * 20)

except Exception as e:
    print(f"❌ Script Error: {e}")