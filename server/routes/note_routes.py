from flask import Blueprint, jsonify, request, session

from server.models.models import Note, db

note_routes = Blueprint("note_routes", __name__)


def serialize_note(note):
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "user_id": note.user_id,
    }


def get_session_user_id():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return user_id


@note_routes.get("/notes")
def list_notes():
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)
    page = max(1, page)
    per_page = min(max(1, per_page), 100)

    pagination = Note.query.filter_by(user_id=user_id).order_by(Note.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return (
        jsonify(
            {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "notes": [serialize_note(note) for note in pagination.items],
            }
        ),
        200,
    )


@note_routes.post("/notes")
def create_note():
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    data = request.get_json(silent=True) 
    if not isinstance(data, dict): 
        return jsonify({"errors": ["Request body must be a JSON object"]}), 400
    title = (data.get("title") or "").strip()
    title = str(title) if title is not None else "" 
    content = data.get("content", "")

    if not title:
        return jsonify({"errors": ["Title is required"]}), 400

    note = Note(title=title, content=content, user_id=user_id)
    db.session.add(note)
    db.session.commit()

    return jsonify(serialize_note(note)), 201


@note_routes.get("/notes/<int:note_id>")
def show_note(note_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    note = Note.query.filter_by(id=note_id, user_id=user_id).first()
    if note is None:
        return jsonify({"errors": ["Note not found"]}), 404

    return jsonify(serialize_note(note)), 200


@note_routes.patch("/notes/<int:note_id>")
def update_note(note_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    note = Note.query.filter_by(id=note_id, user_id=user_id).first()
    if note is None:
        return jsonify({"errors": ["Note not found"]}), 404

    data = request.get_json(silent=True) 
    if not isinstance(data, dict): 
        return jsonify({"errors": ["Request body must be a JSON object"]}), 400
    title = data.get("title")
    content = data.get("content")

    if title is not None:
        title = (str(title)).strip()
        if not title:
            return jsonify({"errors": ["Title is required"]}), 400
        note.title = title

    if content is not None:
        note.content = content

    db.session.commit()
    return jsonify(serialize_note(note)), 200


@note_routes.delete("/notes/<int:note_id>")
def delete_note(note_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    note = Note.query.filter_by(id=note_id, user_id=user_id).first()
    if note is None:
        return jsonify({"errors": ["Note not found"]}), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify({}), 200
