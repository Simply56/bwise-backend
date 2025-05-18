import pytest
from app import app
import json
import os


@pytest.fixture
def client():
    # Reset global variables
    from app import USERS, GROUPS

    USERS.clear()
    GROUPS.clear()

    app.testing = True
    yield app.test_client()

    # Ensure files don't exist
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")


@pytest.fixture
def empty_files():

    with open("users.json", "w") as f:
        f.write("")

    with open("groups.json", "w") as f:
        f.write("")

    yield

    # Cleanup after tests
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")


@pytest.fixture
def noisy_files():
    """Fixture to create test files with random garbage"""
    from app import GROUPS_FILE, USERS_FILE
    from random import randbytes

    # Ensure files don't exist
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")

    with open(USERS_FILE, "bw") as f:
        f.write(randbytes(100))

    with open(GROUPS_FILE, "bw") as f:
        f.write(randbytes(100))

    yield

    # Cleanup after tests
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")


@pytest.fixture
def setup_test_files():
    """Fixture to create test files with known data"""
    with open("users.json", "w") as f:
        f.write('["user1", "user2", "user3"]')

    with open("groups.json", "w") as f:
        f.write(
            '[{"name": "test_group", "creator": "user1", "members": ["user1", "user2", "user3"], "transactions": [{"from_user": "user1", "to_user": "user3", "amount": 100.0}, {"from_user": "user2", "to_user": "user3", "amount": 100.0}]}]'
        )

    yield

    # Cleanup after tests
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")


def test_load_data_missing_files():
    """Test that load_data handles missing files gracefully"""
    from app import load_data

    # Ensure files don't exist
    if os.path.exists("users.json"):
        os.remove("users.json")
    if os.path.exists("groups.json"):
        os.remove("groups.json")

    # Clear existing data
    test_user_dict = dict()
    test_group_dict = dict()

    # Load data (should not raise any errors)
    load_data(test_user_dict, test_group_dict)

    # Verify no data was loaded
    assert len(test_user_dict) == 0
    assert len(test_group_dict) == 0


def test_load_empty_files(empty_files):
    """Test that load_data handles empty files gracefully"""
    from app import load_data

    # Clear existing data
    test_user_dict = dict()
    test_group_dict = dict()

    # Load data (should not raise any errors)
    load_data(test_user_dict, test_group_dict)

    # Verify no data was loaded
    assert len(test_user_dict) == 0
    assert len(test_group_dict) == 0


def test_load_data_users(setup_test_files):
    """Test that users are loaded correctly from file"""
    from app import load_data

    test_user_dict = dict()
    test_group_dict = dict()

    load_data(test_user_dict, test_group_dict)

    # Verify users were loaded
    assert len(test_user_dict) == 3  # Changed from USERS.keys() to just USERS
    assert "user1" in test_user_dict
    assert "user2" in test_user_dict
    assert "user3" in test_user_dict

    # Verify user objects are correct
    assert test_user_dict["user1"].username == "user1"
    assert test_user_dict["user2"].username == "user2"
    assert test_user_dict["user3"].username == "user3"


def test_load_data_groups(setup_test_files):
    """Test that groups and their transactions are loaded correctly"""
    from app import load_data

    test_user_dict = dict()
    test_group_dict = dict()

    load_data(test_user_dict, test_group_dict)
    # Verify group was loaded
    assert len(test_group_dict) == 1
    assert "test_group" in test_group_dict

    group = test_group_dict["test_group"]

    # Verify group properties
    assert group.name == "test_group"
    assert group.creator == "user1"
    assert set(group.members) == {"user1", "user2", "user3"}

    # Verify transactions
    assert len(group.transactions) == 2

    # Verify first transaction
    assert group.transactions[0].from_user == "user1"
    assert group.transactions[0].to_user == "user3"
    assert group.transactions[0].amount == 100.0

    # Verify second transaction
    assert group.transactions[1].from_user == "user2"
    assert group.transactions[1].to_user == "user3"
    assert group.transactions[1].amount == 100


def test_load_invalid_data(noisy_files):
    from app import load_data

    test_user_dict = dict()
    test_group_dict = dict()

    load_data(test_user_dict, test_group_dict)

    # Verify no data was loaded
    assert len(test_user_dict) == 0
    assert len(test_group_dict) == 0


def test_all_have_message(client):
    """Verifies that the every endpoint return json with the key 'message'"""
    missing_message = []

    for rule in app.url_map.iter_rules():
        if "<" in rule.rule:
            continue
        response = client.post(
            rule.rule,
            json={"username": "messenger"},
            content_type="application/json",
        )

        # Ensure it's JSON and contains "message"
        try:
            data = response.get_json(force=True)
            if not isinstance(data, dict) or "message" not in data:
                missing_message.append(
                    (rule.rule, "missing or invalid 'message'")
                )
        except Exception as e:
            missing_message.append((rule.rule, f"not JSON: {e}"))

        assert (
            not missing_message
        ), "Some routes did not return a valid 'message':\n" + "\n".join(
            f"{route}: {reason}" for route, reason in missing_message
        )


def test_client_not_found(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_login_new_user(client):
    response = client.post(
        "/login",
        json={"username": "testuser1"},
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["username"] == "testuser1"


def test_login_existing_user(client):
    # First create a user
    client.post(
        "/login",
        json={"username": "testuser2"},
        content_type="application/json",
    )

    # Then try to login with the same user
    response = client.post(
        "/login",
        json={"username": "testuser2"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == "testuser2"


def test_login_missing_username(client):
    response = client.post("/login", json={}, content_type="application/json")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data


def test_create_group_empty_empty(client):
    response = client.post(
        "/create_group",
        json={},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert 400 <= response.status_code < 500


def test_create_group_not_empty_empty(client):
    # Create a user first
    client.post(
        "/login",
        json={"username": "testuser1"},
        content_type="application/json",
    )

    response = client.post(
        "/create_group",
        json={"username": "testuser1"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert 400 <= response.status_code < 500


def test_create_group_empty_not_empty(client):
    response = client.post(
        "/create_group",
        json={"group_name": "testgroup2"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert 400 <= response.status_code < 500


def test_create_group_not_empty_not_empty(client):
    # Create a user first
    client.post(
        "/login",
        json={"username": "testuser2"},
        content_type="application/json",
    )

    response = client.post(
        "/create_group",
        json={"username": "testuser2", "group_name": "testgroup3"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert response.status_code == 201


def test_create_group_user_exists_group_exists(client):
    # Create a user first
    client.post(
        "/login",
        json={"username": "testuser3"},
        content_type="application/json",
    )

    # Create a group first
    client.post(
        "/create_group",
        json={"username": "testuser3", "group_name": "testgroup4"},
        content_type="application/json",
    )

    # Try to create the same group again
    response = client.post(
        "/create_group",
        json={"username": "testuser3", "group_name": "testgroup4"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert response.status_code == 409


def test_create_group_user_not_exists_group_exists(client):
    # Create a group first with another user
    client.post(
        "/login",
        json={"username": "testuser4"},
        content_type="application/json",
    )
    client.post(
        "/create_group",
        json={"username": "testuser4", "group_name": "testgroup5"},
        content_type="application/json",
    )

    # Try to create the same group with a non-existent user
    response = client.post(
        "/create_group",
        json={"username": "nonexistentuser", "group_name": "testgroup5"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert response.status_code == 404


def test_create_group_user_exists_group_not_exists(client):
    # Create a user first
    client.post(
        "/login",
        json={"username": "testuser5"},
        content_type="application/json",
    )

    # Try to create a new group
    response = client.post(
        "/create_group",
        json={"username": "testuser5", "group_name": "testgroup6"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert response.status_code == 201


def test_create_group_user_exists_group_exists_creator(client):
    # Create a user first
    client.post(
        "/login",
        json={"username": "testuser6"},
        content_type="application/json",
    )

    # Create a group first
    client.post(
        "/create_group",
        json={"username": "testuser6", "group_name": "testgroup7"},
        content_type="application/json",
    )

    # Try to create the same group again as the creator
    response = client.post(
        "/create_group",
        json={"username": "testuser6", "group_name": "testgroup7"},
        content_type="application/json",
    )

    assert "message" in json.loads(response.data)
    assert response.status_code == 409


def test_join_group(client):
    # First create a user and a group
    client.post(
        "/login",
        json={"username": "groupcreator"},
        content_type="application/json",
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup3"},
        content_type="application/json",
    )

    # Create another user
    client.post(
        "/login", json={"username": "joiner"}, content_type="application/json"
    )

    # Join the group
    response = client.post(
        "/join_group",
        json={"username": "joiner", "group_name": "testgroup3"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "joiner" in data["group"]["members"]


def test_join_group_already_member(client):
    # First create a user and a group
    client.post(
        "/login",
        json={"username": "groupcreator"},
        content_type="application/json",
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
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data


def test_delete_group(client):
    # First create a user and a group
    client.post(
        "/login",
        json={"username": "groupcreator"},
        content_type="application/json",
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

    # Verify the group is deleted
    response = client.post(
        "/join_group",
        json={"username": "joiner", "group_name": "testgroup5"},
        content_type="application/json",
    )
    assert response.status_code == 404


def test_delete_group_not_creator(client):
    # First create a user and a group
    client.post(
        "/login",
        json={"username": "groupcreator"},
        content_type="application/json",
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup6"},
        content_type="application/json",
    )

    # Create another user
    client.post(
        "/login", json={"username": "joiner"}, content_type="application/json"
    )

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
    assert "message" in data


def test_admin_delete_group(client):
    # First create a user and a group
    client.post(
        "/login",
        json={"username": "groupcreator"},
        content_type="application/json",
    )
    client.post(
        "/create_group",
        json={"username": "groupcreator", "group_name": "testgroup7"},
        content_type="application/json",
    )

    # Create an admin user
    client.post(
        "/login",
        json={"username": "adminuser"},
        content_type="application/json",
    )

    # Admin deletes the group
    response = client.post(
        "/delete_group",
        json={"username": "adminuser", "group_name": "testgroup7"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_get_user_groups(client):
    # Create a user
    client.post(
        "/login",
        json={"username": "testuser3"},
        content_type="application/json",
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
    client.post(
        "/login", json={"username": "payer"}, content_type="application/json"
    )
    client.post(
        "/login", json={"username": "member1"}, content_type="application/json"
    )
    client.post(
        "/login", json={"username": "member2"}, content_type="application/json"
    )

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

    assert len(debts) == 3

    # Check that member1 owes 100
    member1_debt = next(
        (debt for debt in debts if debt["username"] == "member1"), None
    )
    assert member1_debt is not None
    assert member1_debt["status"] == "owes you"
    assert member1_debt["amount"] == 100

    # Check that member2 owes 100
    member2_debt = next(
        (debt for debt in debts if debt["username"] == "member2"), None
    )
    assert member2_debt is not None
    assert member2_debt["status"] == "owes you"
    assert member2_debt["amount"] == 100

    # Check that payer owes nothing to himself
    payer_debt = next(
        (debt for debt in debts if debt["username"] == "payer"), None
    )
    assert payer_debt is not None
    assert payer_debt["status"] == "settled up"
    assert payer_debt["amount"] == 0


def test_add_expense_nonexistent_group(client):
    # Create a user
    client.post(
        "/login", json={"username": "payer"}, content_type="application/json"
    )

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
    assert "message" in data


def test_add_expense_nonexistent_user(client):
    # Create a group
    client.post(
        "/login", json={"username": "creator"}, content_type="application/json"
    )
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
    assert "message" in data


def test_add_expense_not_member(client):
    # Create users
    client.post(
        "/login", json={"username": "creator"}, content_type="application/json"
    )
    client.post(
        "/login",
        json={"username": "nonmember"},
        content_type="application/json",
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
    assert "message" in data


def test_settle_up(client):
    # Create users
    client.post(
        "/login", json={"username": "payer"}, content_type="application/json"
    )
    client.post(
        "/login", json={"username": "debtor"}, content_type="application/json"
    )

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
        json={
            "username": "debtor",
            "group_name": "settle_group",
            "to_user": "payer",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)

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
    for debt in debts:
        assert debt["amount"] == 0.0


def test_kick_user(client):

    # Create users
    client.post(
        "/login", json={"username": "payer"}, content_type="application/json"
    )
    client.post(
        "/login", json={"username": "debtor"}, content_type="application/json"
    )

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
    for debt in debts:
        assert debt["amount"] == 0.0
        assert debt["username"] != "debtor"

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


@pytest.mark.report_tracemalloc
def test_performance(client):
    size = 10
    users: list[str] = [str(i) for i in range(size)]
    # Create users
    for user in users:
        client.post(
            "/login", json={"username": user}, content_type="application/json"
        )

    for creator in users:
        # Create a group
        group_name = creator + "'s group"
        client.post(
            "/create_group",
            json={"username": creator, "group_name": group_name},
            content_type="application/json",
        )
        for member in users:
            # Add a members to the group each group
            client.post(
                "/join_group",
                json={"username": member, "group_name": group_name},
                content_type="application/json",
            )

    for user in users:
        group_name = user + "'s group"
        # Add an expense
        client.post(
            "/add_expense",
            json={
                "username": user,
                "group_name": group_name,
                "amount": 100,
            },
            content_type="application/json",
        )
