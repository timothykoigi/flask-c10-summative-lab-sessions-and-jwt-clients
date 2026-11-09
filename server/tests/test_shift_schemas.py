
from datetime import datetime, timedelta, timezone

import pytest
from marshmallow import ValidationError

from server.schemas.shift_schemas import UTCDateTime
from server.schemas.shift_schemas import ShiftSchema, ShiftUpdateSchema


def test_shift_schema_accepts_valid_shift():
    data = {
        "clock_in": "2026-11-03T08:00:00Z",
        "clock_out": "2026-11-03T17:00:00Z",
    }

    result = ShiftSchema().load(data)

    assert result["clock_in"] == datetime(2026, 11, 3, 8, tzinfo=timezone.utc)
    assert result["clock_out"] == datetime(2026, 11, 3, 17, tzinfo=timezone.utc)


def test_shift_schema_requires_clock_in():
    with pytest.raises(ValidationError):
        ShiftSchema().load({"clock_out": None})


def test_shift_schema_accepts_null_clock_out():
    data = {"clock_in": "2026-11-03T08:00:00Z", "clock_out": None}

    result = ShiftSchema().load(data)

    assert result["clock_out"] is None


def test_shift_schema_rejects_clock_out_before_clock_in():
    data = {
        "clock_in": "2026-11-03T17:00:00Z",
        "clock_out": "2026-11-03T08:00:00Z",
    }

    with pytest.raises(ValidationError, match="Clock-out must be after clock-in"):
        ShiftSchema().load(data)


def test_shift_schema_rejects_equal_clock_times():
    data = {
        "clock_in": "2026-11-03T08:00:00Z",
        "clock_out": "2026-11-03T08:00:00Z",
    }

    with pytest.raises(ValidationError, match="Clock-out must be after clock-in"):
        ShiftSchema().load(data)


def test_shift_schema_rejects_unknown_fields():
    data = {
        "clock_in": "2026-11-03T08:00:00Z",
        "unexpected": "value",
    }

    with pytest.raises(ValidationError):
        ShiftSchema().load(data)


def test_shift_update_schema_accepts_valid_update():
    data = {
        "clock_in": "2026-11-03T09:00:00Z",
        "clock_out": "2026-11-03T18:00:00Z",
    }

    result = ShiftUpdateSchema().load(data)

    assert result["clock_in"] == datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
    assert result["clock_out"] == datetime(2026, 11, 3, 18, tzinfo=timezone.utc)


def test_shift_update_schema_accepts_partial_update():
    data = {"clock_in": "2026-11-03T09:00:00Z"}

    result = ShiftUpdateSchema().load(data)

    assert result["clock_in"] == datetime(2026, 11, 3, 9, tzinfo=timezone.utc)


def test_shift_update_schema_rejects_invalid_time_order():
    data = {
        "clock_in": "2026-11-03T17:00:00Z",
        "clock_out": "2026-11-03T08:00:00Z",
    }

    with pytest.raises(ValidationError, match="Clock-out must be after clock-in"):
        ShiftUpdateSchema().load(data)


def test_shift_update_schema_rejects_unknown_fields():
    data = {"unexpected": "value"}

    with pytest.raises(ValidationError):
        ShiftUpdateSchema().load(data)

def test_utc_datetime_treats_naive_datetime_as_utc():
    field = UTCDateTime()

    result = field.deserialize("2026-11-03T08:00:00")

    assert result == datetime(2026, 11, 3, 8, tzinfo=timezone.utc)


def test_utc_datetime_converts_timezone_to_utc():
    field = UTCDateTime()

    result = field.deserialize("2026-11-03T11:00:00+03:00")

    assert result == datetime(2026, 11, 3, 8, tzinfo=timezone.utc)      

def test_utc_datetime_serializes_naive_datetime_as_utc():
    field = UTCDateTime()

    result = field.serialize(
        "clock_in",
        {"clock_in": datetime(2026, 11, 3, 8, 0, 0)},
    )

    assert result == "2026-11-03T08:00:00+00:00"


def test_utc_datetime_serializes_timezone_aware_datetime_as_utc():
    field = UTCDateTime()

    result = field.serialize(
        "clock_in",
        {
            "clock_in": datetime(
                2026, 11, 3, 11, 0, 0,
                tzinfo=timezone(timedelta(hours=3)),
            )
        },
    )

    assert result == "2026-11-03T08:00:00+00:00"      