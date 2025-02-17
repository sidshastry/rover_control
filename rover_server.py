from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from rover_controller import RoverController
import signal
import sys
import requests
import aiohttp
import io

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize rover controller
rover = RoverController()

class CameraCommand(BaseModel):
    pan: Optional[int] = None
    tilt: Optional[int] = None

class ModeCommand(BaseModel):
    mode: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    return rover.get_status()

@app.get("/api/events")
async def get_events(start: int = 0, limit: int = 50):
    events = rover.event_buffer.get_events(start, limit)
    total = rover.event_buffer.get_total_events()
    
    # Events are already dicts, no need to convert
    return {
        "events": events,  # events are already converted to dicts in get_events()
        "total": total,
        "has_more": (start + limit) < total
    }

@app.post("/api/control/{command}")
async def control_rover(command: str):
    success = rover.handle_movement_command(command)
    return {"success": success}

@app.post("/api/camera")
async def control_camera(command: CameraCommand):
    success = rover.handle_camera_command(command.pan, command.tilt)
    return {"success": success}

@app.post("/api/mode")
async def set_mode(command: ModeCommand):
    success = rover.set_mode(command.mode)
    return {"success": success}

@app.post("/api/snapshot")
async def take_snapshot():
    return rover.take_snapshot()

@app.get("/api/snapshots")
async def get_snapshots():
    return {"snapshots": rover.get_snapshots()}

@app.get("/video_feed")
async def video_feed():
    """Proxy the vilib video feed"""
    async def video_stream():
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9000/mjpg") as response:
                async for chunk in response.content.iter_chunked(8192):
                    yield chunk

    return StreamingResponse(
        video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

def signal_handler(signum, frame):
    print("\nShutting down gracefully...")
    rover.cleanup()
    sys.exit(0)

def start_server():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start rover controller in a separate thread
    import threading
    threading.Thread(target=rover.start, daemon=True).start()
    
    # Start web server
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_server() 