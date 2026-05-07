import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

@dataclass
class Event:
    type: str          # 'metric', 'anomaly', 'alert'
    source: str        # 'cpu_collector', 'analyzer', etc.
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)