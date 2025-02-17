from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from collections import deque

@dataclass
class RoverStatus:
    rover_id: int
    rover_name: str
    battery: int
    distance: float  # distance from obstacle in cm
    mode: str  # 'manual' or 'autonomous'
    timestamp: float
    camera_pan: int = 0
    camera_tilt: int = 0

@dataclass
class RoverEvent:
    rover_id: int
    event_type: str  # 'STATUS', 'WARNING', 'ERROR', 'CONTROL'
    message: str
    timestamp: float
    
    def to_dict(self):
        return {
            "rover_id": self.rover_id,
            "event_type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp
        }

class EventBuffer:
    def __init__(self, capacity: int = 500):
        self.capacity = capacity
        self.events: deque = deque(maxlen=capacity)
    
    def add_event(self, event: RoverEvent):
        self.events.append(event)
    
    def get_events(self, start: int = 0, limit: int = 50) -> List[dict]:
        """Get events with pagination"""
        events_list = list(self.events)
        # Reverse the list for newest first
        events_list.reverse()
        end = min(start + limit, len(events_list))
        return [event.to_dict() for event in events_list[start:end]]
    
    def get_total_events(self) -> int:
        return len(self.events) 