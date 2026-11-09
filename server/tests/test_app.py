
import jwt
import pytest

from datetime import datetime, timedelta, timezone
from server.app import create_app
from server.routes.auth_routes import bcrypt
from server.models.models import Shift, User, db
from server.seed import seed_database
from server.routes.shift_routes import format_validation_errors

def create_test_app():
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/shifts"),
        ("POST", "/shifts"),
        ("POST", "/shifts/clock-in"),
        ("GET", "/shifts/1"),
        ("PATCH", "/shifts/1"),
        ("DELETE", "/shifts/1"),
        ("PATCH", "/shifts/1/clock-out"),
    ],
)
def test_all_shift_routes_require_an_authenticated_session(method, path):
    app = create_test_app()
    with app.app_context():
        db.create_all()

    response = app.test_client().open(path, method=method)

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()


def test_shift_model_uses_the_shared_person_c_fields():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        assert {
            foreign_key.target_fullname
            for foreign_key in Shift.__table__.c.user_id.foreign_keys
        } == {"user.id"}

        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()

        saved_shift = db.session.get(Shift, shift.id)
        assert saved_shift.user_id == 12
        assert saved_shift.clock_in == datetime(2026, 10, 31, 8, 30)
        assert saved_shift.clock_out is None

        db.drop_all()


def test_clock_in_requires_a_logged_in_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    response = app.test_client().post("/shifts/clock-in")

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()


def test_clock_in_creates_a_shift_for_the_session_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.post("/shifts/clock-in")

    assert response.status_code == 201
    assert response.json["id"] == 1
    assert response.json["clock_in"]
    assert response.json["clock_out"] is None

    with app.app_context():
        shift = Shift.query.one()
        assert shift.user_id == 12
        assert shift.clock_out is None
        db.drop_all()

def test_clock_in_accepts_empty_json_object():
    app = create_test_app()

    with app.app_context():
        db.create_all()

    client = app.test_client()

    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.post("/shifts/clock-in", json={})

    assert response.status_code == 201
    assert response.json["clock_in"] is not None
    assert response.json["clock_out"] is None

    with app.app_context():
        assert Shift.query.count() == 1
        db.drop_all()

def test_clock_in_rejects_a_second_active_shift_for_the_same_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        db.session.add(Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30)))
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.post("/shifts/clock-in")

    assert response.status_code == 409
    assert response.json == {"errors": ["You are already clocked in"]}

    with app.app_context():
        assert Shift.query.count() == 1
        db.drop_all()


def test_clock_in_rejects_client_supplied_timestamps():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.post(
        "/shifts/clock-in",
        json={"clock_in": "2026-10-31T08:30:00Z"},
    )

    assert response.status_code == 400
    assert response.json == {
        "errors": ["Clock-in timestamps are set by the server"]
    }

    with app.app_context():
        assert Shift.query.count() == 0
        db.drop_all()


def test_clock_out_requires_a_logged_in_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    response = app.test_client().patch("/shifts/1/clock-out")

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()


def test_clock_out_updates_the_current_users_active_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(f"/shifts/{shift_id}/clock-out")

    assert response.status_code == 200
    assert response.json["id"] == shift_id
    assert response.json["clock_in"] == "2026-10-31T08:30:00+00:00"
    assert response.json["clock_out"]

    with app.app_context():
        saved_shift = db.session.get(Shift, shift_id)
        assert saved_shift.clock_out is not None
        assert saved_shift.clock_out > saved_shift.clock_in
        db.drop_all()


def test_clock_out_does_not_find_another_users_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 34

    response = client.patch(f"/shifts/{shift_id}/clock-out")

    assert response.status_code == 404
    assert response.json == {"errors": ["Shift not found"]}

    with app.app_context():
        shift = db.session.get(Shift, shift_id)
        assert shift.clock_out is None
        db.drop_all()


def test_clock_out_rejects_a_shift_that_is_already_closed():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(
            user_id=12,
            clock_in=datetime(2026, 10, 31, 8, 30),
            clock_out=datetime(2026, 10, 31, 16, 30),
        )
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(f"/shifts/{shift_id}/clock-out")

    assert response.status_code == 409
    assert response.json == {"errors": ["This shift is already clocked out"]}

    with app.app_context():
        assert Shift.query.count() == 1
        db.drop_all()


def test_list_shifts_returns_only_the_session_users_shifts_with_pagination():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Shift(user_id=12, clock_in=datetime(2026, 10, 30, 8, 30)),
                Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30)),
                Shift(user_id=34, clock_in=datetime(2026, 10, 31, 9, 30)),
            ]
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.get("/shifts?page=1&per_page=1")

    assert response.status_code == 200
    assert response.json["page"] == 1
    assert response.json["per_page"] == 1
    assert response.json["total"] == 2
    assert len(response.json["shifts"]) == 1
    assert response.json["shifts"][0]["clock_in"] == "2026-10-31T08:30:00+00:00"

    with app.app_context():
        db.drop_all()


def test_list_shifts_defaults_and_caps_page_size():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
                for _ in range(105)
            ]
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    default_response = client.get("/shifts?page=invalid&per_page=invalid")
    assert default_response.status_code == 200
    assert default_response.json["page"] == 1
    assert default_response.json["per_page"] == 10
    assert len(default_response.json["shifts"]) == 10

    capped_response = client.get("/shifts?page=0&per_page=101")
    assert capped_response.status_code == 200
    assert capped_response.json["page"] == 1
    assert capped_response.json["per_page"] == 100
    assert capped_response.json["total"] == 105
    assert len(capped_response.json["shifts"]) == 100

    with app.app_context():
        db.drop_all()


def test_list_shifts_returns_empty_list_for_page_past_end():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        db.session.add(
            Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.get("/shifts?page=5&per_page=1")

    assert response.status_code == 200
    assert response.json["page"] == 5
    assert response.json["total"] == 1
    assert response.json["shifts"] == []

    with app.app_context():
        db.drop_all()


def test_get_shift_does_not_expose_another_users_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 34

    response = client.get(f"/shifts/{shift_id}")

    assert response.status_code == 404
    assert response.json == {"errors": ["Shift not found"]}

    with app.app_context():
        db.drop_all()


def test_get_shift_returns_owned_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(
            user_id=12,
            clock_in=datetime(2026, 10, 31, 8, 30),
            clock_out=datetime(2026, 10, 31, 16, 30),
        )
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.get(f"/shifts/{shift_id}")

    assert response.status_code == 200
    assert response.json == {
        "id": shift_id,
        "clock_in": "2026-10-31T08:30:00+00:00",
        "clock_out": "2026-10-31T16:30:00+00:00",
    }

    with app.app_context():
        db.drop_all()


def test_post_shifts_creates_an_active_shift_for_the_session_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.post("/shifts")

    assert response.status_code == 201
    assert response.json["id"] == 1
    assert response.json["clock_in"]
    assert response.json["clock_out"] is None

    with app.app_context():
        shift = Shift.query.one()
        assert shift.user_id == 12
        assert shift.clock_out is None
        db.drop_all()


def test_update_shift_validates_timestamps_and_updates_owned_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(
        f"/shifts/{shift_id}",
        json={
            "clock_in": "2026-10-31T09:00:00Z",
            "clock_out": "2026-10-31T17:00:00Z",
        },
    )

    assert response.status_code == 200
    assert response.json["clock_in"] == "2026-10-31T09:00:00+00:00"
    assert response.json["clock_out"] == "2026-10-31T17:00:00+00:00"

    invalid_response = client.patch(
        f"/shifts/{shift_id}",
        json={"clock_out": "2026-10-31T08:00:00Z"},
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json == {"errors": ["Clock-out must be after clock-in"]}

    with app.app_context():
        saved_shift = db.session.get(Shift, shift_id)
        assert saved_shift.clock_out == datetime(2026, 10, 31, 17, 0)
        db.drop_all()


def test_update_shift_rejects_invalid_timestamps_and_unknown_fields():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    invalid_timestamp = client.patch(
        f"/shifts/{shift_id}",
        json={"clock_in": "not-a-timestamp"},
    )
    assert invalid_timestamp.status_code == 400
    assert any("clock_in" in error for error in invalid_timestamp.json["errors"])

    unknown_field = client.patch(
        f"/shifts/{shift_id}",
        json={"user_id": 34},
    )
    assert unknown_field.status_code == 400
    assert any("user_id" in error for error in unknown_field.json["errors"])

    with app.app_context():
        saved_shift = db.session.get(Shift, shift_id)
        assert saved_shift.user_id == 12
        assert saved_shift.clock_in == datetime(2026, 10, 31, 8, 30)
        db.drop_all()


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"clock_in": "not-a-date"},
        {"clock_out": 123},
        ["not", "an", "object"],
    ],
)
def test_update_shift_rejects_empty_or_malformed_payloads(body):
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(f"/shifts/{shift_id}", json=body)

    assert response.status_code == 400
    assert response.json["errors"]

    with app.app_context():
        saved_shift = db.session.get(Shift, shift_id)
        assert saved_shift.clock_in == datetime(2026, 10, 31, 8, 30)
        assert saved_shift.clock_out is None
        db.drop_all()


def test_update_shift_cannot_create_a_second_active_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        active_shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        closed_shift = Shift(
            user_id=12,
            clock_in=datetime(2026, 10, 30, 8, 30),
            clock_out=datetime(2026, 10, 30, 16, 30),
        )
        db.session.add_all([active_shift, closed_shift])
        db.session.commit()
        closed_shift_id = closed_shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(
        f"/shifts/{closed_shift_id}",
        json={"clock_out": None},
    )

    assert response.status_code == 409
    assert response.json == {"errors": ["You are already clocked in"]}

    with app.app_context():
        saved_shift = db.session.get(Shift, closed_shift_id)
        assert saved_shift.clock_out == datetime(2026, 10, 30, 16, 30)
        db.drop_all()


def test_update_shift_cannot_modify_another_users_shift():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 34

    response = client.patch(
        f"/shifts/{shift_id}",
        json={"clock_out": "2026-10-31T17:00:00Z"},
    )

    assert response.status_code == 404
    assert response.json == {"errors": ["Shift not found"]}

    with app.app_context():
        shift = db.session.get(Shift, shift_id)
        assert shift.clock_out is None
        db.drop_all()


def test_delete_shift_is_owner_scoped():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        shift = Shift(user_id=12, clock_in=datetime(2026, 10, 31, 8, 30))
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session["user_id"] = 34

    response = client.delete(f"/shifts/{shift_id}")
    assert response.status_code == 404
    assert response.json == {"errors": ["Shift not found"]}

    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.delete(f"/shifts/{shift_id}")
    assert response.status_code == 200
    assert response.json == {}

    with app.app_context():
        assert Shift.query.count() == 0
        db.drop_all()


def test_signup_creates_user_with_hashed_password_and_starts_session():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    response = client.post(
        "/signup",
        json={
            "username": "alex",
            "password": "safe-password",
            "password_confirmation": "safe-password",
        },
    )

    assert response.status_code == 201
    assert response.json["username"] == "alex"
    assert response.json["user"] == {
        "id": response.json["id"],
        "username": "alex",
    }
    assert response.json["token"]
    assert client.get("/check_session").json == response.json["user"]
    assert client.get(
        "/me",
        headers={"Authorization": f"Bearer {response.json['token']}"},
    ).json == response.json["user"]

    with app.app_context():
        user = db.session.get(User, response.json["id"])
        assert user.password_hash != "safe-password"
        assert bcrypt.check_password_hash(user.password_hash, "safe-password")
        db.drop_all()


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        (
            {"username": "alex", "password": "safe-password"},
            "Password confirmation is required",
        ),
        (
            {
                "username": "alex",
                "password": "safe-password",
                "password_confirmation": "different-password",
            },
            "Passwords do not match",
        ),
        (
            {
                "username": 42,
                "password": "safe-password",
                "password_confirmation": "safe-password",
            },
            "Username is required",
        ),
        (
            {
                "username": "alex",
                "password": ["not", "a", "string"],
                "password_confirmation": "safe-password",
            },
            "Password is required",
        ),
        (
            {
                "username": "alex",
                "password": "safe-password",
                "password_confirmation": ["not", "a", "string"],
            },
            "Password confirmation is required",
        ),
        (
            {
                "username": "a" * 81,
                "password": "safe-password",
                "password_confirmation": "safe-password",
            },
            "Username must be 80 characters or fewer",
        ),
        (["not", "an", "object"], "Request body must be a JSON object"),
    ],
)
def test_signup_rejects_invalid_input_without_creating_a_user(payload, expected_error):
    app = create_test_app()
    with app.app_context():
        db.create_all()

    response = app.test_client().post("/signup", json=payload)

    assert response.status_code == 400
    assert expected_error in response.json["errors"]

    with app.app_context():
        assert User.query.count() == 0
        db.drop_all()


def test_signup_rejects_duplicate_usernames():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    payload = {
        "username": "alex",
        "password": "safe-password",
        "password_confirmation": "safe-password",
    }
    assert client.post("/signup", json=payload).status_code == 201

    duplicate_response = client.post("/signup", json=payload)

    assert duplicate_response.status_code == 409
    assert duplicate_response.json == {"errors": ["Username already exists"]}

    with app.app_context():
        assert User.query.count() == 1
        db.drop_all()


def test_login_validates_credentials_and_starts_session():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        user = User(
            username="alex",
            password_hash=bcrypt.generate_password_hash("safe-password").decode(
                "utf-8"
            ),
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    response = client.post(
        "/login",
        json={"username": "alex", "password": "safe-password"},
    )

    assert response.status_code == 200
    assert response.json["id"] == user_id
    assert response.json["user"] == {"id": user_id, "username": "alex"}
    assert response.json["token"]
    assert client.get("/check_session").json == response.json["user"]

    invalid_credentials = client.post(
        "/login",
        json={"username": "alex", "password": "wrong-password"},
    )
    assert invalid_credentials.status_code == 401
    assert invalid_credentials.json == {
        "errors": ["Invalid username or password"]
    }

    with app.app_context():
        db.drop_all()


def test_login_rejects_malformed_or_missing_credentials():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    non_object_response = client.post("/login", json=["invalid"])
    missing_password_response = client.post("/login", json={"username": "alex"})
    invalid_types_response = client.post(
        "/login",
        json={"username": "alex", "password": ["not", "a", "string"]},
    )

    assert non_object_response.status_code == 400
    assert non_object_response.json == {
        "errors": ["Request body must be a JSON object"]
    }
    assert missing_password_response.status_code == 400
    assert missing_password_response.json == {"errors": ["Password is required"]}
    assert invalid_types_response.status_code == 400
    assert invalid_types_response.json == {"errors": ["Password is required"]}

    with app.app_context():
        db.drop_all()


def test_logout_clears_session_and_check_session_handles_no_user():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        user = User(
            username="alex",
            password_hash=bcrypt.generate_password_hash("safe-password").decode(
                "utf-8"
            ),
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    logged_out = client.get("/check_session")
    assert logged_out.status_code == 401
    assert logged_out.json == {"errors": ["Authentication required"]}

    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id
    assert client.get("/check_session").json == {"id": user_id, "username": "alex"}

    logout_response = client.delete("/logout")
    assert logout_response.status_code == 200
    assert logout_response.json == {}
    assert client.get("/check_session").status_code == 401

    with app.app_context():
        db.drop_all()

def test_me_rejects_missing_or_invalid_jwt():
    app = create_test_app()
    with app.app_context():
        db.create_all()

    client = app.test_client()
    missing_token = client.get("/me")
    invalid_token = client.get("/me", headers={"Authorization": "Bearer invalid"})

    assert missing_token.status_code == 401
    assert missing_token.json == {"errors": ["Authentication required"]}
    assert invalid_token.status_code == 401
    assert invalid_token.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()


def test_seed_database_creates_demo_users_and_shifts_once():
    app = create_test_app()
    with app.app_context():
        db.create_all()

        credentials = seed_database(user_count=2)
        assert [username for username, _ in credentials] == [
            "demo_worker_1",
            "demo_worker_2",
        ]
        assert User.query.count() == 2
        assert Shift.query.count() == 30
        for username, password in credentials:
            user = User.query.filter_by(username=username).one()
            assert bcrypt.check_password_hash(user.password_hash, password)

        assert seed_database(user_count=2) == []
        assert User.query.count() == 2
        assert Shift.query.count() == 30

        db.drop_all()

def test_me_accepts_valid_jwt():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="alex", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {"user_id": user.id, "username": user.username},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        user_id = user.id

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json == {"id": user_id, "username": "alex"}

    with app.app_context():
        db.drop_all()

def test_me_accepts_jwt_authorization_prefix():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="alex", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {"user_id": user.id, "username": user.username},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        user_id = user.id

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"JWT {token}"},
    )

    assert response.status_code == 200
    assert response.json == {"id": user_id, "username": "alex"}

    with app.app_context():
        db.drop_all()

def test_me_accepts_raw_jwt_token():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="alex", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {"user_id": user.id, "username": user.username},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        user_id = user.id

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": token},
    )

    assert response.status_code == 200
    assert response.json == {"id": user_id, "username": "alex"}

    with app.app_context():
        db.drop_all()

def test_me_rejects_jwt_signed_with_wrong_secret():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="alex", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {"user_id": user.id, "username": user.username},
            "wrong-secret",
            algorithm="HS256",
        )

        db.session.expunge(user)
        db.drop_all()

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

def test_me_rejects_jwt_for_nonexistent_user():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        token = jwt.encode(
            {"user_id": 9999, "username": "unknown"},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()    

def test_me_rejects_expired_jwt():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="alex", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {
                "user_id": user.id,
                "username": user.username,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}

    with app.app_context():
        db.drop_all()


def test_format_validation_errors_flattens_nested_errors():
    messages = {
        "clock_in": ["Not a valid datetime."],
        "clock_out": ["Missing data."],
    }

    result = format_validation_errors(messages)

    assert result == [
        "clock_in: Not a valid datetime.",
        "clock_out: Missing data.",
    ]

def test_delete_shift_returns_404_for_nonexistent_shift():
    app = create_test_app()

    with app.app_context():
        db.create_all()

    client = app.test_client()

    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.delete("/shifts/999")

    assert response.status_code == 404
    assert response.json == {"errors": ["Shift not found"]}

    with app.app_context():
        assert Shift.query.count() == 0
        db.drop_all()

def test_update_shift_can_reopen_a_closed_shift():
    app = create_test_app()

    with app.app_context():
        db.create_all()
        shift = Shift(
            user_id=12,
            clock_in=datetime(2026, 10, 31, 8, 30),
            clock_out=datetime(2026, 10, 31, 16, 30),
        )
        db.session.add(shift)
        db.session.commit()
        shift_id = shift.id

    client = app.test_client()

    with client.session_transaction() as user_session:
        user_session["user_id"] = 12

    response = client.patch(
        f"/shifts/{shift_id}",
        json={"clock_out": None},
    )

    assert response.status_code == 200
    assert response.json["clock_out"] is None

    with app.app_context():
        saved_shift = db.session.get(Shift, shift_id)
        assert saved_shift.clock_out is None
        db.drop_all()        

def test_me_rejects_token_for_deleted_user():
    app = create_test_app()

    with app.app_context():
        db.create_all()

        user = User(username="deleted_user", password_hash="hashed-password")
        db.session.add(user)
        db.session.commit()

        token = jwt.encode(
            {"user_id": user.id, "username": user.username},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        db.session.delete(user)
        db.session.commit()

    client = app.test_client()
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json == {"errors": ["Authentication required"]}        