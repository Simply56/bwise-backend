from flask import Flask, request, jsonify

app = Flask(__name__)

# Temporary in-memory storage (Replace with a database later)
expenses = []

# GET: Fetch all expenses
@app.route('/expenses', methods=['GET'])
def get_expenses():
    return jsonify(expenses)

# POST: Add a new expense
@app.route('/expenses', methods=['POST'])
def add_expense():
    data = request.json  # Get JSON data from request
    if "amount" not in data or "payer" not in data or "group" not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    expense = {
        "id": len(expenses) + 1,
        "amount": data["amount"],
        "payer": data["payer"],
        "group": data["group"]
    }
    expenses.append(expense)
    return jsonify(expense), 201  # 201 = Created

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

