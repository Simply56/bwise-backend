import json
from flask import jsonify


class Jsonable:
    def to_json(self):
        return jsonify(self.__dict__)

    def store(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data: list = json.load(file)  # Load the list from the JSON file
        except (FileNotFoundError, json.JSONDecodeError):
            data = []  # If file is empty or doesn't exist, start with an empty list

        data.append(self.__dict__)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)


class User(Jsonable):
    def __init__(self, username="", data=None):
        super().__init__()
        if data:
            self.username: str = str(data["username"])
        else:
            self.username: str = str(username)

    def store(self, file_path):
        return super().store("users.json")


class Group(Jsonable):
    def __init__(self, group_name="", creator="", data=None):
        super().__init__()
        if data:
            self.group_name: str = str(data["group_name"])
            self.creator: str = str(data["creator"])
        else:
            self.group_name: str = str(group_name)
            self.group_name: str = str(creator)

    def store(self):
        return super().store("groups.json")


class Memebership(Jsonable):
    def __init__(self, username="", group_name="", data=None):
        super().__init__()
        if data:
            self.username: str = str(data["username"])
            self.group_name: str = str(data["group_name"])
        else:
            self.username: str = str(username)
            self.group_name: str = str(group_name)

    def store(self):
        return super().store("memberships.json")


class Transaction(Jsonable):
    LAST_ID: int = 0

    def __init__(self, group="", payer="", recipient="", amount=0.0, data=None):
        super().__init__()

        Transaction.LAST_ID += 1
        self.id: int = Transaction.LAST_ID

        if data:
            self.group: str = str(data["group"])
            self.payer: str = str(data["payer"])
            self.recipient: str = str(data["recipient"])
            self.amount: float = float(data["amount"])
        else:
            self.group = str(group)
            self.payer = str(payer)
            self.recipient = str(recipient)
            self.amount = float(amount)

    def store(self):
        return super().store("expenses.json")
