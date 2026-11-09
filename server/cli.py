
import json
import os
import sys
from datetime import datetime, timezone
from getpass import getpass
from http.cookiejar import MozillaCookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5555").rstrip("/")
COOKIE_FILE = os.path.expanduser("~/.shift_cli_cookies")
PER_PAGE = 10

cookies = MozillaCookieJar(COOKIE_FILE)
if os.path.exists(COOKIE_FILE):
    try:
        cookies.load(ignore_discard=True, ignore_expires=True)
    except OSError:
        pass
opener = build_opener(HTTPCookieProcessor(cookies))


class ApiError(Exception):
    """Raised when the API cannot be reached."""


def call(method, path, body=None):
    """Send a request and return (status_code, parsed_json_or_empty_dict)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(API_URL + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with opener.open(request) as response:
            status, raw = response.status, response.read()
    except HTTPError as error:
        status, raw = error.code, error.read()
    except URLError:
        raise ApiError(f"Cannot reach the API at {API_URL}. Is the Flask server running?")
    cookies.save(ignore_discard=True, ignore_expires=True)
    try:
        return status, json.loads(raw) if raw else {}
    except ValueError:
        return status, {}


def show_errors(status, data):
    errors = data.get("errors") if isinstance(data, dict) else None
    print(f"  Failed ({status}): " + ("; ".join(errors) if errors else "unexpected response"))


def fmt_time(value):
    if not value:
        return "-"
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def ask(prompt):
    return input(prompt).strip()


def ask_id(prompt):
    value = ask(prompt)
    if not value.isdigit():
        print("  Please enter a number.")
        return None
    return int(value)


# account 

def current_user():
    status, data = call("GET", "/check_session")
    return data if status == 200 and data.get("id") else None


def signup():
    username = ask("Username: ")
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    status, data = call("POST", "/signup", {
        "username": username, "password": password, "password_confirmation": confirmation,
    })
    if status == 201:
        print(f"  Account created. Logged in as {data['username']}.")
    else:
        show_errors(status, data)


def login():
    username = ask("Username: ")
    password = getpass("Password: ")
    status, data = call("POST", "/login", {"username": username, "password": password})
    if status == 200:
        print(f"  Logged in as {data['username']}.")
    else:
        show_errors(status, data)


def logout():
    call("DELETE", "/logout")
    print("  Logged out.")


# shifts 
def print_shift(shift):
    state = "OPEN" if shift["clock_out"] is None else "done"
    print(f"  #{shift['id']:<4} in {fmt_time(shift['clock_in'])}   out {fmt_time(shift['clock_out'])}   [{state}]")


def clock_in():
    status, data = call("POST", "/shifts/clock-in")
    if status == 201:
        print(f"  Clocked in at {fmt_time(data['clock_in'])} (shift #{data['id']}).")
    else:
        show_errors(status, data)


def find_open_shift():
    status, data = call("GET", f"/shifts?page=1&per_page=100")
    if status != 200:
        show_errors(status, data)
        return None
    for shift in data["shifts"]:
        if shift["clock_out"] is None:
            return shift
    return None


def clock_out():
    shift = find_open_shift()
    if shift is None:
        print("  You are not clocked in.")
        return
    status, data = call("PATCH", f"/shifts/{shift['id']}/clock-out")
    if status == 200:
        print(f"  Clocked out at {fmt_time(data['clock_out'])} (shift #{data['id']}).")
    else:
        show_errors(status, data)


def list_shifts():
    page = 1
    while True:
        status, data = call("GET", f"/shifts?page={page}&per_page={PER_PAGE}")
        if status != 200:
            show_errors(status, data)
            return
        pages = max(1, -(-data["total"] // data["per_page"]))
        print(f"\n  Shifts, page {data['page']} of {pages} ({data['total']} total)")
        if not data["shifts"]:
            print("  No shifts on this page.")
        for shift in data["shifts"]:
            print_shift(shift)
        choice = ask("  [n]ext, [p]revious, [b]ack: ").lower()
        if choice == "n" and page < pages:
            page += 1
        elif choice == "p" and page > 1:
            page -= 1
        elif choice == "b":
            return


def delete_shift():
    shift_id = ask_id("Shift id to delete: ")
    if shift_id is None:
        return
    status, data = call("DELETE", f"/shifts/{shift_id}")
    if status in (200, 204):
        print("  Shift deleted.")
    else:
        show_errors(status, data)


#  notes

def list_notes():
    page = 1
    while True:
        status, data = call("GET", f"/notes?page={page}&per_page={PER_PAGE}")
        if status != 200:
            show_errors(status, data)
            return
        pages = max(1, -(-data["total"] // data["per_page"]))
        print(f"\n  Notes, page {data['page']} of {pages} ({data['total']} total)")
        if not data["notes"]:
            print("  No notes on this page.")
        for note in data["notes"]:
            print(f"  #{note['id']:<4} {note['title']}")
        choice = ask("  [n]ext, [p]revious, [b]ack: ").lower()
        if choice == "n" and page < pages:
            page += 1
        elif choice == "p" and page > 1:
            page -= 1
        elif choice == "b":
            return


def create_note():
    title = ask("Title: ")
    content = ask("Content: ")
    status, data = call("POST", "/notes", {"title": title, "content": content})
    if status == 201:
        print(f"  Note #{data['id']} created.")
    else:
        show_errors(status, data)


def view_note():
    note_id = ask_id("Note id: ")
    if note_id is None:
        return
    status, data = call("GET", f"/notes/{note_id}")
    if status == 200:
        print(f"  #{data['id']} {data['title']}\n  {data['content']}")
    else:
        show_errors(status, data)


def update_note():
    note_id = ask_id("Note id: ")
    if note_id is None:
        return
    changes = {}
    title = ask("New title (blank to keep): ")
    content = ask("New content (blank to keep): ")
    if title:
        changes["title"] = title
    if content:
        changes["content"] = content
    if not changes:
        print("  Nothing to change.")
        return
    status, data = call("PATCH", f"/notes/{note_id}", changes)
    if status == 200:
        print("  Note updated.")
    else:
        show_errors(status, data)


def delete_note():
    note_id = ask_id("Note id to delete: ")
    if note_id is None:
        return
    status, data = call("DELETE", f"/notes/{note_id}")
    if status in (200, 204):
        print("  Note deleted.")
    else:
        show_errors(status, data)


# menus

LOGGED_OUT_MENU = [("Log in", login), ("Sign up", signup)]
LOGGED_IN_MENU = [
    ("Clock in", clock_in),
    ("Clock out", clock_out),
    ("List my shifts", list_shifts),
    ("Delete a shift", delete_shift),
    ("List my notes", list_notes),
    ("Create a note", create_note),
    ("View a note", view_note),
    ("Update a note", update_note),
    ("Delete a note", delete_note),
    ("Log out", logout),
]


def main():
    print("Productivity API: shift tracker CLI")
    while True:
        try:
            user = current_user()
            menu = LOGGED_IN_MENU if user else LOGGED_OUT_MENU
            print(f"\n{'Logged in as ' + user['username'] if user else 'Not logged in'}")
            for number, (label, _) in enumerate(menu, start=1):
                print(f"  {number}. {label}")
            print("  0. Quit")
            choice = ask("Choose: ")
            if choice == "0":
                return
            if choice.isdigit() and 1 <= int(choice) <= len(menu):
                menu[int(choice) - 1][1]()
            else:
                print("  Not a valid choice.")
        except ApiError as error:
            print(f"  {error}")
        except (KeyboardInterrupt, EOFError):
            print()
            return


if __name__ == "__main__":
    sys.exit(main())