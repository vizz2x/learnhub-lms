import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# Generate unique email
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

print("2. Ask chatbot about Algebra (lesson 1)...")
chatbot_response = requests.post(
    f"{BASE_URL}/chatbot/ask?token={token}",
    json={
        "message": "How do I solve for x in an equation?",
        "course_id": 1,
        "lesson_id": 1
    }
)
print(f"Status: {chatbot_response.status_code}")
print(json.dumps(chatbot_response.json(), indent=2))

print("\n3. Ask chatbot about Geometry (lesson 2)...")
chatbot_response2 = requests.post(
    f"{BASE_URL}/chatbot/ask",
    json={
        "message": "What are the properties of triangles?",
        "course_id": 2,
        "lesson_id": 2,
        "token": token
    }
)
print(f"Status: {chatbot_response2.status_code}")
print(json.dumps(chatbot_response2.json(), indent=2))