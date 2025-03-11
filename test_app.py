import pytest
from app import app
from flask import Flask, jsonify


@pytest.fixture
def client():
    return app.test_client()


def test_client(client):
    # login as tester
    body = {"username": "tester"}
    response = client.post("/login", json=body)
    assert response.get_json() == {"success": "login successful"}
    assert response.status_code == 200

    # login as joiner
    body = {"username": "joiner"}
    response = client.post("/login", json=body)
    assert response.get_json() == {"success": "login successful"}
    assert response.status_code == 200

    # create test goup 1
    body = {
        "group": "test group 1",
        "creator": "tester",
    }
    response = client.post("/groups/create", json=body)
    assert response.get_json() == {
        "creator": "tester",
        "members": ["tester"],
        "group": "test group 1",
    }
    assert response.status_code == 201

    # joiner joins test group 1
    body = {"group": "test group 1", "username": "joiner"}
    response = client.post("/groups/join", json=body)
    assert response.get_json() == {
        "creator": "tester",
        "members": ["tester", "joiner"],
        "group": "test group 1",
    }
    assert response.status_code == 200

    # tester add an expense to test group 1
    body = {
        "group": "test group 1",
        "payer": "tester",
        "amount": 20,
        "submitter": "tester",
    }
    response = client.post("/expenses", json=body)
    assert response.get_json() == {
        "id": 0,
        "payer": "tester",
        "submitter": "tester",
        "amount": 20,
        "group": "test group 1",
    }
    assert response.status_code == 201
