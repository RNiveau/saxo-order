from enum import StrEnum


class EnumWithGetValue(StrEnum):
    @classmethod
    def get_value(cls, value):
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")
