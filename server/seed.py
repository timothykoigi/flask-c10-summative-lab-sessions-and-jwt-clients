from datetime import datetime, timedelta, timezone
from faker import Faker
from flask_bcrypt import Bcrypt
from server.app import create_app
from server.models.models import Note, Shift, User, db


fake = Faker()
bcrypt = Bcrypt()


def seed_database(user_count=3):
    created_credentials = []
    now = datetime.now(timezone.utc)

    for index in range(1, user_count + 1):
        username = f"demo_worker_{index}"
        user = User.query.filter_by(username=username).first()
        if user is None:
            password = fake.password(length=16)
            user = User(
                username=username,
                password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            )
            db.session.add(user)
            db.session.flush()
            created_credentials.append((username, password))

            for days_ago in range(1, 16):
                clock_in = now - timedelta(
                    days=days_ago,
                    hours=fake.random_int(min=1, max=8),
                )
                db.session.add(
                    Shift(
                        user_id=user.id,
                        clock_in=clock_in,
                        clock_out=clock_in + timedelta(hours=8),
                    )
                )

            if index == 2:
                db.session.add(Note(
                        title=fake.sentence(nb_words=4).rstrip("."),
                        content=fake.paragraph(nb_sentences=2),
                        user_id=user.id,
                    ))

    db.session.commit()
    return created_credentials


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        credentials = seed_database()

    if credentials:
        print("Created demo users (save these generated passwords):")
        for username, password in credentials:
            print(f"{username}: {password}")
    else:
        print("Demo users already exist; no seed data was added.")
