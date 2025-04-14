import flask
from flask import Flask, request
from waitress import serve
import json
import os
from queue import Queue
from threading import Thread
import signal
import sys


app = Flask(__name__)
DEBUG: bool = True

# TODO: REJECT REQUESTS IF MEMORY IS ALMOST FULL
# TODO: CONSIDER CHANGING JOIN GROUP TO ADD MEMBER


# Limit request size to 1MB (adjust as needed)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024


# wrapper so that we have a lot of log with little code
def jsonify(*args, **kwargs):
    if DEBUG:
        print(args)
        print(kwargs)
        print()
    return flask.jsonify(*args, **kwargs)


# Data models
class User:  # TODO: USER IS ONLY USED WHEN IT'S STORED
    def __init__(self, username: str):
        self.username = str(username)

    def to_dict(self):
        return {"username": self.username}


class Transaction:
    def __init__(self, from_user: str, to_user: str, amount: float):
        self.from_user = str(from_user)  # User who owes money
        self.to_user = str(to_user)  # User who is owed money
        self.amount = float(amount)

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


write_queue: Queue[tuple[str, str]] = Queue()
# In-memory storage
users: dict[str, User] = {}
groups: dict[str, Group] = {}

# File paths
USERS_FILE = "users.json"
GROUPS_FILE = "groups.json"


# Helper functions for data persistence
def load_data():
    global users, groups

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users_data = json.load(f)
            users = {username: User(username) for username in users_data}

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

                groups[group.name] = group


def save_data():
    users_json: str = json.dumps([user for user in users.keys()])

    groups_json: str = json.dumps([group.to_dict() for group in groups.values()])
    write_queue.put((USERS_FILE, users_json))
    write_queue.put((GROUPS_FILE, groups_json))


def writer_thread():
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
    if username in users:
        return jsonify({"message": "Login successful", "username": username}), 200

    # If user doesn't exist, create a new one
    users[username] = User(username)
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

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name in groups:
        return jsonify({"message": f"Group {group_name} already exists"}), 409

    group = Group(group_name, username)
    groups[group_name] = group
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

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = groups[group_name]

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
                "group": group.to_dict(),
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

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    if not username.startswith("admin"):
        group = groups[group_name]
        if group.creator != username:
            return (
                jsonify(
                    {
                        "message": f"Only the group creator {group.creator} can delete groups"
                    }
                ),
                403,
            )

    groups.pop(group_name)
    save_data()

    return (jsonify({"message": f"Group {group_name} deleted succesfuly"}), 200)


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

    if username not in users or target_username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = groups[group_name]

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

    group.members.remove(target_username)

    # Remove transactions involving the kicked user
    group.transactions = [
        t
        for t in group.transactions
        if t.from_user != target_username and t.to_user != target_username
    ]

    # save_data()

    return (
        jsonify({"message": f"User {username} kicked successfully", "group": group.to_dict()}),
        200,
    )


# changed to post because retrofit does not accept GET request with json bodies
@app.route("/get_user_groups", methods=["POST"])
def get_user_groups():
    data: dict = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username is required"}), 400

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    user_groups = [
        group.to_dict() for group in groups.values() if username in group.members
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

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = groups[group_name]

    if username not in group.members:
        return jsonify({"message": f"User {username} is not a member of {group.name}"}), 403

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
                "group": group.to_dict(),
            }
        ),
        201,
    )


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

    if username not in users or to_user not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = groups[group_name]

    if username not in group.members or to_user not in group.members:
        return jsonify({"message": f"User {username} is not a member of {group.name}"}), 403

    # Remove all transactions between the two members
    original_transaction_count = len(group.transactions)
    group.transactions = [
        t
        for t in group.transactions
        if (
            t.from_user != username
            and t.from_user != to_user
            and t.to_user != to_user
            and t.from_user != to_user
        )
    ]

    settled_transaction_count = original_transaction_count - len(group.transactions)

    save_data()

    return (
        jsonify(
            {
                "message": "Settled up successfully",
                "transactions_settled": settled_transaction_count,
                "group": group.to_dict(),
            }
        ),
        200,
    )


@app.route("/get_debts", methods=["POST"])
def get_debts():
    data: dict = request.get_json()
    username = data.get("username")
    group_name = data.get("group_name")

    if not username or not group_name:
        return jsonify({"message": "Username and group_name are required"}), 400

    if username not in users:
        return jsonify({"message": f"User {username} does not exist"}), 404

    if group_name not in groups:
        return jsonify({"message": f"Group {group_name} does not exist"}), 404

    group = groups[group_name]

    if username not in group.members:
        return jsonify({"message": f"User {username} is not a member of {group.name}"}), 403

    # Calculate debts per user
    debts = {}
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
    for user, amount in debts.items():
        if amount > 0:
            result.append({"username": user, "amount": amount, "status": "you owe"})
        elif amount < 0:
            result.append(
                {"username": user, "amount": abs(amount), "status": "owes you"}
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


def shutdown_handler(signum, frame):
    print(f"Received signal {signum}, shutting down gracefully...")

    # Signal the writer thread to stop
    write_queue.put(None)

    # Wait for all queued writes to finish
    thread.join()

    print("Writer thread finished. Exiting.")
    sys.exit(0)


if __name__ == "__main__":

    thread = Thread(target=writer_thread)
    thread.start()

    if DEBUG:
        app.run(host="0.0.0.0", port=5000)
    else:
        serve(app, host="0.0.0.0", port=5000)

    # Register handlers for SIGINT (Ctrl+C) and SIGTERM (e.g., pkill)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
