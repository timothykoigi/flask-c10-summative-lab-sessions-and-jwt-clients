from datetime import datetime, timezone

from marshmallow import RAISE, Schema, ValidationError, fields, validates_schema


class UTCDateTime(fields.DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        parsed = super()._deserialize(value, attr, data, **kwargs)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return super()._serialize(value, attr, obj, **kwargs)


class ShiftSchema(Schema):
    id = fields.Int(dump_only=True)
    clock_in = UTCDateTime(required=True)
    clock_out = UTCDateTime(allow_none=True)

    class Meta:
        unknown = RAISE

    @validates_schema
    def validate_shift_times(self, data, **kwargs):
        clock_in = data["clock_in"]
        clock_out = data.get("clock_out")
        if clock_out is not None and clock_out <= clock_in:
            raise ValidationError("Clock-out must be after clock-in")


class ShiftUpdateSchema(Schema):
    clock_in = UTCDateTime()
    clock_out = UTCDateTime(allow_none=True)

    class Meta:
        unknown = RAISE

    @validates_schema
    def validate_shift_times(self, data, **kwargs):
        clock_in = data.get("clock_in")
        clock_out = data.get("clock_out")
        if (
            clock_in is not None
            and clock_out is not None
            and clock_out <= clock_in
        ):
            raise ValidationError("Clock-out must be after clock-in")
