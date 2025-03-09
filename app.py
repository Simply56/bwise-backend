from flask import Flask, request, jsonify


username = str
group = dict[str, str]

app = Flask(__name__)
SALT = "yum"

# Temporary in-memory storage (Replace with a database later)
expenses = []
users: list[username] = []
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
        "username": data["username"],
        "members": [data["username"]],  # adding member twice does nothing
    }

    groups.append(new_group)
    return jsonify(new_group), 200


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


# TODO: LEAVE/KICK FROM GROUP


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
    if "amount" not in data or "payer" not in data or "group" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    expense = {
        "id": len(expenses) + 1,
        "amount": float(data["amount"]),
        "payer": data["payer"],
        "group": data["group"],
    }
    expenses.append(expense)
    return jsonify(expense), 201  # 201 = Created


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
