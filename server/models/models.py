from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    """Application user."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")
    shifts = db.relationship("Shift", back_populates="user", cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, plain_text):
        self.password_hash = bcrypt.generate_password_hash(plain_text).decode("utf-8")


    def __repr__(self):
        return f"<User {self.username}>"


class Note(db.Model):
    """A user-owned note."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_shift_user_id_user"),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note {self.id} user={self.user_id}>"


class Shift(db.Model):
    """A single work shift owned by one user."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    clock_in = db.Column(db.DateTime(timezone=True), nullable=False)
    clock_out = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="shifts")

    def __repr__(self):
        return f"<Shift {self.id} user={self.user_id}>"
