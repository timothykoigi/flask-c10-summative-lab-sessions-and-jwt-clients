from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from marshmallow import ValidationError

from server.models.models import Shift, db
from server.schemas.shift_schemas import ShiftSchema, ShiftUpdateSchema


shift_routes = Blueprint("shift_routes", __name__)
shift_schema = ShiftSchema()
shift_update_schema = ShiftUpdateSchema()


def format_validation_errors(messages, field_path=None):
    errors = []
    if isinstance(messages, dict):
        for field, field_messages in messages.items():
            path = (
                field_path
                if field == "_schema"
                else f"{field_path}.{field}"
                if field_path
                else field
            )
            errors.extend(format_validation_errors(field_messages, path))
    elif isinstance(messages, list):
        for message in messages:
            errors.extend(format_validation_errors(message, field_path))
    else:
        errors.append(f"{field_path}: {messages}" if field_path else str(messages))
    return errors


def get_session_user_id():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return user_id


@shift_routes.get("/shifts")
def list_shifts():
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(max(1, request.args.get("per_page", default=10, type=int)), 100)
    pagination = (
        Shift.query.filter_by(user_id=user_id)
        .order_by(Shift.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return (
        jsonify(
            {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "shifts": [shift_schema.dump(shift) for shift in pagination.items],
            }
        ),
        200,
    )


@shift_routes.post("/shifts")
@shift_routes.post("/shifts/clock-in")
def clock_in():
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    data = request.get_json(silent=True)
    if request.get_data(cache=True) and data != {}:
        return jsonify({"errors": ["Clock-in timestamps are set by the server"]}), 400

    active_shift = Shift.query.filter_by(user_id=user_id, clock_out=None).first()
    if active_shift is not None:
        return jsonify({"errors": ["You are already clocked in"]}), 409

    shift = Shift(user_id=user_id, clock_in=datetime.now(timezone.utc))
    db.session.add(shift)
    db.session.commit()

    return jsonify(shift_schema.dump(shift)), 201


@shift_routes.get("/shifts/<int:shift_id>")
def show_shift(shift_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    shift = Shift.query.filter_by(id=shift_id, user_id=user_id).first()
    if shift is None:
        return jsonify({"errors": ["Shift not found"]}), 404

    return jsonify(shift_schema.dump(shift)), 200


@shift_routes.patch("/shifts/<int:shift_id>")
def update_shift(shift_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    shift = Shift.query.filter_by(id=shift_id, user_id=user_id).first()
    if shift is None:
        return jsonify({"errors": ["Shift not found"]}), 404

    request_data = request.get_json(silent=True)
    if not isinstance(request_data, dict) or not request_data:
        return jsonify({"errors": ["A JSON object with shift fields is required"]}), 400

    try:
        data = shift_update_schema.load(request_data)
        clock_in = data.get("clock_in", shift.clock_in)
        clock_out = data.get("clock_out", shift.clock_out)
        candidate = shift_schema.load(
            {
                "clock_in": clock_in.isoformat(),
                "clock_out": clock_out.isoformat() if clock_out is not None else None,
            }
        )
    except ValidationError as error:
        return jsonify({"errors": format_validation_errors(error.messages)}), 400

    clock_in = candidate["clock_in"]
    clock_out = candidate.get("clock_out")

    if clock_out is None:
        active_shift = Shift.query.filter(
            Shift.user_id == user_id,
            Shift.clock_out.is_(None),
            Shift.id != shift.id,
        ).first()
        if active_shift is not None:
            return jsonify({"errors": ["You are already clocked in"]}), 409

    shift.clock_in = clock_in
    shift.clock_out = clock_out
    db.session.commit()

    return jsonify(shift_schema.dump(shift)), 200


@shift_routes.delete("/shifts/<int:shift_id>")
def delete_shift(shift_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    shift = Shift.query.filter_by(id=shift_id, user_id=user_id).first()
    if shift is None:
        return jsonify({"errors": ["Shift not found"]}), 404

    db.session.delete(shift)
    db.session.commit()
    return jsonify({}), 200


@shift_routes.patch("/shifts/<int:shift_id>/clock-out")
def clock_out(shift_id):
    user_id = get_session_user_id()
    if user_id is None:
        return jsonify({"errors": ["Authentication required"]}), 401

    shift = Shift.query.filter_by(id=shift_id, user_id=user_id).first()
    if shift is None:
        return jsonify({"errors": ["Shift not found"]}), 404

    if shift.clock_out is not None:
        return jsonify({"errors": ["This shift is already clocked out"]}), 409

    clock_out_time = datetime.now(timezone.utc)
    clock_in_time = shift.clock_in
    if clock_in_time.tzinfo is None:
        clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)

    if clock_out_time <= clock_in_time:
        return jsonify({"errors": ["Clock-out must be after clock-in"]}), 400

    shift.clock_out = clock_out_time
    db.session.commit()

    return jsonify(shift_schema.dump(shift)), 200
