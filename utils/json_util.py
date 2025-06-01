import datetime
import hashlib
import json
from enum import Enum
from typing import Any


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def dumps_indicator(indicator: Any) -> str:
    return json.dumps(indicator, cls=CustomEncoder, sort_keys=True)


def hash_indicator(indicator_str: str) -> str:
    return hashlib.md5(indicator_str.encode("utf-8")).hexdigest()
