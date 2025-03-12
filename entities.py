import json
from flask import jsonify


class Jsonable:
    def to_json(self):
        return jsonify(self.__dict__)

    def store(self, file_path) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data: list = json.load(file)

        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        data.append(self.__dict__)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def load_raw_json(self, file_path: str) -> list[dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                raw_data: list[dict] = json.load(file)

        except (FileNotFoundError, json.JSONDecodeError):
            raw_data = []
        return raw_data


class User(Jsonable):
    FILE_NAME = "users.json"

    def __init__(self, username="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))

    def store(self):
        return super().store(User.FILE_NAME)


class Group(Jsonable):
    FILE_NAME = "groups.json"

    def __init__(self, group_name="", creator="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.group_name = str(data.get("group_name", group_name))
        self.creator = str(data.get("creator", creator))

    def store(self):
        return super().store(Group.FILE_NAME)


class Membership(Jsonable):
    FILE_NAME = "memberships.json"

    def __init__(self, username="", group_name="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))
        self.group_name = str(data.get("group_name", group_name))

    def store(self):
        return super().store(Membership.FILE_NAME)


class Transaction(Jsonable):
    FILE_NAME = "transactions.json"
    LAST_ID: int = 0

    def __init__(self, group="", payer="", recipient="", amount=0.0, data=None):
        Transaction.LAST_ID += 1
        self.id: int = Transaction.LAST_ID

        data = data or {}
        self.group = str(data.get("group", group))
        self.payer = str(data.get("payer", payer))
        self.recipient = str(data.get("recipient", recipient))
        self.amount = float(data.get("amount", amount))

    def store(self):
        return super().store(Transaction.FILE_NAME)
