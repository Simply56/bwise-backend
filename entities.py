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


class User(Jsonable):
    def __init__(self, username="", data=None):
        super().__init__()

        data = data or {}
        self.username = str(data.get("username", username))

    def store(self, file_path):
        return super().store("users.json")


class Group(Jsonable):
    def __init__(self, group_name="", creator="", data=None):
        super().__init__()

        data = data or {}  # Ensure data is a dictionary
        self.group_name = str(data.get("group_name", group_name))
        self.creator = str(data.get("creator", creator))

    def store(self):
        return super().store("groups.json")


class Membership(Jsonable):
    def __init__(self, username="", group_name="", data=None):
        super().__init__()

        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))
        self.group_name = str(data.get("group_name", group_name))

    def store(self):
        return super().store("memberships.json")


class Transaction(Jsonable):
    LAST_ID: int = 0

    def __init__(self, group="", payer="", recipient="", amount=0.0, data=None):
        super().__init__()

        Transaction.LAST_ID += 1
        self.id: int = Transaction.LAST_ID

        data = data or {}
        self.group = str(data.get("group", group))
        self.payer = str(data.get("payer", payer))
        self.recipient = str(data.get("recipient", recipient))
        self.amount = float(data.get("amount", amount))

    def store(self):
        return super().store("expenses.json")
