# Productivity API

A Flask API for a productivity app. It provides session-based authentication, JWT login responses with a JWT-protected current-user endpoint, a user-owned notes resource, and paginated shift CRUD with clock-in/clock-out workflows.

## Team Contributions

| Assignment | Responsibility | Contributor |
|---|---|---|
| Person A | Project setup and database foundation | Victor Kingara |
| Person B | Authentication | Faith Nderitu |
| Person C | Shift CRUD and pagination | Humphrey |
| Person D | Shift clock-in/clock-out logic and ownership security | Lerionka Olentiki |
| Person E | Testing, documentation, and final delivery | Timothy Koigi and Anord |

The descriptions below summarize the responsibilities and delivered work for each assigned workstream.

### Person A — Victor Kuria: Project Setup and Database Foundation

- Set up the Flask application structure, configuration, and shared SQLAlchemy database extension.
- Defined the database models for users, notes, and shifts, including keys, indexes, and relationships used by the API.
- Configured Flask-Migrate and added the initial Alembic migration so a new database can be created consistently with `db upgrade`.
- Prepared the Faker-based seed utility for repeatable local demonstration data.

### Person B — Faith Nderitu: Authentication

- Implemented signup and login, including validation, bcrypt password hashing, and duplicate-username handling.
- Added session creation and the session-check and logout endpoints used by the session-based client.
- Added JWT creation at signup/login and `GET /me` to verify a JWT and return its user.
- Kept authentication errors in JSON responses and ensured passwords are never returned by user serialization.

### Person C — Humphrey: Shift CRUD and Pagination

- Implemented the shift resource endpoints: list with pagination, create, retrieve one, update, and delete.
- Restricted shift reads and mutations to the current session user; other users' shifts are returned as not found.
- Used the shift schemas for timestamp validation and response serialization, and applied the rules that clock-out follows clock-in and a user has at most one active shift.
- Added support for page/per-page controls, including defaults and a maximum page size.

### Person D — Lerionka Olentiki: Clock-in/out Workflow and Ownership Security

- Implemented `POST /shifts/clock-in` (also available as `POST /shifts`) to record server-side UTC clock-in time.
- Prevented a user from starting another shift while they already have an active shift.
- Implemented `PATCH /shifts/<shift_id>/clock-out` to close the active shift using server-side UTC time.
- Scoped the clock-out lookup by both shift ID and session user ID; missing or non-owned shifts return 404.
- Rejected clocking out an already closed shift and enforced clock-out later than clock-in.
- Added focused tests for clock-in/out, duplicate clock-in prevention, authentication, and ownership boundaries.

### Person E — Timothy Koigi and Anord: Testing, Documentation, and Final Delivery

**Timothy Koigi — Testing and Integration**

- Expanded pytest coverage for authentication, validation, shift CRUD, pagination, clock-in/out rules, and user ownership isolation.
- Ran the backend test suite and checked that a user cannot read, update, or delete another user's shift.
- Verified the API's migration and seed workflow on a fresh local database.

**Anord — Documentation and Delivery**

- Updated this README with setup steps, migration and seed commands, authentication behavior, endpoint details, example requests, and project layout.
- Organized the hand-off information so the frontend team can identify the required session cookie and API paths.
- Prepared the project for final integration and submission, including a final check of the documented workflow.

## Features

- Sign up and log in with passwords stored as bcrypt hashes.
- Session cookies for the session-based client.
- JWTs returned at login and signup, with `GET /me` for JWT verification.
- Notes CRUD and pagination, scoped to the logged-in session user.
- Paginated shift CRUD and clock-in/clock-out with ownership checks and duplicate-clock-in protection.

## Requirements

- Python 3.8 or newer
- Pipenv
- Git

## Install and Run

From the repository root:

```bash
pipenv install --dev
```

Set a private secret key before running the app. Do not use the development fallback in a deployed environment.

```bash
export SECRET_KEY="replace-with-a-long-random-secret"
```

Optionally set `DATABASE_URL` to use a different SQLAlchemy database. By default, the app uses the SQLite database `shifts.db` in the instance directory.

Run the API on port 5555:

```bash
pipenv run python app.py
```

## Run a Frontend Client

The session client is configured to proxy API requests to the Flask server on port 5555. From a second terminal, start it with:

```bash
cd client-with-sessions
npm install
npm start
```

Open [http://localhost:4000](http://localhost:4000), choose Sign Up to create an account, then use those credentials to log in.

The JWT client is an alternative auth-flow example:

```bash
cd client-with-jwt
npm install
npm start
```

Both provided clients demonstrate authentication only. After login they show a placeholder page; the assignment does not provide a shift-tracker UI, so shifts are currently used through the documented API endpoints.

## Database Migrations and Seed Data

The initial Flask-Migrate revision is included in `migrations/versions`. Apply it to create the database tables:

```bash
pipenv run flask --app app db upgrade
```

After model changes, generate and apply a new migration:

```bash
pipenv run flask --app app db migrate -m "Describe the schema change"
pipenv run flask --app app db upgrade
```

Run the Faker seed script after applying migrations:

```bash
pipenv run python seed.py
```

The script creates up to three demo users and two completed shifts for each. It is safe to rerun: existing `demo_worker_1` through `demo_worker_3` users are left unchanged. Newly generated passwords are printed once when each demo user is created; save them if you need to log in. The script does not delete or overwrite existing records.

## Authentication

The API supports session cookies and issues JWTs, but protected resource routes currently authenticate using the Flask session cookie. The JWT is currently accepted by `GET /me`; it is not yet a substitute for the session on the notes or shifts endpoints.

For browser clients, send JSON requests with `Content-Type: application/json`. Keep the session cookie between requests.

| Method and Path | Authentication | Description |
|---|---|---|
| `POST /signup` | Public | Register a user, start a session, and return a JWT |
| `POST /login` | Public | Authenticate a user, start a session, and return a JWT |
| `GET /check_session` | Session cookie | Return the current session user or `{}` |
| `DELETE /logout` | Session cookie if logged in | Clear the current session |
| `GET /me` | JWT bearer token | Validate the token and return its user |

### POST /signup

Creates a user, hashes their password, starts a session, and returns a JWT. Username, password, and password confirmation are required. The username is limited to 80 characters, and the password confirmation must match.

**Request:**

```json
{
  "username": "alex",
  "password": "example-password",
  "password_confirmation": "example-password"
}
```

**Success response (201 Created):**

```json
{
  "id": 1,
  "username": "alex",
  "token": "<JWT>",
  "user": {
    "id": 1,
    "username": "alex"
  }
}
```

### POST /login

Authenticates an existing user and starts a session. The response has the same fields as signup; successful login returns `200 OK`. Invalid credentials return `401 Unauthorized`; malformed request bodies or missing credentials return `400 Bad Request`.

**Request:**

```json
{
  "username": "alex",
  "password": "example-password"
}
```

### GET /check_session

Returns the current session user:

```json
{
  "id": 1,
  "username": "alex"
}
```

If no valid session exists, returns `{}` with `200 OK`.

### DELETE /logout

Clears the current session and returns `{}` with `200 OK`.

### GET /me

Verifies a JWT and returns its user. Send the token in the Authorization header:

```http
Authorization: Bearer YOUR_JWT_TOKEN
```

Returns the user object with `200 OK`, or an authentication error with `401 Unauthorized`.

### Authentication Request Examples

Signup creates the session cookie and returns a JWT:

```bash
curl -i -c cookies.txt -H "Content-Type: application/json" \
  -d '{"username":"alex","password":"example-password","password_confirmation":"example-password"}' \
  http://localhost:5555/signup
```

Login uses the same cookie jar:

```bash
curl -i -c cookies.txt -b cookies.txt -H "Content-Type: application/json" \
  -d '{"username":"alex","password":"example-password"}' \
  http://localhost:5555/login
```

Use the returned token to verify JWT authentication:

```bash
curl -i -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:5555/me
```

`cookies.txt` contains an authentication cookie; keep it private and remove it when finished.

Check or clear the session with:

```bash
curl -i -b cookies.txt http://localhost:5555/check_session
curl -i -X DELETE -b cookies.txt http://localhost:5555/logout
```

## Notes

All notes endpoints require a logged-in session. Each query is scoped to the current user; a user cannot read, update, or delete another user's note.

| Method and Path | Description |
|---|---|
| `GET /notes?page=1&per_page=10` | Paginated list of the current user's notes |
| `POST /notes` | Create a note |
| `GET /notes/<note_id>` | Get one of the current user's notes |
| `PATCH /notes/<note_id>` | Update a note's title and/or content |
| `DELETE /notes/<note_id>` | Delete one of the current user's notes |

### GET /notes

Returns a page of the current user's notes. `page` defaults to 1; `per_page` defaults to 10 and is limited to a maximum of 100.

```http
GET /notes?page=1&per_page=10
```

**Response:**

```json
{
  "page": 1,
  "per_page": 10,
  "total": 1,
  "notes": [
    {
      "id": 1,
      "title": "Weekly plan",
      "content": "Finish tasks before Friday.",
      "user_id": 1
    }
  ]
}
```

### POST /notes

Creates a note for the current user. `title` is required; `content` defaults to an empty string.

```json
{
  "title": "Weekly plan",
  "content": "Finish tasks before Friday."
}
```

Returns the created note with `201 Created`.

### GET /notes/<note_id>

Returns one of the current user's notes. Returns `404 Not Found` if it does not exist or belongs to another user.

```bash
curl -i -b cookies.txt http://localhost:5555/notes/1
```

### PATCH /notes/<note_id>

Updates the supplied title and/or content fields. The title cannot be blank.

```json
{
  "title": "Updated plan"
}
```

Returns the updated note with `200 OK`.

```bash
curl -i -X PATCH -b cookies.txt -H "Content-Type: application/json" \
  -d '{"title":"Updated plan"}' http://localhost:5555/notes/1
```

### DELETE /notes/<note_id>

Deletes one of the current user's notes and returns `{}` with `200 OK`. Returns `404 Not Found` for missing notes or notes owned by another user.

**Example create request:**

```bash
curl -i -b cookies.txt -H "Content-Type: application/json" \
  -d '{"title":"Weekly plan","content":"Finish tasks before Friday."}' \
  http://localhost:5555/notes
```

**Delete example:**

```bash
curl -i -X DELETE -b cookies.txt http://localhost:5555/notes/1
```

## Shifts

Every shift endpoint requires a logged-in Flask session cookie and scopes the operation to that session's user ID. JWTs are issued by the auth endpoints, but JWT-only requests do not authenticate notes or shifts.

| Method and Path | Description |
|---|---|
| `GET /shifts?page=1&per_page=10` | Paginated list of the current user's shifts |
| `POST /shifts` | Create an active shift (clock in) |
| `POST /shifts/clock-in` | Alias for creating an active shift |
| `GET /shifts/<shift_id>` | Get one of the current user's shifts |
| `PATCH /shifts/<shift_id>` | Update `clock_in` and/or `clock_out` timestamps |
| `DELETE /shifts/<shift_id>` | Delete one of the current user's shifts |
| `PATCH /shifts/<shift_id>/clock-out` | Close an active shift using server time |

### GET /shifts

Lists only the current user's shifts, newest first. `page` defaults to 1; `per_page` defaults to 10 and is limited to a maximum of 100. Invalid or out-of-range values are clamped to supported values. Pages beyond the final page return an empty shifts list.

```bash
curl -i -b cookies.txt \
  "http://localhost:5555/shifts?page=1&per_page=10"
```

**Response:**

```json
{
  "page": 1,
  "per_page": 10,
  "total": 1,
  "shifts": [
    {
      "id": 1,
      "clock_in": "2026-10-31T08:30:00+00:00",
      "clock_out": null
    }
  ]
}
```

### POST /shifts and POST /shifts/clock-in

Both paths create a shift with the current UTC time as `clock_in` and `clock_out` set to `null`; do not provide timestamps in the request. Returns `201 Created`. If the user already has an active shift, returns `400 Bad Request`.

```bash
curl -i -X POST -b cookies.txt http://localhost:5555/shifts/clock-in
```

### GET /shifts/<shift_id>

Returns the requested shift if it belongs to the current user. Missing and non-owned shifts return `404 Not Found`.

```bash
curl -i -b cookies.txt http://localhost:5555/shifts/1
```

### PATCH /shifts/<shift_id>

Updates one or both timestamps. Values must be ISO 8601; timestamps without an offset are interpreted as UTC. Unknown fields, malformed values, empty payloads, and clock-out times not later than clock-in return `400 Bad Request`. `clock_out: null` reopens a shift only if the user has no other active shift.

```bash
curl -i -X PATCH -b cookies.txt -H "Content-Type: application/json" \
  -d '{"clock_in":"2026-10-31T08:30:00Z","clock_out":"2026-10-31T16:30:00Z"}' \
  http://localhost:5555/shifts/1
```

### PATCH /shifts/<shift_id>/clock-out

Closes the current user's active shift using the current UTC time. Returns the updated shift with `200 OK`. Returns `404 Not Found` if the shift does not exist or belongs to another user, and `400 Bad Request` if it is already closed.

```bash
curl -i -X PATCH -b cookies.txt http://localhost:5555/shifts/1/clock-out
```

### DELETE /shifts/<shift_id>

Deletes one of the current user's shifts and returns `{}` with `200 OK`. A missing or non-owned shift returns `404 Not Found`.

```bash
curl -i -X DELETE -b cookies.txt http://localhost:5555/shifts/1
```

## Error Responses

Errors use a JSON `errors` array. For example:

```json
{
  "errors": ["Authentication required"]
}
```

Common status codes are:

- `400` — Invalid input or business-rule violations.
- `401` — Missing or invalid authentication.
- `404` — A resource is not found or is not owned by the current user.

## Tests

Run the test suite with:

```bash
pipenv run pytest
```

Automated tests are organized in:

- `tests/test_app.py` — Shift endpoints, schemas, auth flows, and seed behavior.
- `tests/test_auth.py` — Authentication.
- `tests/test_notes.py` — Notes routes.

Run `pipenv run pytest` to execute all of them.

## Project Layout

```text
.
├── app.py
├── config.py
├── models.py
├── auth_routes.py
├── note_routes.py
├── shift_routes.py
├── shift_schemas.py
├── seed.py
├── migrations/
└── tests/
```

- `app.py` — Flask application factory and blueprint registration.
- `config.py` — Application and database configuration.
- `models.py` — Database, user, note, and shift models.
- `auth_routes.py` — Signup, login, session, logout, and JWT `/me` routes.
- `note_routes.py` — Protected notes CRUD and pagination.
- `shift_routes.py` — Protected shift CRUD, pagination, and clock-in/clock-out.
- `shift_schemas.py` — Shift validation and serialization schemas.
- `seed.py` — Creates sample users and shifts for local development.
- `migrations/` — Tracked Alembic migration history.
- `tests/` — Pytest tests.