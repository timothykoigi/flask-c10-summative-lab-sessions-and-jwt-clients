from server.models.models import User


def test_signup_successfully_registers_a_user(client, app):
    response = client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "password123",
    })

    assert response.status_code == 201

    data = response.get_json()

    assert data["username"] == "timothy"
    assert data["user"]["username"] == "timothy"
    assert data["token"] is not None

    with app.app_context():
        user = User.query.filter_by(username="timothy").first()

        assert user is not None
        assert user.password_hash != "password123"


def test_signup_rejects_missing_username(client):
    response = client.post("/signup", json={
        "password": "password123",
        "password_confirmation": "password123",
    })

    assert response.status_code == 400
    assert "Username is required" in response.get_json()["errors"]


def test_signup_rejects_missing_password(client):
    response = client.post("/signup", json={
        "username": "timothy",
        "password_confirmation": "password123",
    })

    assert response.status_code == 400
    assert "Password is required" in response.get_json()["errors"]


def test_signup_rejects_password_mismatch(client):
    response = client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "different123",
    })

    assert response.status_code == 400
    assert "Passwords do not match" in response.get_json()["errors"]


def test_signup_rejects_duplicate_username(client):
    client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "password123",
    })

    response = client.post("/signup", json={
        "username": "timothy",
        "password": "another123",
        "password_confirmation": "another123",
    })

    assert response.status_code == 409
    assert "Username already exists" in response.get_json()["errors"]


def test_login_successfully_authenticates_user(client):
    client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "password123",
    })

    response = client.post("/login", json={
        "username": "timothy",
        "password": "password123",
    })

    assert response.status_code == 200
    assert response.get_json()["username"] == "timothy"
    assert response.get_json()["token"] is not None


def test_login_rejects_incorrect_password(client):
    client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "password123",
    })

    response = client.post("/login", json={
        "username": "timothy",
        "password": "wrongpassword",
    })

    assert response.status_code == 401
    assert "Invalid username or password" in response.get_json()["errors"]


def test_login_rejects_nonexistent_user(client):
    response = client.post("/login", json={
        "username": "unknown",
        "password": "password123",
    })

    assert response.status_code == 401
    assert "Invalid username or password" in response.get_json()["errors"]


def test_login_rejects_missing_credentials(client):
    response = client.post("/login", json={})

    assert response.status_code == 400
    assert "Username is required" in response.get_json()["errors"]

def test_logout_clears_user_session(client):
    client.post("/signup", json={
        "username": "timothy",
        "password": "password123",
        "password_confirmation": "password123",
    })

    before_logout = client.get("/check_session")
    assert before_logout.status_code == 200
    assert before_logout.get_json()["username"] == "timothy"

    logout_response = client.delete("/logout")
    assert logout_response.status_code == 200

    after_logout = client.get("/check_session")
    assert after_logout.status_code == 401
    assert after_logout.get_json() == {"errors": ["Authentication required"]}    