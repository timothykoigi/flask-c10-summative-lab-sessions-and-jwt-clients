# Productivity API

A Flask API for a productivity app. It provides session-based authentication, JWT login responses with a JWT-protected current-user endpoint, a user-owned notes resource, and paginated shift CRUD with clock-in/clock-out workflows.

## Project Overview

The Productivity API helps users manage their productivity activities through a single application. Users can create accounts, log in, manage personal notes, and record their working hours.

The backend is built with Flask and provides protected resources to ensure that users can only access their own information.

The project includes two React frontend clients: one designed for JWT authentication and another designed for session-based authentication.

## Project Objectives

- Provide secure user registration and login.
- Allow users to create and manage personal notes.
- Support pagination when retrieving notes.
- Record employee shift start and finish times.
- Protect user data through authentication and ownership checks.
- Provide automated tests for important application functionality.

## Team Contributions

| Assignment | Responsibility | Contributor |
|---|---|---|
| Person A | Project setup and database foundation | Victor Kuria |
| Person B | Authentication | Faith Nderitu |
| Person C | Shift CRUD and pagination | Humphrey |
| Person D | Shift clock-in/clock-out logic and ownership security | Lerionka Olentiki |
| Person E | Testing | Timothy Koigi |
| Person F | Documentation and final delivery | Anord |

### Contribution details

- **Victor Kuria — setup and database:** established the Flask/SQLAlchemy project foundation, application configuration, database models, and migration setup.
- **Faith Nderitu — authentication:** implemented signup/login, password hashing, session handling, and JWT issuance and verification.
- **Humphrey — shift CRUD and pagination:** implemented the user-scoped shift list, create, retrieve, update, and delete operations with pagination.
- **Lerionka Olentiki — clock-in/out and ownership:** implemented the server-timestamped clock-in/out workflow, active-shift rules, and owner checks.
- **Timothy Koigi — testing:** expanded automated coverage for authentication, validation, notes, shift routes, pagination, and ownership.
- **Anord — documentation and delivery:** documented setup, migration and seed usage, authentication behavior, endpoints, and example requests for handoff.

## Features

- User registration and login.
- Password hashing using bcrypt.
- Session-based authentication using Flask session cookies.
- JWT generation during signup and login.
- JWT-protected current-user endpoint.
- Personal notes CRUD operations.
- Notes pagination.
- Shift clock-in and clock-out.
- User ownership protection for notes and shifts.
- Automated backend testing.

## Technologies Used

### Backend

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Bcrypt
- PyJWT
- SQLite
- pytest

### Frontend

- React 17
- React Router
- styled-components
- npm

The project contains two frontend applications:

- `client-with-jwt` — JWT-based authentication client.
- `client-with-sessions` — session-based authentication client.

### Development Tools

- Pipenv
- Git
- GitHub
- VS Code

## Project Structure

productivity-api/
│
├── app.py
├── config.py
├── models.py
├── auth_routes.py
├── note_routes.py
├── shift_routes.py
├── Pipfile
├── Pipfile.lock
├── pytest.ini
│
├── migrations/
│
├── tests/
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_notes.py
│   └── test_shift_schemas.py
│
├── client-with-jwt/
│   ├── package.json
│   └── src/
│
└── client-with-sessions/
    ├── package.json
    └── src/

### Important Files

| File | Description |
|---|---|
| `app.py` | Creates the Flask application and registers routes. |
| `config.py` | Contains application and database configuration. |
| `models.py` | Defines database models and relationships. |
| `auth_routes.py` | Handles registration, login, sessions and JWT verification. |
| `note_routes.py` | Handles notes operations and pagination. |
| `shift_routes.py` | Handles protected shift CRUD, pagination, and clock-in/out. |
| `shift_schemas.py` | Validates and serializes shift data. |
| `seed.py` | Creates demo users and sample notes/shifts. |
| `migrations/` | Stores database migration files. |
| `tests/` | Contains automated backend tests, including shift schema tests. |

## Requirements

Before running the project, install:

- Python 3.10 or newer
- Pipenv
- Node.js and npm
- Git

## Installation and Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd <repository-folder>
```
### 2. Install backend dependencies

Install the exact dependency versions recorded in the lock file:

```bash
pipenv install --dev 
```

### 3. Configure environment variables

Set a secure secret key:

```bash
export SECRET_KEY="your-long-random-secret"
```

Optionally configure a different database:

```bash
export DATABASE_URL="your-database-connection-url"
```

By default, the application uses SQLite with a database named `shifts.db` in the instance directory.

### 4. Set up the database

The migration repository and initial migration are already included. Apply all
tracked migrations to create or update the database:

```bash
pipenv run flask --app app db upgrade
```

For future model changes:

```bash
pipenv run flask --app server.app db migrate -m "Describe the schema change"
pipenv run flask --app server.app db upgrade
```

### 5. Add demo data

After applying migrations, populate the database with demo users and sample
records:

```bash
pipenv run python seed.py
```

The script creates up to three demo users, 15 completed shifts for each new
user, and a sample note. It is safe to rerun: existing demo users are not
overwritten. Generated passwords are printed only when a user is first created;
save them if you need to sign in as a demo user.

### 6. Start the backend
```bash
pipenv run python -m server.app
```
The backend runs on port `5555`.

### 7. Start the JWT frontend

Open another terminal:

```bash
cd client-with-jwt
npm install
npm start
```


### 8. Start the session-based frontend

Open another terminal:

```bash
cd client-with-sessions
npm install
npm start
```


Both frontend clients proxy API requests to the Flask backend on port `5555`.

## Authentication

The API supports both session-based authentication and JWT generation.

### Session Authentication

The session-based client uses Flask session cookies to maintain the authenticated user's identity.

Protected notes and shift endpoints currently require a valid Flask session.

### JWT Authentication

The API returns a JWT during signup and login.

The JWT is accepted by:

`GET /me`

Send the token through the Authorization header:

```http
Authorization: Bearer <JWT>
```

**Important:** JWT authentication is currently used for the `/me` endpoint. It does not replace session authentication for notes and shifts.

## API Documentation

Send JSON requests using:

```http
Content-Type: application/json
```

Keep the session cookie between requests when accessing session-protected endpoints.

### Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/signup` | Register a new user. |
| POST | `/login` | Authenticate an existing user. |
| GET | `/check_session` | Check the current session. |
| DELETE | `/logout` | Clear the current session. |
| GET | `/me` | Verify a JWT and retrieve its user. |

### Signup

`POST /signup`

Example request:

```json
{
  "username": "alex",
  "password": "example-password",
  "password_confirmation": "example-password"
}
```

Returns `201 Created` when registration succeeds.

### Login

`POST /login`

Example request:

```json
{
  "username": "alex",
  "password": "example-password"
}
```

Returns `200 OK` when authentication succeeds and `401 Unauthorized` for invalid credentials.

### Notes Endpoints

All notes endpoints require a logged-in session.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/notes` | Retrieve the current user's notes. |
| POST | `/notes` | Create a new note. |
| GET | `/notes/<note_id>` | Retrieve a specific note. |
| PATCH | `/notes/<note_id>` | Update a note. |
| DELETE | `/notes/<note_id>` | Delete a note. |

### Notes Pagination

Use query parameters to control pagination:

```http
GET /notes?page=1&per_page=10
```

- `page` defaults to 1.
- `per_page` defaults to 10.
- The maximum `per_page` value is 100.

### Create a Note

`POST /notes`

```json
{
  "title": "Weekly plan",
  "content": "Complete project tasks before Friday."
}
```

The title is required. Content defaults to an empty string.

### Update a Note

`PATCH /notes/<note_id>`

```json
{
  "title": "Updated weekly plan"
}
```

### Shift Endpoints

All shift endpoints require a logged-in session.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/shifts` | List the current user's shifts, newest first. |
| POST | `/shifts` or `/shifts/clock-in` | Start a shift using server UTC time. |
| GET | `/shifts/<shift_id>` | Retrieve one of the current user's shifts. |
| PATCH | `/shifts/<shift_id>` | Update validated shift timestamps. |
| DELETE | `/shifts/<shift_id>` | Delete one of the current user's shifts. |
| PATCH | `/shifts/<shift_id>/clock-out` | Finish an active shift using server UTC time. |

### Clock In

`POST /shifts/clock-in`

Creates a shift using the current UTC time.

`GET /shifts` lists only the current user's shifts, newest first. `page`
defaults to `1`; `per_page` defaults to `10` and is limited to a maximum of
`100`. Invalid or out-of-range values are clamped to supported values. Pages
beyond the final page return an empty `shifts` list.

```bash
curl -i -b cookies.txt \
  "http://localhost:5555/shifts?page=1&per_page=10"
```

Response:

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

A user cannot start another shift while an active shift exists.

An active shift conflict returns `409 Conflict`. Invalid request data returns
`400 Bad Request`.

### Clock Out

`PATCH /shifts/<shift_id>/clock-out`

Closes the specified active shift if it belongs to the logged-in user.

Another user's shift returns `404 Not Found`. A shift that is already closed returns `409 Conflict`.

## Error Responses

Errors are returned in JSON format.

Example:

```json
{
  "errors": ["Authentication required"]
}
```

Common HTTP status codes:

| Status | Meaning |
|---|---|
| 200 | Request successful. |
| 201 | Resource created successfully. |
| 400 | Invalid input or business-rule violation. |
| 401 | Authentication required or invalid. |
| 404 | Resource not found or not owned by the current user. |
| 409 | Conflict, such as clocking in while a shift is already active. |

## Testing

The backend uses pytest for automated testing.

Run the complete test suite:

```bash
pipenv run pytest
```

Run tests with detailed output:

```bash
pipenv run pytest -v
```

The test suite includes tests for application, authentication, notes and shift functionality.

## Security Considerations

- Passwords are stored as bcrypt hashes.
- Protected resources require authentication.
- Notes and shifts are scoped to the current user.
- JWTs are verified before the `/me` endpoint returns user information.
- A secure `SECRET_KEY` should be configured before deployment.
- Secret keys and other private credentials should not be committed to GitHub.

## Future Improvements

The following are possible improvements for future development:

1. Extend JWT authentication to protected notes and shift endpoints if token-based access is required.
2. Build shift history and clock-in/clock-out screens in the frontend clients.
3. Add API documentation using Swagger or OpenAPI.
4. Add deployment instructions and production environment configuration.


## Team Contribution and Collaboration

The project is developed collaboratively using Git and GitHub.

Recommended workflow:

1. Pull the latest changes from the team's `main` branch.
2. Create or switch to your assigned feature branch.
3. Implement your assigned work.
4. Run the relevant tests.
5. Commit changes using clear commit messages.
6. Push your branch to GitHub.
7. Open a pull request for team review.


## Conclusion

The Productivity API provides a foundation for user authentication, personal notes management and employee shift tracking. It combines a Flask backend with two React authentication clients and can be extended with additional productivity features in future development.
