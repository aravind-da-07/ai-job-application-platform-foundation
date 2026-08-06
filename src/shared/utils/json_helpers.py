"""JSON helpers with sane defaults for datetimes, UUIDs, and Decimals."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class PlatformJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def to_json(data: Any, *, indent: int | None = None) -> str:
    return json.dumps(data, cls=PlatformJSONEncoder, indent=indent)


def from_json(raw: str) -> Any:
    return json.loads(raw)
