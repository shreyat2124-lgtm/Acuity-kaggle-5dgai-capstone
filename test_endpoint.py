import sys
import os
import json
from fastapi.testclient import TestClient

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app

client = TestClient(app)

def test_endpoint():
    symptoms_list = [
        "I've had a crushing pain in my chest for the last hour, and it's spreading to my left arm.",
        "I have a mild headache and a runny nose."
    ]
    
    print("Testing /assess endpoint...")
    for symptoms in symptoms_list:
        print(f"\nInput: {symptoms}")
        response = client.post("/assess", json={"symptoms": symptoms})
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    test_endpoint()
