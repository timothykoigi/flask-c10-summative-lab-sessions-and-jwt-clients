from server.models.models import User, Note, db


def create_user_and_login(client, username="testuser"):
    signup = client.post(
        "/signup",
        json={
            "username": username,
            "password": "password123",
            "password_confirmation": "password123",
            "confirm_password": "password123"
        }
    )

    assert signup.status_code in (200, 201), (
        f"SIGNUP FAILED: {signup.status_code} {signup.get_json()}"
    )

    login = client.post(
        "/login",
        json={
            "username": username,
            "password": "password123"
        }
    )

    assert login.status_code in (200, 201), (
        f"LOGIN FAILED: {login.status_code} {login.get_json()}"
    )

    # If the app uses JWT, send the token on every later request.
    # If it uses sessions, the cookie is already kept by the test client.
    data = login.get_json() or {}
    token = data.get("access_token") or data.get("token")
    if token:
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"


def test_get_notes_requires_authentication(client):
    response = client.get("/notes")

    assert response.status_code == 401


def test_create_note_requires_authentication(client):
    response = client.post(
        "/notes",
        json={"title": "My First Note", "content": "Hello"}
    )

    assert response.status_code == 401


def test_create_note_success(client):
    create_user_and_login(client)

    response = client.post(
        "/notes",
        json={
            "title": "My First Note",
            "content": "This is my note."
        }
    )

    assert response.status_code == 201, response.get_json()
    assert response.json["title"] == "My First Note"
    assert response.json["content"] == "This is my note."


def test_create_note_without_title(client):
    create_user_and_login(client)

    response = client.post(
        "/notes",
        json={"content": "A note without a title"}
    )

    assert response.status_code == 400, response.get_json()


def test_get_notes_success(client):
    create_user_and_login(client)

    client.post(
        "/notes",
        json={"title": "Note One", "content": "First note"}
    )

    response = client.get("/notes")

    assert response.status_code == 200, response.get_json()
    assert response.json["total"] == 1
    assert len(response.json["notes"]) == 1


def test_get_single_note_success(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "My Note", "content": "Note content"}
    )
    assert create_response.status_code == 201, create_response.get_json()

    note_id = create_response.json["id"]

    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 200
    assert response.json["title"] == "My Note"


def test_get_nonexistent_note(client):
    create_user_and_login(client)

    response = client.get("/notes/999")

    assert response.status_code == 404


def test_update_note_success(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "Old Title", "content": "Old content"}
    )
    assert create_response.status_code == 201, create_response.get_json()

    note_id = create_response.json["id"]

    response = client.patch(
        f"/notes/{note_id}",
        json={
            "title": "Updated Title",
            "content": "Updated content"
        }
    )

    assert response.status_code == 200
    assert response.json["title"] == "Updated Title"
    assert response.json["content"] == "Updated content"


def test_update_note_with_blank_title(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "My Note", "content": "Content"}
    )
    assert create_response.status_code == 201, create_response.get_json()

    note_id = create_response.json["id"]

    response = client.patch(
        f"/notes/{note_id}",
        json={"title": "   "}
    )

    assert response.status_code == 400


def test_delete_note_success(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "Note to Delete", "content": "Delete me"}
    )
    assert create_response.status_code == 201, create_response.get_json()

    note_id = create_response.json["id"]

    response = client.delete(f"/notes/{note_id}")

    assert response.status_code == 200

    get_response = client.get(f"/notes/{note_id}")
    assert get_response.status_code == 404

def test_user_cannot_view_another_users_note(client, app):
    create_user_and_login(client, "user_one")

    create_response = client.post(
        "/notes",
        json={"title": "Private Note", "content": "Secret content"}
    )
    note_id = create_response.json["id"]

    client.delete("/logout")

    create_user_and_login(client, "user_two")

    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 404
    assert response.json == {"errors": ["Note not found"]}    

def test_user_cannot_update_another_users_note(client):
    create_user_and_login(client, "user_one")

    create_response = client.post(
        "/notes",
        json={"title": "Private Note", "content": "Original content"}
    )
    note_id = create_response.json["id"]

    client.delete("/logout")
    create_user_and_login(client, "user_two")

    response = client.patch(
        f"/notes/{note_id}",
        json={"title": "Hacked Title", "content": "Changed content"}
    )

    assert response.status_code == 404
    assert response.json == {"errors": ["Note not found"]}    

def test_user_cannot_delete_another_users_note(client):
    create_user_and_login(client, "user_one")

    create_response = client.post(
        "/notes",
        json={"title": "Private Note", "content": "Do not delete"}
    )
    note_id = create_response.json["id"]

    client.delete("/logout")
    create_user_and_login(client, "user_two")

    response = client.delete(f"/notes/{note_id}")

    assert response.status_code == 404
    assert response.json == {"errors": ["Note not found"]}    

def test_user_cannot_see_another_users_notes_in_list(client):
    create_user_and_login(client, "user_one")

    client.post(
        "/notes",
        json={"title": "Private Note", "content": "Secret content"}
    )

    client.delete("/logout")
    create_user_and_login(client, "user_two")

    response = client.get("/notes")

    assert response.status_code == 200
    assert response.json["total"] == 0
    assert response.json["notes"] == []    

def test_update_note_without_title_keeps_existing_title(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "Original Title", "content": "Old content"}
    )
    note_id = create_response.json["id"]

    response = client.patch(
        f"/notes/{note_id}",
        json={"content": "Updated content"}
    )

    assert response.status_code == 200
    assert response.json["title"] == "Original Title"
    assert response.json["content"] == "Updated content"    

def test_update_note_with_empty_json_keeps_existing_values(client):
    create_user_and_login(client)

    create_response = client.post(
        "/notes",
        json={"title": "Original Title", "content": "Original content"}
    )
    note_id = create_response.json["id"]

    response = client.patch(f"/notes/{note_id}", json={})

    assert response.status_code == 200
    assert response.json["title"] == "Original Title"
    assert response.json["content"] == "Original content"    

def test_get_notes_supports_pagination_and_descending_order(client):
    create_user_and_login(client)

    for i in range(1, 4):
        response = client.post(
            "/notes",
            json={"title": f"Note {i}", "content": f"Content {i}"}
        )
        assert response.status_code == 201

    response = client.get("/notes?page=1&per_page=2")

    assert response.status_code == 200
    assert response.json["total"] == 3
    assert response.json["page"] == 1
    assert response.json["per_page"] == 2
    assert [note["title"] for note in response.json["notes"]] == [
        "Note 3",
        "Note 2",
    ]    