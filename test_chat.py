
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def login():
    # Helper to get token (assuming test user/pw or using admin)
    # For simplicity, we assume we can get token. 
    # Or strict test: create user. 
    # But let's assume we have "admin@example.com" / "admin"
    resp = requests.post(f"{BASE_URL}/auth/token", data={"username": "admin@example.com", "password": "admin"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return None
    return resp.json()["access_token"]

def test_chat_persistence():
    token = login()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Start new chat
    print("\n1. Sending first message...")
    msg1 = {
        "message": "Mi chiamo Mario Rossi."
        # No session_id
    }
    resp1 = requests.post(f"{BASE_URL}/chat", json=msg1, headers=headers)
    if resp1.status_code != 200:
        print(f"Chat failed: {resp1.text}")
        return
    
    data1 = resp1.json()
    session_id = data1["session_id"]
    print(f"Session created: {session_id}")
    print(f"Response: {data1['message']}")
    
    # 2. Follow up (Context test)
    print("\n2. Sending follow-up message...")
    msg2 = {
        "message": "Come mi chiamo?",
        "session_id": session_id
    }
    resp2 = requests.post(f"{BASE_URL}/chat", json=msg2, headers=headers)
    data2 = resp2.json()
    print(f"Response: {data2['message']}")
    
    if "Mario Rossi" in data2['message']:
        print("SUCCESS: Context preserved!")
    else:
        print("FAILURE: Context lost.")

    # 3. Check History Endpoint
    print("\n3. Checking history...")
    resp_hist = requests.get(f"{BASE_URL}/chat/sessions/{session_id}", headers=headers)
    msgs = resp_hist.json()
    print(f"Found {len(msgs)} messages in history.")
    for m in msgs:
        print(f"- {m['role']}: {m['content']}")

if __name__ == "__main__":
    test_chat_persistence()
