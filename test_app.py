import pytest
from app import app
from flask import Flask, jsonify
import subprocess
import json


@pytest.fixture(autouse=True)
def run_before_each_test():
    # clears previous data
    subprocess.call(["./clr.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def client():
    return app.test_client()


def test_client_not_found(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_login_new_user(client):
    response = client.post(
        "/login", json={"username": "testuser1"}, content_type="application/json"
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "User registered successfully"
    assert data["username"] == "testuser1"


def test_login_existing_user(client):
    # First create a user
    client.post(
        "/login", json={"username": "testuser2"}, content_type="application/json"
    )

    # Then try to login with the same user
    response = client.post(
        "/login", json={"username": "testuser2"}, content_type="application/json"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Login successful"
    assert data["username"] == "testuser2"


def test_login_missing_username(client):
    response = client.post("/login", json={}, content_type="application/json")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Username is required"


def test_create_group(client):
    # First create a user
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )

    # Then create a group
    response = client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup1"},
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "Group created successfully"
    assert data["group"]["name"] == "testgroup1"
    assert data["group"]["creator"] == "groupcreator"
    assert "groupcreator" in data["group"]["members"]


def test_create_group_missing_params(client):
    response = client.post(
        "/create_group",
        json={"username": "groupcreator"},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Username and group_name are required"


def test_create_group_nonexistent_user(client):
    response = client.post(
        "/create_group",
        json={"username": "nonexistentuser", "group_name": "testgroup2"},
        content_type="application/json",
    )
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "User does not exist"


def test_join_group(client):
    # First create a user and a group
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup3"},
        content_type="application/json",
    )

    # Create another user
    client.post("/login", json={"username": "joiner"}, content_type="application/json")

    # Join the group
    response = client.post(
        "/join_group",
        json={"username": "joiner", "group_name": "testgroup3"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "User joined successfully"
    assert "joiner" in data["group"]["members"]


def test_join_group_already_member(client):
    # First create a user and a group
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup4"},
        content_type="application/json",
    )

    # Try to join the group again
    response = client.post(
        "/join_group",
        json={"username": "groupcreator", "group_name": "testgroup4"},
        content_type="application/json",
    )
    assert response.status_code == 409
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "User is already a member of this group"


def test_delete_group(client):
    # First create a user and a group
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup5"},
        content_type="application/json",
    )

    # Delete the group
    response = client.post(
        "/delete_group",
        json={"username": "groupcreator", "group_name": "testgroup5"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Group deleted succesfuly"

    # Verify the group is deleted
    response = client.post(
        "/join_group",
        json={"username": "joiner", "group_name": "testgroup5"},
        content_type="application/json",
    )
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data["error"] == "Group does not exist"


def test_delete_group_not_creator(client):
    # First create a user and a group
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup6"},
        content_type="application/json",
    )

    # Create another user
    client.post("/login", json={"username": "joiner"}, content_type="application/json")

    # Join the group
    client.post(
        "/join_group",
        json={"username": "joiner", "group_name": "testgroup6"},
        content_type="application/json",
    )

    # Try to delete the group as a non-creator
    response = client.post(
        "/delete_group",
        json={"username": "joiner", "group_name": "testgroup6"},
        content_type="application/json",
    )
    assert response.status_code == 403
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Only the group creator can delete groups"


def test_admin_delete_group(client):
    # First create a user and a group
    client.post(
        "/login", json={"username": "groupcreator"}, content_type="application/json"
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup7"},
        content_type="application/json",
    )

    # Create an admin user
    client.post(
        "/login", json={"username": "adminuser"}, content_type="application/json"
    )

    # Admin deletes the group
    response = client.post(
        "/delete_group",
        json={"username": "adminuser", "group_name": "testgroup7"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Group deleted succesfuly"


def test_get_user_groups(client):
    # Create a user
    client.post(
        "/login", json={"username": "testuser3"}, content_type="application/json"
    )

    # Create a group
    client.post(
        "/create_group",
        json={"username": "testuser3", "group_name": "testgroup8"},
        content_type="application/json",
    )

    # Get user groups
    response = client.post(
        "/get_user_groups",
        json={"username": "testuser3"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["groups"]) == 1
    assert data["groups"][0]["name"] == "testgroup8"


def test_add_expense(client):
    # Create users
    client.post("/login", json={"username": "payer"}, content_type="application/json")
    client.post("/login", json={"username": "member1"}, content_type="application/json")
    client.post("/login", json={"username": "member2"}, content_type="application/json")

    # Create a group
    client.post(
        "/create_group",
        json={"username": "payer", "group_name": "expense_group"},
        content_type="application/json",
    )

    # Add members to the group
    client.post(
        "/join_group",
        json={"username": "member1", "group_name": "expense_group"},
        content_type="application/json",
    )
    client.post(
        "/join_group",
        json={"username": "member2", "group_name": "expense_group"},
        content_type="application/json",
    )

    # Add an expense
    response = client.post(
        "/add_expense",
        json={
            "username": "payer",
            "group_name": "expense_group",
            "amount": 300,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "Expense added successfully"

    # Check that the expense was added correctly
    response = client.post(
        "/get_debts",
        json={"username": "payer", "group_name": "expense_group"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify that each member owes 100 (300/3)
    debts = data["debts"]
    assert len(debts) == 2  # Two members owe money to the payer

    # Check that member1 owes 100
    member1_debt = next((debt for debt in debts if debt["username"] == "member1"), None)
    assert member1_debt is not None
    assert member1_debt["status"] == "owes you"
    assert member1_debt["amount"] == 100

    # Check that member2 owes 100
    member2_debt = next((debt for debt in debts if debt["username"] == "member2"), None)
    assert member2_debt is not None
    assert member2_debt["status"] == "owes you"
    assert member2_debt["amount"] == 100


def test_add_expense_nonexistent_group(client):
    # Create a user
    client.post("/login", json={"username": "payer"}, content_type="application/json")

    # Try to add an expense to a nonexistent group
    response = client.post(
        "/add_expense",
        json={
            "username": "payer",
            "group_name": "nonexistent_group",
            "amount": 100,
        },
        content_type="application/json",
    )

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Group does not exist"


def test_add_expense_nonexistent_user(client):
    # Create a group
    client.post("/login", json={"username": "creator"}, content_type="application/json")
    client.post(
        "/create_group",
        json={"username": "creator", "group_name": "test_group"},
        content_type="application/json",
    )

    # Try to add an expense with a nonexistent user
    response = client.post(
        "/add_expense",
        json={
            "username": "nonexistent_user",
            "group_name": "test_group",
            "amount": 100,
        },
        content_type="application/json",
    )

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "User does not exist"


def test_add_expense_not_member(client):
    # Create users
    client.post("/login", json={"username": "creator"}, content_type="application/json")
    client.post(
        "/login", json={"username": "nonmember"}, content_type="application/json"
    )

    # Create a group
    client.post(
        "/create_group",
        json={"username": "creator", "group_name": "test_group"},
        content_type="application/json",
    )

    # Try to add an expense as a non-member
    response = client.post(
        "/add_expense",
        json={
            "username": "nonmember",
            "group_name": "test_group",
            "amount": 100,
        },
        content_type="application/json",
    )

    assert response.status_code == 403
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "User is not a member of this group"


def test_settle_up(client):
    # Create users
    client.post("/login", json={"username": "payer"}, content_type="application/json")
    client.post("/login", json={"username": "debtor"}, content_type="application/json")

    # Create a group
    client.post(
        "/create_group",
        json={"username": "payer", "group_name": "settle_group"},
        content_type="application/json",
    )

    # Add a member to the group
    client.post(
        "/join_group",
        json={"username": "debtor", "group_name": "settle_group"},
        content_type="application/json",
    )

    # Add an expense
    client.post(
        "/add_expense",
        json={
            "username": "payer",
            "group_name": "settle_group",
            "amount": 100,
        },
        content_type="application/json",
    )

    # Settle up
    response = client.post(
        "/settle_up",
        json={"username": "debtor", "group_name": "settle_group", "to_user": "payer"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Settled up successfully"

    # Check that the debt is settled
    response = client.post(
        "/get_debts",
        json={"username": "payer", "group_name": "settle_group"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify that there are no debts
    debts = data["debts"]
    assert len(debts) == 0


def test_kick_user(client):

    # Create users
    client.post("/login", json={"username": "payer"}, content_type="application/json")
    client.post("/login", json={"username": "debtor"}, content_type="application/json")

    # Create a group
    client.post(
        "/create_group",
        json={"username": "payer", "group_name": "kick_group"},
        content_type="application/json",
    )

    # Add a member to the group
    client.post(
        "/join_group",
        json={"username": "debtor", "group_name": "kick_group"},
        content_type="application/json",
    )

    # Add an expense
    client.post(
        "/add_expense",
        json={
            "username": "payer",
            "group_name": "kick_group",
            "amount": 100,
        },
        content_type="application/json",
    )

    response = client.post(
        "/kick_user",
        json={
            "username": "debtor",
            "group_name": "kick_group",
            "target_username": "payer",
        },
    )
    assert response.status_code == 403

    response = client.post(
        "/kick_user",
        json={
            "username": "payer",
            "group_name": "kick_group",
            "target_username": "debtor",
        },
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["group"]) != 0
    assert data["group"]["name"] == "kick_group"
    assert len(data["group"]["transactions"]) == 0
    assert "debtor" not in list(data["group"]["members"])

    # Check that the debt is settled
    response = client.post(
        "/get_debts",
        json={"username": "payer", "group_name": "kick_group"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify that there are no debts
    debts = data["debts"]
    assert len(debts) == 0


    # the last user kicks himself out
    response = client.post(
        "/kick_user",
        json={
            "username": "payer",
            "group_name": "kick_group",
            "target_username": "payer",
        },
        content_type="application/json",
    )

    data = json.loads(response.data)

    assert response.status_code == 200
    assert "payer" not in list(data["group"]["members"])
