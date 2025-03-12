import json
from flask import jsonify


class Jsonable:
    def to_json(self):
        return jsonify(self.__dict__)

    def store(self, file_path) -> None:
        data = self.load_raw_json(file_path)
        data.append(self.__dict__)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    @staticmethod
    def load_raw_json(file_path: str) -> list[dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                raw_data: list[dict] = json.load(file)

        except (FileNotFoundError, json.JSONDecodeError):
            raw_data = []
        return raw_data


class User(Jsonable):
    FILE_NAME = "users.json"
    STORAGE: list = []

    def __init__(self, username="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))

    def store(self):
        return super().store(User.FILE_NAME)

    @staticmethod
    def load(storage: list):
        raw_data = Jsonable.load_raw_json(User.FILE_NAME)
        for raw_json_dict in raw_data:
            User.STORAGE.append(User(data=raw_json_dict))


class Group(Jsonable):
    FILE_NAME = "groups.json"
    STORAGE: list = []

    def __init__(self, group_name="", creator="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.group_name = str(data.get("group_name", group_name))
        self.creator = str(data.get("creator", creator))

    def store(self):
        return super().store(Group.FILE_NAME)

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Group.FILE_NAME)
        for raw_json_dict in raw_data:
            Group.STORAGE.append(Group(data=raw_json_dict))


class Membership(Jsonable):
    FILE_NAME = "memberships.json"
    STORAGE: list = []

    def __init__(self, username="", group_name="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))
        self.group_name = str(data.get("group_name", group_name))

    def store(self):
        return super().store(Membership.FILE_NAME)

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Membership.FILE_NAME)
        for raw_json_dict in raw_data:
            Membership.STORAGE.append(Membership(data=raw_json_dict))


class Transaction(Jsonable):
    FILE_NAME = "transactions.json"
    LAST_ID: int = 0
    STORAGE: list = []

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

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Transaction.FILE_NAME)
        for raw_json_dict in raw_data:
            Transaction.STORAGE.append(Transaction(data=raw_json_dict))
