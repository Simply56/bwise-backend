from flask import Flask, request, jsonify
from entities import Transaction, User, Group

app = Flask(__name__)

""" 
The app will only display how much does the current user owe to each member
it will not display hisotry or what the money was used for (no notes in the app for now)
 """

# TODO SETTLE UP GROUP BUTTON THAT DELETES TRANSACTION HISTORY


def jsonify_error(msg: str):
    return jsonify({"error": msg})


@app.route("/login", methods=["POST"])
def login_user():
    data = request.json
    try:
        u = User(data=data)
    except KeyError:
        return jsonify_error("Missing required fields"), 400
    except (ValueError, TypeError):
        return jsonify_error("Invalid request"), 400

    if u.good_to_store():
        User.STORAGE.append(u)
        u.store()
    return u.to_json(), 200


# creator does not have to be a member but he was at some point
@app.route("/groups/create", methods=["POST"])
def create_group():
    data = request.json

    try:
        g = Group(data=data)
    except KeyError:
        return jsonify_error("Missing required fields"), 400
    except (ValueError, TypeError):
        return jsonify_error("Invalid request"), 400

    if not g.good_to_store():
        return jsonify_error("Invalid group"), 400

    Group.STORAGE.append(g)
    g.store()

    return g.to_json(), 201


@app.route("/groups/join", methods=["POST"])
def join_group():
    data = request.json
    if "group_name" not in data or "username" not in data:
        return jsonify_error("Missing required fields"), 400

    g = Group.get_group(data["group_name"])
    if g is None:
        return jsonify_error("Group does not exist"), 404
    u = User.get_user(data["username"])
    if u is None:
        return jsonify_error("Cannot join because user does not exist"), 404

    if u not in g.members:
        g.members.append(u.username)
    return g.to_json(), 200


# if creator leaves he is still the creator but not a member, so he can rejoin and keep the role
@app.route("/groups/kick", methods=["PUT"])
def kick_user():
    data = request.json
    # username is the user we want to kick
    # creator is the user does the kicking
    if "username" not in data or "kicker" not in data or "group_name" not in data:
        return jsonify_error("Missing required fields"), 400

    g = Group.get_group(data["group_name"])
    if g is None:
        return jsonify_error("Group not found"), 404

    u = User.get_user(data["username"])
    if u is None:
        return jsonify_error("User not found"), 404
    k = User.get_user(data["kicker"])
    if k is None:
        return jsonify_error("Kicker not found"), 404

    # Creator can kick anybody
    # Member can kick himself
    if k.username != g.creator and k.username != u.username:
        return jsonify_error("Insuficient privladge"), 401

    if k.username not in g.members or u.username not in g.members:
        return jsonify_error("Not a member"), 404

    g.members.pop(g.members.index(u.username))
    return g.to_json(), 200


@app.route("/users/groups", methods=["GET"])
def get_user_groups():
    data = request.json
    if "username" not in data:
        return jsonify_error("Missing required fields"), 400

    u = User.get_user(data["username"])
    if u is None:
        return jsonify_error("User not found"), 404

    response = []
    for g in Group.STORAGE:
        if u.username in g.members:
            response.append(g.to_json)
    return response, 200  # TODO: JSONIFY RESPONSE?


# POST: Add a new expense
@app.route("/expenses", methods=["POST"])
def add_expense():
    data = request.json  # Get JSON data from request
    try:
        transaction = Transaction(data)
    except KeyError:
        return jsonify_error("Missing required fields"), 400
    except (ValueError, TypeError):
        return jsonify_error("Invalid request"), 400

    g = Group.get_group(transaction.group_name)
    if g is None:
        return jsonify_error("Group not found"), 404

    if transaction.submitter not in g.members:
        return jsonify_error(f"User is not a member of {data['group']}"), 400
    if transaction.payer not in g.members:
        return jsonify_error(f"Payer is not a member of {data['group']}"), 400

    transaction.store()
    Transaction.STORAGE.append(transaction)
    return transaction.to_json(), 201  # 201 = Created


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
    User.load()
    Group.load()
    Transaction.load()
