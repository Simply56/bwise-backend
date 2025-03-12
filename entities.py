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
    def __init__(self, data):
        super().__init__()
        self.username: str = str(data["username"])

    def store(self, file_path):
        return super().store("users.json")


class Group(Jsonable):
    def __init__(self, data):
        super().__init__()

        self.group_name: str = data["group_name"]
        self.creator: str = data["creator"]

    def store(self, file_path):
        return super().store("groups.json")


class Expense(Jsonable):
    LAST_ID: int = 0

    def __init__(self, data):
        super().__init__()

        Expense.LAST_ID += 1
        self.id: int = Expense.LAST_ID
        self.group: str = str(data["group"])
        self.payer: str = str(data["payer"])
        self.amount: int = float(data["amount"])
        self.submitter: str = str(data["submitter"])

    def store(self):
        return super().store("expenses.json")
