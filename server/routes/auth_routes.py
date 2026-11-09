from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import Bcrypt


from server.models.models import User, bcrypt, db

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None


auth_routes = Blueprint("auth_routes", __name__)
bcrypt = Bcrypt()


def serialize_user(user):
    return {"id": user.id, "username": user.username}


def create_token(user):
    if jwt is None:
        return None
    payload = {"user_id": user.id, "username": user.username}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def get_current_user_from_token():
    if jwt is None:
        return None

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif auth_header.startswith("JWT "):
        token = auth_header.split(" ", 1)[1]
    elif auth_header:
        token = auth_header

    if not token:
        return None

    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except Exception:
        return None

    return db.session.get(User, payload.get("user_id"))


@auth_routes.post("/signup")
def signup():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"errors": ["Request body must be a JSON object"]}), 400

    username_value = data.get("username")
    username = username_value.strip() if isinstance(username_value, str) else ""
    password = data.get("password")
    password_confirmation = data.get("password_confirmation")

    errors = []
    if not username:
        errors.append("Username is required")
    elif len(username) > 80:
        errors.append("Username must be 80 characters or fewer")
    if not isinstance(password, str) or not password:
        errors.append("Password is required")
    if not isinstance(password_confirmation, str) or not password_confirmation:
        errors.append("Password confirmation is required")
    elif isinstance(password, str) and password != password_confirmation:
        errors.append("Passwords do not match")
    if username and User.query.filter_by(username=username).first() is not None:
        errors.append("Username already exists")

    if errors:
        status = 409 if errors == ["Username already exists"] else 400
        return jsonify({"errors": errors}), status
    
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(username=username, password_hash=password_hash)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": ["Username already exists"]}), 409

    session["user_id"] = user.id
    user_data = serialize_user(user)
    response = {**user_data, "token": create_token(user), "user": user_data}
    return jsonify(response), 201


@auth_routes.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"errors": ["Request body must be a JSON object"]}), 400

    username_value = data.get("username")
    password = data.get("password")
    if not isinstance(username_value, str) or not username_value.strip():
        return jsonify({"errors": ["Username is required"]}), 400
    if not isinstance(password, str) or not password:
        return jsonify({"errors": ["Password is required"]}), 400

    username = username_value.strip()

    user = User.query.filter_by(username=username).first()
    if user is None or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"errors": ["Invalid username or password"]}), 401

    session["user_id"] = user.id
    user_data = serialize_user(user)
    response = {**user_data, "token": create_token(user), "user": user_data}
    return jsonify(response), 200


@auth_routes.get("/check_session")
def check_session():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    user = db.session.get(User, user_id)
    if user is None:
        session.pop("user_id", None)
        return jsonify({"errors": ["Authentication required"]}), 401

    return jsonify(serialize_user(user)), 200


@auth_routes.delete("/logout")
def logout():
    session.clear()
    return jsonify({}), 200


@auth_routes.get("/me")
def me():
    user = get_current_user_from_token()
    if user is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    return jsonify(serialize_user(user)), 200
