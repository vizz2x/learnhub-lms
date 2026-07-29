import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
email = f"student_{timestamp}@example.com"

print("1. Signup...")
signup_response = requests.post(
    f"{BASE_URL}/auth/signup",
    json={"email": email, "password": "password123"}
)
token = signup_response.json()["token"]
user_id = signup_response.json()["user_id"]
print(f"✓ User {user_id} created\n")

print("2. Enroll in course 1...")
enroll1 = requests.post(f"{BASE_URL}/courses/1/enroll?token={token}")
print(f"Status: {enroll1.status_code}")
print(json.dumps(enroll1.json(), indent=2))

print("\n3. Enroll in course 2...")
enroll2 = requests.post(f"{BASE_URL}/courses/2/enroll?token={token}")
print(f"Status: {enroll2.status_code}")
print(json.dumps(enroll2.json(), indent=2))

print("\n4. Get courses...")
courses = requests.get(f"{BASE_URL}/courses?token={token}")
print(f"Status: {courses.status_code}")
print(json.dumps(courses.json(), indent=2))