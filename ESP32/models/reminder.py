"""Reminder model for the ESP32 MicroPython application."""


class Reminder:
    """Represent a single reminder received from the backend API."""

    def __init__(self, assignment_id, elderly_id, activity, message, scheduled_time):
        """Initialize a reminder with backend-provided data."""

        self.assignment_id = assignment_id
        self.elderly_id = elderly_id
        self.activity = activity
        self.message = message
        self.scheduled_time = scheduled_time

    @classmethod
    def from_dict(cls, data):
        """Build a reminder instance from a dictionary payload."""

        return cls(
            assignment_id=data.get("assignment_id"),
            elderly_id=data.get("elderly_id"),
            activity=data.get("activity"),
            message=data.get("message"),
            scheduled_time=data.get("scheduled_time"),
        )
