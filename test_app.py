import pytest
from app import app
from flask import Flask, jsonify


@pytest.fixture
def client():
    return app.test_client()


def test_client(client):
    body = {"username": "tester"}
    response = client.post("/login", json=body)
    assert response.get_json() == {"success": "login successful"}
    assert response.status_code == 200

    body = {"username": "joiner"}
    response = client.post("/login", json=body)
    assert response.get_json() == {"success": "login successful"}
    assert response.status_code == 200

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

    body = {"group": "test group 1", "username": "joiner"}
    response = client.post("/groups/join", json=body)
    assert response.get_json() == {
        "creator": "tester",
        "members": ["tester", "joiner"],
        "group": "test group 1",
    }
    assert response.status_code == 200
