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
    STORAGE: list["User"] = []

    def __init__(self, username="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))

    @staticmethod
    def get_user(username: str) -> "User" | None:
        for user in User.STORAGE:
            if user.username == username:
                return user
        return None

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(User.FILE_NAME)
        for raw_json_dict in raw_data:
            User.STORAGE.append(User(data=raw_json_dict))

    def store(self):
        return super().store(User.FILE_NAME)

    def good_to_store(self) -> bool:
        for user in User.STORAGE:
            if user.username == self.username:
                return False  # user already exists
        return True


class Group(Jsonable):
    FILE_NAME = "groups.json"
    STORAGE: list["Group"] = []

    def __init__(self, group_name="", creator="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.group_name = str(data.get("group_name", group_name))
        self.creator = str(data.get("creator", creator))

    @staticmethod
    def get_group(group_name: str) -> "Group" | None:
        for group in Group.STORAGE:
            if group.group_name == group_name:
                return group
        return None

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Group.FILE_NAME)
        for raw_json_dict in raw_data:
            Group.STORAGE.append(Group(data=raw_json_dict))

    def store(self):
        return super().store(Group.FILE_NAME)

    def good_to_store(self):
        if not any(lambda u: u == self.creator, User.STORAGE):
            return False  # user not found
        for group in Group.STORAGE:
            if group.group_name == self.group_name:
                return False  # group_name is taken
        return True


class Membership(Jsonable):
    FILE_NAME = "memberships.json"
    STORAGE: list["Membership"] = []

    def __init__(self, username="", group_name="", data=None):
        data = data or {}  # Ensure data is a dictionary
        self.username = str(data.get("username", username))
        self.group_name = str(data.get("group_name", group_name))

    @staticmethod  # TODO: THIS SMELLS BAD
    def get_members(group_name: str) -> list[User]:
        result = []
        for membership in Membership.STORAGE:
            if membership.group_name == group_name:
                for user in User.STORAGE:
                    if user.username == membership.username:
                        result.append(user)
        return result

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Membership.FILE_NAME)
        for raw_json_dict in raw_data:
            Membership.STORAGE.append(Membership(data=raw_json_dict))

    def store(self):
        return super().store(Membership.FILE_NAME)

    def good_to_store(self):
        if not any(lambda u: u.username == self.username, User.STORAGE):
            return False  # user not found
        if not any(lambda g: g.group_name == self.group_name, Group.STORAGE):
            return False  # group not found
        return True


class Transaction(Jsonable):
    FILE_NAME = "transactions.json"
    LAST_ID: int = 0
    STORAGE: list["Transaction"] = []

    def __init__(self, group_name="", payer="", recipient="", amount=0.0, data=None):
        Transaction.LAST_ID += 1
        self.id: int = Transaction.LAST_ID

        data = data or {}
        self.group_name = str(data.get("group_name", group_name))
        self.payer = str(data.get("payer", payer))
        self.recipient = str(data.get("recipient", recipient))
        self.amount = float(data.get("amount", amount))

    @staticmethod
    def load():
        raw_data = Jsonable.load_raw_json(Transaction.FILE_NAME)
        for raw_json_dict in raw_data:
            Transaction.STORAGE.append(Transaction(data=raw_json_dict))

    def store(self):
        return super().store(Transaction.FILE_NAME)

    def good_to_store(self):
        for transaction in Transaction.STORAGE:
            if transaction.id == self.id:
                return False  # id already used

        if not any(lambda g: g.group_name == self.group_name, Group.STORAGE):
            return False  # group not found
        if not any(
            lambda u: u.username == self.payer, Membership.get_members(self.group_name)
        ):
            return False  # payer not a member
        if not any(
            lambda u: u.username == self.recipient,
            Membership.get_members(self.group_name),
        ):
            return False  # recipeint not a member

        return True


# u1 = User("1")
# User.STORAGE.append(u1)
# u2 = User("2")
# print(u2.good_to_store())
