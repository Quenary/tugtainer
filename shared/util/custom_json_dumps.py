from datetime import date, datetime
from functools import partial
import json


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


custom_json_dumps = partial(json.dumps, default=_json_serializer)
