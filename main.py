import logging
from typing import Union
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from pydantic import BaseModel
import json
from datetime import datetime
import time

logging.basicConfig(level=logging.DEBUG)

# {"status": "ok", "timestamp": 1698270360.0, "rover_id": 1, "rover_name": "rover_1", "battery": 100}
class Heartbeat(BaseModel):
    status: str
    timestamp: float
    rover_id: int
    rover_name: str
    battery: int

class RoverEvents(BaseModel):
    rover_id: int
    event_type: str
    msg: str

class Control(BaseModel):
    command: str

class CameraControl(BaseModel):
    direction: str

heartbeats = [
    Heartbeat(
        status="ok",
        timestamp=datetime.now().timestamp(),
        rover_id=2,
        rover_name="rover_2",
        battery=95
    ),
    Heartbeat(
        status="ok",
        timestamp=datetime.now().timestamp(),
        rover_id=3,
        rover_name="rover_3",
        battery=87
    )
]

rover_events = [
    RoverEvents(
        rover_id=2,
        event_type="STATUS",
        msg="Rover 2 initialized successfully"
    ),
    RoverEvents(
        rover_id=3,
        event_type="WARNING",
        msg="Low battery warning"
    ),
    RoverEvents(
        rover_id=2,
        event_type="CONTROL",
        msg="Moving forward"
    )
]

connected_clients = []

app = FastAPI()

# Mount templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/heartbeat")
# accept json
def heartbeat(
    heartbeat: Heartbeat,
) -> Heartbeat:
    logging.info(f"Received heartbeat: {heartbeat}")
    heartbeats.append(heartbeat)
    logging.debug("Completed appending heartbeat")
    return heartbeat

@app.post("/events")
def events(event: RoverEvents) -> RoverEvents:
    logging.debug(f"Rover sent an event {event}")
    rover_events.append(event)
    return event

@app.get("/latest_heartbeat")
def get_latest_heartbeat():
    if heartbeats:
        return heartbeats[-1]
    raise HTTPException(status_code=404, detail="No heartbeat data available")

@app.post("/control")
def control_rover(control: Control):
    # Here you would implement actual rover control logic
    event = RoverEvents(
        rover_id=1,  # Assuming rover ID 1
        event_type="CONTROL",
        msg=f"Received control command: {control.command}"
    )
    rover_events.append(event)
    return {"status": "success"}

@app.post("/camera")
def control_camera(camera: CameraControl):
    # Here you would implement actual camera control logic
    event = RoverEvents(
        rover_id=1,  # Assuming rover ID 1
        event_type="CAMERA",
        msg=f"Received camera command: {camera.direction}"
    )
    rover_events.append(event)
    return {"status": "success"}

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Wait for new events and broadcast them
            if rover_events:
                await websocket.send_json(rover_events[-1].dict())
            time.sleep(5)
    except:
        connected_clients.remove(websocket)

