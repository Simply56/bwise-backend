import pytest
from app import app
from flask import Flask, jsonify

@pytest.fixture
def client():
    return app.test_client()

def test_api(client):
    body = {"username": "test"}
    response = client.post("/login", json=body)
    assert response.status_code == 200
    assert response.get_json() == {"success": "login successful"}



def test_api1(client):
    body = {"username": "test"}
    response = client.post("/login", json=body)
    assert response.status_code == 200
    assert response.get_json() == {"success": "login successful"}