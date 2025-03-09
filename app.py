from flask import Flask, request, jsonify

# TODO RECALCUALTE EXPENSES WHEN USER LEAVES A GROUP?
username = str

app = Flask(__name__)


# Temporary in-memory storage (Replace with a database later)
# {
#     "group": str
#     "username": str # user who paid (could have been entered by someone else)
#     "amount": float
#     "note": str
# }
expenses = []  # always plit equaly
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
        return jsonify({"error": "Missing required fields"}), 400

    if find_user(data) is None:
        users.append(data["username"])
    return jsonify({"success": "login successful"}), 200


# creator does not have to be a member but he was at some point
@app.route("/groups/create", methods=["POST"])
def create_group():
    data = request.json
    if "group" not in data or "username" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    if find_group(data) is not None:
        return jsonify_error("Group already exists"), 409
    if find_user(data) is None:
        return jsonify_error("User not found"), 404

    new_group = {
        "group": data["group"],
        "username": data["username"],  # this is the creator
        "members": [data["username"]],  # adding member twice does nothing
    }

    groups.append(new_group)
    return jsonify(new_group), 201


@app.route("/groups/join", methods=["POST"])
def join_group():
    data = request.json
    if "group" not in data or "username" not in data:
        return jsonify({"error": "Missing required fields"}), 400

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
        return jsonify({"error": "Missing required fields"}), 400

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
        return jsonify({"error": "Missing required fields"}), 400

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
    if (
        "amount" not in data
        or "payer" not in data
        or "group" not in data
        or "note" not in data
        or "username" not in data  # user who submitted the expanse
    ):
        return jsonify({"error": "Missing required fields"}), 400

    g = find_group(data)
    if g is None:
        return jsonify_error("Group not found"), 404

    if data["username"] not in users:
        return jsonify_error("User not found"), 404
    if data["payer"] not in users:
        return jsonify_error("Payer not found"), 404

    if data["username"] not in g["members"]:
        return jsonify_error(f"User is not a member of {data["group"]}"), 400
    if data["payer"] not in g["members"]:
        return jsonify_error(f"Payer is not a member of {data["group"]}"), 400

    expense = {
        "id": len(expenses) + 1,
        "amount": float(data["amount"]),
        "payer": data["payer"],  # user who paid, not the user who entered it
        "username": data["username"], # use who submitted the expense
        "group": data["group"],
        "note": data["note"],
    }
    expenses.append(expense)
    return jsonify(expense), 201  # 201 = Created


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
