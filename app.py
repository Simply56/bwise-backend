import flask
from flask import Flask, request
from flask.wrappers import Response
from waitress import serve
import json
import os
from queue import Queue
from threading import Thread
import signal  # for gracefull shutdowns
from dataclasses import dataclass


app = Flask(__name__)
DEBUG: bool = True

# TODO: REJECT REQUESTS IF MEMORY IS ALMOST FULL


# Limit request size to 500MB (adjust as needed)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024


# wrapper so that we have a lot of log with little code
def jsonify(*args, **kwargs) -> Response:
    if DEBUG:
        print()
        print(args)
    return flask.jsonify(*args, **kwargs)


# Data models
@dataclass
class User:  # TODO: USER IS ONLY USED WHEN IT'S STORED
    username: str

    def to_dict(self):
        return {"username": self.username}


@dataclass
class Transaction:
    from_user: str  # User who owes money
    to_user: str  # User who is owed money
    amount: float

    def to_dict(self):
        return {
            "from_user": self.from_user,
            "to_user": self.to_user,
            "amount": self.amount,
        }


class Group:
    def __init__(self, name, creator):
        self.name = str(name)
        self.creator = str(creator)
        self.members = [str(creator)]
        self.transactions: list[Transaction] = []

    def to_dict(self):
        return {
            "name": self.name,
            "creator": self.creator,
            "members": self.members,
            "transactions": [t.to_dict() for t in self.transactions],
        }

    def to_dict_response(self):
        """same as to dict but doesnt send the transactions to save bandwidth"""
        return {
            "name": self.name,
            "creator": self.creator,
            "members": self.members,
        }


write_queue: Queue[tuple[str, str]] = Queue()
# In-memory storage
USERS: dict[str, User] = {}
GROUPS: dict[str, Group] = {}

# File paths
USERS_FILE = "users.json"
GROUPS_FILE = "groups.json"


# Helper functions for data persistence
def load_data():
    global USERS, GROUPS

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users_data = json.load(f)
            USERS = {username: User(username) for username in users_data}

    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r") as f:
            groups_data = json.load(f)
            # groups = {}
            for group_dict in groups_data:
                group = Group(group_dict["name"], group_dict["creator"])
                group.members = group_dict["members"]

                # Reconstruct transactions
                for t_dict in group_dict.get("transactions", []):
                    transaction = Transaction(
                        t_dict["from_user"],
                        t_dict["to_user"],
                        t_dict["amount"],
                    )
                    group.transactions.append(transaction)

                GROUPS[group.name] = group


def save_data() -> None:
    users_json: str = json.dumps(
        [user for user in USERS.keys()]
    )  # this is still called before we return
    write_queue.put((USERS_FILE, users_json))

    groups_json: str = json.dumps([group.to_dict() for group in GROUPS.values()])
    write_queue.put((GROUPS_FILE, groups_json))

    # with open(USERS_FILE, "w") as f:
    #     f.write(users_json)

    # with open(GROUPS_FILE, "w") as f:
    #     f.write(groups_json)


def writer_thread() -> None:
    while True:  # not a busy wait
        item: tuple[str, str] = write_queue.get()  # this blocks and sleeps the thread
        if item is None:
            break

        filename, json_data = item
        with open(filename, "w") as f:
            f.write(json_data)

        write_queue.task_done()


# TODO: ADD PASSWORD AUTHENTIFICATION
@app.route("/login", methods=["POST"])
def login():
    data: dict = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username is required to Login"}), 400

    # If user exists, return success
    if username in USERS:
        return jsonify({"message": "Login successful", "username": username}), 200

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


@app.route("/create_group", methods=["POST"])
def create_group():
    data: dict = request.get_json()
    username = data.get("username")
    group_name = data.get("group_name")

    if not username or not group_name:
        return jsonify({"message": "Username and group_name are required"}), 400

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
def join_group():
    data: dict = request.get_json()
    username = data.get("username")
    group_name = data.get("group_name")

    if not username or not group_name:
        return jsonify({"message": "Username and group_name are required"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username in group.members:
        return (
            jsonify(
                {"message": f"User {username} is already a member of {group.name}"}
            ),
            409,
        )

    group.members.append(username)
    save_data()

    return (
        jsonify(
            {
                "message": f"User {username} joined successfully",
                "group": group.to_dict_response(),
            }
        ),
        200,
    )


@app.route("/delete_group", methods=["POST"])
def delete_group():
    data: dict = request.get_json()
    username: str = data.get("username")
    group_name = data.get("group_name")

    if not username or not group_name:
        return jsonify({"message": "Username and group_name are required"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    if not username.startswith("admin"):
        group = GROUPS[group_name]
        if group.creator != username:
            return (
                jsonify(
                    {
                        "message": f"Only the group creator {group.creator} can delete groups"
                    }
                ),
                403,
            )

    GROUPS.pop(group_name)
    save_data()

    return (jsonify({"message": f"Group {group_name} deleted succesfuly"}), 200)


def settle_up_internal(username1: str, group: Group, username2: str):
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
def settle_up():
    data: dict = request.get_json()
    username = data.get("username")  # User who is settling up
    to_user = data.get("to_user")  # User who is being paid
    group_name = data.get("group_name")

    if not username or not to_user or not group_name:
        return (
            jsonify({"message": "Username, to_user, and group_name are required"}),
            400,
        )

    if username not in USERS or to_user not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members or to_user not in group.members:
        return (
            jsonify({"message": f"User {username} is not a member of {group.name}"}),
            403,
        )

    original_transaction_count = len(group.transactions)
    settle_up_internal(username, group, to_user)
    save_data()
    settled_transaction_count = original_transaction_count - len(group.transactions)
    return (
        jsonify(
            {
                "message": "Settled up successfully",
                "transactions_settled": settled_transaction_count,
                "group": group.to_dict_response(),
            }
        ),
        200,
    )


@app.route("/kick_user", methods=["POST"])
def kick_user():
    data: dict = request.get_json()
    username: str = data.get("username")  # User requesting the kick
    target_username = data.get("target_username")  # User to be kicked
    group_name = data.get("group_name")

    if not username or not target_username or not group_name:
        return (
            jsonify(
                {"message": "Username, target_username, and group_name are required"}
            ),
            400,
        )

    if username not in USERS or target_username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if target_username not in group.members:
        return jsonify({"message": f"{username} is not a member of this group"}), 404

    if not username.startswith("admin"):
        if username != group.creator and username != target_username:
            return (
                jsonify(
                    {
                        "message": f"Only the group creator {group.creator} can kick other users"
                    }
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
                "group": group.to_dict_response(),
            }
        ),
        200,
    )


# changed to post because retrofit does not accept GET request with json bodies
@app.route("/get_user_groups", methods=["POST"])
def get_user_groups():
    data: dict = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username is required"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    user_groups = [
        group.to_dict_response()
        for group in GROUPS.values()
        if username in group.members
    ]

    return jsonify({"message": "Groups retrieved", "groups": user_groups}), 200


@app.route("/add_expense", methods=["POST"])
def add_expense():
    data: dict = request.get_json()
    username = data.get("username")  # User who paid
    group_name = data.get("group_name")
    amount = data.get("amount")

    if not username or not group_name or amount is None:
        return (
            jsonify({"message": "Username, group_name, and amount are required"}),
            400,
        )

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"message": "Amount must be positive"}), 400
    except ValueError:
        return jsonify({"message": "Amount must be a number"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members:
        return (
            jsonify({"message": f"User {username} is not a member of {group.name}"}),
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
                "group": group.to_dict_response(),
            }
        ),
        201,
    )


@app.route("/get_debts", methods=["POST"])
def get_debts():
    data: dict = request.get_json()
    username = data.get("username")
    group_name = data.get("group_name")

    if not username or not group_name:
        return jsonify({"message": "Username and group_name are required"}), 400

    if username not in USERS:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in GROUPS:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = GROUPS[group_name]

    if username not in group.members:
        return (
            jsonify({"message": f"User {username} is not a member of {group.name}"}),
            403,
        )

    # Calculate debts per user
    debts: dict[str, float] = {}

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

    # Format the result
    result = []
    for user in group.members:
        amount = debts.get(user, 0.0)
        if amount > 0:
            result.append({"username": user, "amount": amount, "status": "you owe"})
        elif amount < 0:
            result.append(
                {"username": user, "amount": abs(amount), "status": "owes you"}
            )
        else:
            result.append({"username": user, "amount": amount, "status": "settled up"})

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
    signal.signal(signal.SIGKILL, shutdown_handler)

    load_data()

    thread = Thread(target=writer_thread)
    thread.start()

    if DEBUG:
        app.run(host="0.0.0.0", port=5000)
    else:
        serve(app, host="0.0.0.0", port=5000)
