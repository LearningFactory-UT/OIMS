# backend/models/order.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class Order:
    order_id: str
    ws_id: str
    side: str
    creation_time: datetime
    urgent: bool
    items_dict: Dict[str, int]
    end_time: Optional[datetime] = None
    end_reason: Optional[str] = None

    # For debugging or labeling
    label_text: str = field(default="")

    def to_serializable_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "ws_id": self.ws_id,
            "side": self.side,
            "creation_time": self.creation_time.isoformat(),
            "urgent": self.urgent,
            "items_dict": self.items_dict,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "end_reason": self.end_reason,
            "label_text": self.label_text,
        }