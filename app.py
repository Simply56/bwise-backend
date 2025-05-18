import json
import os
import queue
import signal  # for gracefull shutdowns
import threading
from dataclasses import dataclass

import flask
import waitress
from flask.wrappers import Response

app = flask.Flask(__name__)
DEBUG: bool = True


def jsonify(*args, **kwargs) -> Response:
    """
    Wrapper of the flask.jsonify() function
    that prints the passed args. Used for debugging only
    """
    if DEBUG:
        print()
        print(args)
    return flask.jsonify(*args, **kwargs)


# Data models
@dataclass
class User:
    username: str

    def to_dict(self) -> dict[str, str]:
        return {"username": self.username}


@dataclass
class Transaction:
    from_user: str  # User who owes money
    to_user: str  # User who is owed money
    amount: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "from_user": self.from_user,
            "to_user": self.to_user,
            "amount": self.amount,
        }


class Group:
    def __init__(self, name, creator):
        self.name = str(name)
        self.creator = str(creator)
        self.members: list[str] = [str(creator)]
        self.transactions: list[Transaction] = []

    def to_dict(self):
        result = self.to_dict_no_transactions()
        result["transactions"] = [t.to_dict() for t in self.transactions]
        return result

    def to_dict_no_transactions(self):
        # same as to dict but doesnt send the transactions to save bandwidth
        return {
            "name": self.name,
            "creator": self.creator,
            "members": self.members,
        }


write_queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
# In-memory storage
USERS: dict[str, User] = dict()
GROUPS: dict[str, Group] = dict()

# File paths
USERS_FILE = "users.json"
GROUPS_FILE = "groups.json"


def load_data(
    load_users_dict: dict[str, User], load_groups_dict: dict[str, Group]
) -> None:
    """
    Loads the list of Groups and Users from json file
    when the server starts
    """
    load_users(load_users_dict)
    load_groups(load_groups_dict)


def load_users(load_users_dict: dict[str, User]) -> None:
    if not os.path.exists(USERS_FILE):
        return

    with open(USERS_FILE, "r") as f:
        try:
            users_data = json.load(f)
        except Exception:
            return

        load_users_dict.update(
            {username: User(username) for username in users_data}
        )


def load_groups(load_groups_dict: dict[str, Group]) -> None:
    if not os.path.exists(GROUPS_FILE):
        return

    with open(GROUPS_FILE, "r") as f:
        try:
            groups_data = json.load(f)
        except Exception:
            return

        for group_dict in groups_data:
            group = Group(group_dict["name"], group_dict["creator"])
            group.members = group_dict["members"]

            # Reconstruct transactions
            for t_dict in group_dict.get("transactions", dict()):
                transaction = Transaction(
                    t_dict["from_user"],
                    t_dict["to_user"],
                    t_dict["amount"],
                )
                group.transactions.append(transaction)

            load_groups_dict[group.name] = group


def save_data() -> None:
    """
    Saves the current in-memory representation of GROUPS and USERS
    into a json file.
    For a faster response time, the strings to write
    are first put into a queue and the  writing is done after responding
    """
    users_json: str = json.dumps([username for username in USERS.keys()])

    groups_json: str = json.dumps(
        [group.to_dict() for group in GROUPS.values()]
    )

    # with open(USERS_FILE, "w")as f:
    #     f.write(users_json)
    # with open(GROUPS_FILE, "w") as f:
    #     f.write(groups_json)

    write_queue.put((USERS_FILE, users_json))
    write_queue.put((GROUPS_FILE, groups_json))


def writer_thread() -> None:
    while True:  # not a busy wait
        # this blocks and sleeps the thread
        item: tuple[str, str] | None = write_queue.get()
        if item is None:
            break

        filename, json_data = item
        with open(filename, "w") as f:
            f.write(json_data)

        write_queue.task_done()


@app.route("/login", methods=["POST"])
def login() -> tuple[Response, int]:
    data: dict = flask.request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username is required to Login"}), 400

    # If user exists, return success
    if username in USERS:
        return (
            jsonify({"message": "Login successful", "username": username}),
            200,
        )

    # If user doesn't exist, create a new one
    USERS[username] = User(username)
    save_data()
    return (
        jsonify(
            {
                "message": f"User {username} registered successfully",
                "username": username,
            }
        ),
        201,
    )


def validate_request(request: flask.Request, *keys: str):
    """
    A helper function that extracts values for each key
    from a flask request.
    It returns the values in the same order as the keys.
    It is designed to be used with tuple unpacking.

    Raises KeyError if a key is not found in the request.
    The propper response is included in the exeption
    including a json payload and a http error code
    """
    data: dict = flask.request.get_json()
    missing_keys = [key for key in keys if data.get(key) is None]

    if missing_keys:
        # Return the first missing key in the error
        raise KeyError(
            (jsonify({"message": f"{missing_keys[0]} is required"}), 400)
        )

    values = [str(data.get(key)) for key in keys]
    return values[0] if len(values) == 1 else tuple(values)


@app.route("/create_group", methods=["POST"])
def create_group() -> tuple[Response, int]:
    try:
        username, group_name = validate_request(
            flask.request, "username", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name in GROUPS:
        return jsonify({"message": f"Group {group_name} already exists"}), 409

    group = Group(group_name, username)
    GROUPS[group_name] = group
    save_data()

    return (
        jsonify(
            {
                "message": f"Group {group_name} created successfully",
                "group": group.to_dict(),
            }
        ),
        201,
    )


@app.route("/join_group", methods=["POST"])
def join_group() -> tuple[Response, int]:
    try:
        username, group_name = validate_request(
            flask.request, "username", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username in group.members:
        return (
            jsonify(
                {"message": f"{username} is already member of {group.name}"}
            ),
            200,
        )

    group.members.append(username)
    save_data()

    return (
        jsonify(
            {
                "message": f"User {username} joined successfully",
                "group": group.to_dict_no_transactions(),
            }
        ),
        200,
    )


@app.route("/delete_group", methods=["POST"])
def delete_group() -> tuple[Response, int]:
    try:
        username, group_name = validate_request(
            flask.request, "username", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    if not username.startswith("admin"):
        group = GROUPS[group_name]
        if group.creator != username:
            return (
                jsonify(
                    {"message": f"Only {group.creator} can delete groups"}
                ),
                403,
            )

    GROUPS.pop(group_name)
    save_data()

    return (
        jsonify({"message": f"Group {group_name} deleted succesfuly"}),
        200,
    )


def settle_up_internal(username1: str, group: Group, username2: str) -> None:
    # Remove all transactions between the two members
    updated_transactions: list[Transaction] = []

    for trn in group.transactions:
        if trn.from_user == username1 and trn.to_user == username2:
            continue
        if trn.from_user == username2 and trn.to_user == username1:
            continue

        updated_transactions.append(trn)

    group.transactions = updated_transactions


@app.route("/settle_up", methods=["POST"])
def settle_up() -> tuple[Response, int]:
    try:
        username, to_user, group_name = validate_request(
            flask.request, "username", "to_user", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS or to_user not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members or to_user not in group.members:
        return (
            jsonify(
                {"message": f"User {username} is not a member of {group.name}"}
            ),
            403,
        )

    original_transaction_count = len(group.transactions)
    settle_up_internal(username, group, to_user)
    save_data()
    settled_transaction_count = original_transaction_count - len(
        group.transactions
    )
    return (
        jsonify(
            {
                "message": "Settled up successfully",
                "transactions_settled": settled_transaction_count,
                "group": group.to_dict_no_transactions(),
            }
        ),
        200,
    )


@app.route("/kick_user", methods=["POST"])
def kick_user() -> tuple[Response, int]:
    try:
        username, target_username, group_name = validate_request(
            flask.request, "username", "target_username", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS or target_username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if target_username not in group.members:
        return (
            jsonify({"message": f"{username} is not a member of this group"}),
            404,
        )

    if not username.startswith("admin"):
        if username != group.creator and username != target_username:
            return (
                jsonify(
                    {"message": f"Only {group.creator} can kick other users"}
                ),
                403,
            )

    # kicked user settles all of his debts
    for member_name in group.members:
        settle_up_internal(username, group, member_name)

    group.members.remove(target_username)

    save_data()
    return (
        jsonify(
            {
                "message": f"User {username} kicked successfully",
                "group": group.to_dict_no_transactions(),
            }
        ),
        200,
    )


# changed to post because retrofit can't create GET request with json bodies
@app.route("/get_user_groups", methods=["POST"])
def get_user_groups() -> tuple[Response, int]:
    try:
        username = validate_request(flask.request, "username")
    except KeyError as e:
        return e.args[0]

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    user_groups = [
        group.to_dict_no_transactions()
        for group in GROUPS.values()
        if username in group.members
    ]

    return jsonify({"message": "Groups retrieved", "groups": user_groups}), 200


@app.route("/add_expense", methods=["POST"])
def add_expense() -> tuple[Response, int]:
    try:
        username, group_name, amount = validate_request(
            flask.request, "username", "group_name", "amount"
        )
    except KeyError as e:
        return e.args[0]

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"message": "Amount must be a number"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members:
        return (
            jsonify(
                {"message": f"User {username} is not a member of {group.name}"}
            ),
            403,
        )

    # Calculate equal share for each member
    num_members = len(group.members)
    share_per_member = amount / num_members

    # Create transactions for each member (except the payer)
    for member in group.members:
        if member != username:
            transaction = Transaction(member, username, share_per_member)
            group.transactions.append(transaction)

    save_data()

    return (
        jsonify(
            {
                "message": "Expense added successfully",
                "amount": amount,
                "share_per_member": share_per_member,
                "group": group.to_dict_no_transactions(),
            }
        ),
        201,
    )


@app.route("/get_debts", methods=["POST"])
def get_debts() -> tuple[Response, int]:
    try:
        username, group_name = validate_request(
            flask.request, "username", "group_name"
        )
    except KeyError as e:
        return e.args[0]

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members:
        return (
            jsonify(
                {"message": f"User {username} is not a member of {group.name}"}
            ),
            403,
        )

    debts = calculate_relative_debt(group, username)
    # Format the result
    result: list[dict[str, str | float]] = []
    for user in group.members:
        amount = debts.get(user, 0.0)
        if amount > 0:
            result.append(
                {"username": user, "amount": amount, "status": "you owe"}
            )
        elif amount < 0:
            result.append(
                {"username": user, "amount": abs(amount), "status": "owes you"}
            )
        else:
            result.append(
                {"username": user, "amount": amount, "status": "settled up"}
            )

    return (
        jsonify(
            {
                "message": "Got debts",
                "username": username,
                "group_name": group_name,
                "debts": result,
            }
        ),
        200,
    )


def calculate_relative_debt(group: Group, username: str) -> dict[str, float]:
    debts: dict[str, float] = dict()

    for transaction in group.transactions:
        if transaction.from_user == username:
            # User owes money to someone
            if transaction.to_user not in debts:
                debts[transaction.to_user] = 0
            debts[transaction.to_user] += transaction.amount
        elif transaction.to_user == username:
            # Someone owes money to the user
            if transaction.from_user not in debts:
                debts[transaction.from_user] = 0
            debts[transaction.from_user] -= transaction.amount

    return debts


def shutdown_handler(signum, frame):
    print(f"Received signal {signum}, shutting down gracefully...")

    # Signal the writer thread to stop
    write_queue.put(None)

    # Wait for all queued writes to finish
    thread.join()

    print("Writer thread finished. Exiting.")
    exit(0)


if __name__ == "__main__":
    # Register handlers for SIGINT (Ctrl+C) and SIGTERM (e.g., pkill)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    load_data(USERS, GROUPS)

    thread = threading.Thread(target=writer_thread)
    thread.start()

    if DEBUG:
        app.run(host="0.0.0.0", port=5000)
    else:
        waitress.serve(app, host="0.0.0.0", port=5000)
