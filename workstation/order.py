from dataclasses import dataclass, fields
import customtkinter as ctk
from datetime import datetime

@dataclass
class Order:
    order_id: str
    original_ws_id: str
    ws_id: str
    side: str
    creation_time: datetime
    label_text: ctk.StringVar
    urgent: bool
    items_dict: dict
    end_time: datetime = None
    end_reason: str = None

    def to_serializable_dict(self):
        """Convert the Order instance into a JSON-serializable dictionary"""
        # Manually construct dict, omitting complex types for now
        serializable_dict = {field.name: getattr(self, field.name) for field in fields(self) if field.name not in ['creation_time', 'label_text', 'end_time']}
        
        # Serialize datetime to ISO format string
        serializable_dict['creation_time'] = self.creation_time.isoformat()
        
        serializable_dict['end_time'] = self.end_time.isoformat() if self.end_time else None

        # Serialize label_text to string (adjust based on your GUI toolkit)
        serializable_dict['label_text'] = str(self.label_text.get()) if self.label_text else None

        # Note: If 'items_dict' contains non-serializable values, further conversion is needed
        
        return serializable_dict


# TODO: implement to_serializable_dict()
@dataclass
class HelpRequest:
    help_id: str
    original_ws_id: str
    ws_id: str
    side: str
    creation_time: datetime
    idle: bool
    help: bool
    label_text: ctk.StringVar

    def to_serializable_dict(self):
        return None
