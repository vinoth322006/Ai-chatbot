from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import random
import string

def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))

def random_email() -> str:
    return f"{random_lower_string()}@example.com"

def test_create_user(client: TestClient) -> None:
    email = random_email()
    password = random_lower_string()
    data = {"email": email, "password": password, "username": email.split("@")[0]}
    response = client.post(f"/api/auth/register", json=data)
    assert response.status_code == 201
    content = response.json()
    assert content["email"] == email
    assert "id" in content

def test_login_user(client: TestClient) -> None:
    email = random_email()
    password = random_lower_string()
    # Register first
    data = {"email": email, "password": password, "username": email.split("@")[0]}
    client.post(f"/api/auth/register", json=data)
    
    # Login
    login_data = {
        "username": email,
        "password": password
    }
    response = client.post(f"/api/auth/login", data=login_data)
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"
