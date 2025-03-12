from flask import Flask, request, jsonify
import json

""" 
The app will only display how much does the current user owe to each member
it will not display hisotry or what the money was used for (no notes in the app for now)

 """

# TODO SETTLE UP GROUP BUTTON THAT DELETES TRANSACTION HISTORY
# TODO MOVO A TRANSACTION MODEL, WHEN A USER PAYS FOR A THING AND OTHER MEMBERS OWE HIM MONEY
#      IT SHOW UP AS IF HE PAID FRACTION OF THE TOTAL COST OT EACH OF THEM
username = str

app = Flask(__name__)


class Jsonable:
    def to_json(self):
        return jsonify(self.__dict__)

    def store(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data: list = json.load(file)  # Load the list from the JSON file
        except (FileNotFoundError, json.JSONDecodeError):
            data = []  # If file is empty or doesn't exist, start with an empty list

        data.append(self.__dict__)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)


class Expense(Jsonable):
    # some how jsonify just works with this
    id: int
    group: str
    payer: str
    submitter: str
    amount: float

    def __init__(self, data):
        self.id = len(expenses)
        self.group = str(data["group"])
        self.payer = str(data["payer"])
        self.amount = float(data["amount"])
        self.submitter = str(data["submitter"])

    def store(self):
        return super().store("expenses.json")


# Temporary in-memory storage (Replace with a database later)
# {
#     "group": str
#     "username": str # user who paid (could have been entered by someone else)
#     "amount": float
# }
expenses: list[Expense] = []  # always plit equaly
users: list[username] = []
group = dict
groups: list[group] = []


# assumes valid data
def find_user(data) -> username | None:
    for u in users:
        if u == data["username"]:
            return u
    return None


# assumes valid data
def find_group(data) -> group | None:
    for g in groups:
        if g["group"] == data["group"]:
            return g
    return None


def jsonify_error(msg: str):
    return jsonify({"error": msg})


@app.route("/login", methods=["POST"])
def login_user():
    data = request.json
    if "username" not in data:
        return jsonify_error("Missing required fields"), 400

    if find_user(data) is None:
        users.append(data["username"])
    return jsonify({"success": "login successful"}), 200


# creator does not have to be a member but he was at some point
@app.route("/groups/create", methods=["POST"])
def create_group():
    data = request.json
    if "group" not in data or "creator" not in data:
        return jsonify_error("Missing required fields"), 400

    if find_group(data) is not None:
        return jsonify_error("Group already exists"), 409
    if data["creator"] not in users:
        return jsonify_error("User not found"), 404

    new_group = {
        "group": data["group"],
        "creator": data["creator"],  # this is the creator
        "members": [data["creator"]],  # adding member twice does nothing
    }

    groups.append(new_group)
    return jsonify(new_group), 201


@app.route("/groups/join", methods=["POST"])
def join_group():
    data = request.json
    if "group" not in data or "username" not in data:
        return jsonify_error("Missing required fields"), 400

    g = find_group(data)
    if g is None:
        return jsonify_error("Group does not exist"), 404
    if find_user(data) is None:
        return jsonify_error("Cannot join because user does not exist"), 404

    if data["username"] not in g["members"]:
        g["members"].append(data["username"])
    return jsonify(g), 200


# if creator leaves he is still the creator but not a member, so he can rejoin and keep the role
@app.route("/groups/kick", methods=["PUT"])
def kick_user():
    data = request.json
    # username is the user we want to kick
    # creator is the user does the kicking
    if "username" not in data or "kicker" not in data or "group" not in data:
        return jsonify_error("Missing required fields"), 400

    g = find_group(data)
    if g is None:
        return jsonify_error("Group not found"), 404

    u = find_user(data)
    if u is None:
        return jsonify_error("User not found"), 404

    if data["kicker"] not in users:
        return jsonify_error("Kicker not found"), 404

    # Creator can kick anybody
    # Member can kick himself
    if data["kicker"] != g["username"] and data["kicker"] != data["username"]:
        return jsonify_error("Insuficient privladge"), 401

    if data["kicker"] not in g["members"] or data["username"] not in g["members"]:
        return jsonify_error("Not a member"), 404

    g["members"].pop(g["members"].index(data["username"]))
    return jsonify(g), 200


@app.route("/users/groups", methods=["GET"])
def get_user_groups():
    data = request.json
    if "username" not in data:
        return jsonify_error("Missing required fields"), 400

    current_user = find_user(data)
    if current_user is None:
        return jsonify_error("User not found"), 404

    relevant_groups = []
    for g in groups:
        for member in g["members"]:
            if current_user == member:
                relevant_groups.append(g)
    return jsonify(relevant_groups)


# GET: Fetch all expenses
@app.route("/expenses", methods=["GET"])
def get_expenses():
    return jsonify(expenses)


# POST: Add a new expense
@app.route("/expenses", methods=["POST"])
def add_expense():
    data = request.json  # Get JSON data from request
    try:
        expense = Expense(data)
    except KeyError:
        return jsonify_error("Missing required fields"), 400
    except (ValueError, TypeError):
        return jsonify_error("Invalid request"), 400

    g = find_group(data)
    if g is None:
        return jsonify_error("Group not found"), 404

    if expense.submitter not in users:
        return jsonify_error("User not found"), 404
    if expense.payer not in users:
        return jsonify_error("Payer not found"), 404

    if expense.submitter not in g["members"]:
        return jsonify_error(f"User is not a member of {data['group']}"), 400
    if expense.payer not in g["members"]:
        return jsonify_error(f"Payer is not a member of {data['group']}"), 400

    expense.store()
    expenses.append(expense)
    return expense.to_json(), 201  # 201 = Created


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
