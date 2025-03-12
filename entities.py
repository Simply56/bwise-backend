import json
from flask import jsonify


# class Hashable:
#     def __eq__(self, other):
#         return (
#             isinstance(other, type(self)) and self.id == other.id
#         )  # Define equality based on `id`
#     # TODO: VERIFY THAT type(self) WORKS

#     def __hash__(self):
#         return hash(self.id)  # Ensures uniqueness in a set

#     def __repr__(self):
#         return f"MyData(id={self.id}, payer={self.payer})"


# TODO: ADD A SECOND CONSTRUCTOR
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

    def store(self):
        return super().store("groups.json")


class Memebership(Jsonable):
    def __init__(self, data):
        super().__init__()

        self.username: str = data["username"]
        self.group_name: str = data["group_name"]

    def store(self):
        return super().store("memberships.json")


class Transaction(Jsonable):
    LAST_ID: int = 0

    def __init__(self, data):
        super().__init__()

        Transaction.LAST_ID += 1
        self.id: int = Transaction.LAST_ID
        self.group: str = str(data["group"])
        self.payer: str = str(data["payer"])
        self.amount: int = float(data["amount"])
        self.submitter: str = str(data["submitter"])

    def store(self):
        return super().store("expenses.json")
