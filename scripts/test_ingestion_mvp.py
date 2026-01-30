
import os
import time
import requests
import json
import sys

# Configuration
API_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin"
TEST_DATA_DIR = "./testdata/input"

def login():
    print(f"Logging in as {USERNAME}...")
    try:
        response = requests.post(f"{API_URL}/auth/token", data={
            "username": USERNAME,
            "password": PASSWORD
        })
        response.raise_for_status()
        token = response.json()["access_token"]
        print("Login successful.")
        return token
    except Exception as e:
        print(f"Login failed: {e}")
        if response.content:
            print(response.content.decode())
        sys.exit(1)

def upload_file(token, filepath):
    filename = os.path.basename(filepath)
    print(f"Uploading {filename}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    # FastAPI expects "files" key for List[UploadFile] = File(...)
    files = [
        ("files", (filename, open(filepath, "rb"), "application/pdf"))
    ]
    
    try:
        response = requests.post(
            f"{API_URL}/ingestion/upload",
            headers=headers,
            files=files
        )
        response.raise_for_status()
        job = response.json()
        doc_ids = job.get("documents_created", [])
        if doc_ids:
            # For simplicity, return the first one since we upload one by one in this loop
            print(f"Upload successful. Job ID: {job['job_id']}, Docs: {doc_ids}")
            return doc_ids[0]
        else:
            print("Upload successful but no documents created (maybe duplicate?).")
            return None
    except Exception as e:
        print(f"Upload failed: {e}")
        if response.content:
            print(response.content.decode())
        return None

def poll_document(token, doc_id):
    print(f"Polling document {doc_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    while time.time() - start_time < 300:  # 5 minutes timeout
        try:
            response = requests.get(f"{API_URL}/documents/{doc_id}", headers=headers)
            if response.status_code != 200:
                print(f"Error polling: {response.status_code}")
                time.sleep(2)
                continue
                
            doc = response.json()
            status = doc["status"]
            print(f"Status: {status}")
            
            if status in ["extracted", "validated", "failed"]:
                return doc
            
            time.sleep(2)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(2)
            
    print("Timeout waiting for processing.")
    return None

def main():
    token = login()
    
    # Get files
    files = [f for f in os.listdir(TEST_DATA_DIR) if f.endswith(".pdf")]
    files.sort()
    
    if not files:
        print("No PDF files found in testdata/input")
        sys.exit(1)
        
    results = {}
    
    for filename in files:
        filepath = os.path.join(TEST_DATA_DIR, filename)
        doc_id = upload_file(token, filepath)
        if doc_id:
            final_doc = poll_document(token, doc_id)
            if final_doc:
                results[filename] = final_doc
                
                # Print Extraction Summary
                print(f"\n--- Result for {filename} ---")
                print(f"Type: {final_doc.get('doc_type')}")
                print(f"Stats: {final_doc.get('doc_type_confidence')}")
                print(f"Warnings: {final_doc.get('warnings')}")
                
                # Fetch fields usually requires a separate call if not fully detailed in get
                # But based on schemas, DocumentRead might verify basic metadata.
                # Let's verify fields extraction separately if valid
                
    # Save full dump
    with open("mvp_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull results saved to mvp_test_results.json")

if __name__ == "__main__":
    main()
