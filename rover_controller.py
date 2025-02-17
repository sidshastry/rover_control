from picarx import Picarx
import time
from datetime import datetime
from rover_data import RoverStatus, RoverEvent, EventBuffer
from typing import Optional
import threading
from vilib import Vilib  # Import sunfounder's video library
import base64
import cv2
import os

class Constants:
    # Drive settings
    SAFE_DISTANCE = 40  # cm
    DANGER_DISTANCE = 20  # cm
    MOVE_SPEED = 15
    BACKUP_SPEED = 7
    TURN_ANGLE = 30  # degrees
    
    # Camera settings
    CAMERA_DEFAULT_ANGLE = 0
    
    # Timing settings
    STATUS_UPDATE_INTERVAL = 0.5
    AUTONOMOUS_DRIVE_INTERVAL = 0.25
    BACKUP_STEP_DELAY = 0.25
    BACKUP_STEPS = 3

class RoverController:
    def __init__(self, rover_id: int = 1, rover_name: str = "rover_1"):
        self.px = Picarx()
        self.event_buffer = EventBuffer()
        self.running = True
        self.mode = "autonomous"
        self.rover_id = rover_id
        self.rover_name = rover_name
        self.battery = 100  # Mock battery level
        
        # Initialize camera and servos
        self.px.set_dir_servo_angle(Constants.CAMERA_DEFAULT_ANGLE)
        self.px.set_cam_pan_angle(Constants.CAMERA_DEFAULT_ANGLE)
        self.px.set_cam_tilt_angle(Constants.CAMERA_DEFAULT_ANGLE)
        
        # Initialize video streaming
        Vilib.camera_start(vflip=False, hflip=True)  # Try different flip combinations
        # Start video server on port 9000
        Vilib.display(local=False, web=True)  # Web display only
        # Note: vilib uses port 9000 by default
        self.add_event("STATUS", "Camera streaming started on port 9000")
        
        self._shutdown_event = threading.Event()
        self._threads = []
        
        # Create snapshots directory if it doesn't exist
        self.snapshots_dir = "static/snapshots"
        os.makedirs(self.snapshots_dir, exist_ok=True)
        self.max_snapshots = 10  # Keep last 10 snapshots
    
    def get_status(self) -> dict:
        """Get current rover status"""
        status = RoverStatus(
            rover_id=self.rover_id,
            rover_name=self.rover_name,
            battery=self.battery,
            distance=self.px.ultrasonic.read(),
            mode=self.mode,
            timestamp=datetime.now().timestamp(),
            camera_pan=self.px.cam_pan.angle,
            camera_tilt=self.px.cam_tilt.angle
        )
        # Convert to dict to avoid serialization issues
        return {
            "rover_id": status.rover_id,
            "rover_name": status.rover_name,
            "battery": status.battery,
            "distance": status.distance,
            "mode": status.mode,
            "timestamp": status.timestamp,
            "camera_pan": status.camera_pan,
            "camera_tilt": status.camera_tilt
        }
    
    def add_event(self, event_type: str, message: str):
        """Add a new event to the buffer"""
        event = RoverEvent(
            rover_id=self.rover_id,
            event_type=event_type,
            message=message,
            timestamp=datetime.now().timestamp()
        )
        self.event_buffer.add_event(event)
    
    def handle_movement_command(self, command: str):
        """Handle manual movement commands"""
        if self.mode != "manual":
            self.add_event("WARNING", "Movement command ignored - not in manual mode")
            return False
            
        if command == "forward":
            self.px.forward(Constants.MOVE_SPEED)
        elif command == "backward":
            self.px.backward(Constants.MOVE_SPEED)
        elif command == "left":
            self.px.set_dir_servo_angle(-Constants.TURN_ANGLE)
            self.px.forward(Constants.MOVE_SPEED)
        elif command == "right":
            self.px.set_dir_servo_angle(Constants.TURN_ANGLE)
            self.px.forward(Constants.MOVE_SPEED)
        elif command == "stop":
            self.px.forward(0)
            self.px.set_dir_servo_angle(0)
        
        self.add_event("CONTROL", f"Manual command executed: {command}")
        return True
    
    def handle_camera_command(self, pan: Optional[int] = None, tilt: Optional[int] = None):
        """Handle camera movement commands"""
        if pan is not None:
            self.px.set_cam_pan_angle(pan)
        if tilt is not None:
            self.px.set_cam_tilt_angle(tilt)
        self.add_event("CONTROL", f"Camera adjusted to pan:{pan} tilt:{tilt}")
        return True
    
    def set_mode(self, new_mode: str):
        """Switch between manual and autonomous modes"""
        if new_mode not in ["manual", "autonomous"]:
            return False
            
        self.mode = new_mode
        if new_mode == "manual":
            self.px.forward(0)  # Stop the rover
            self.px.set_dir_servo_angle(0)
            
        self.add_event("STATUS", f"Mode changed to {new_mode}")
        return True
    
    def autonomous_drive(self):
        """Autonomous driving logic"""
        while not self._shutdown_event.is_set():
            if self.mode == "autonomous":
                distance = round(self.px.ultrasonic.read(), 2)
                
                if distance >= Constants.SAFE_DISTANCE:
                    self.px.set_dir_servo_angle(0)
                    self.px.forward(Constants.MOVE_SPEED)
                    
                elif distance >= Constants.DANGER_DISTANCE:
                    self.px.set_dir_servo_angle(Constants.TURN_ANGLE)
                    self.px.forward(Constants.MOVE_SPEED)
                    
                else:
                    self.add_event("WARNING", f"Obstacle detected at {distance}cm")
                    self.px.set_dir_servo_angle(-Constants.TURN_ANGLE)
                    for _ in range(Constants.BACKUP_STEPS):
                        if self._shutdown_event.is_set():
                            break
                        self.px.backward(Constants.BACKUP_SPEED)
                        time.sleep(Constants.BACKUP_STEP_DELAY)
                    self.px.forward(Constants.MOVE_SPEED)
                
            time.sleep(Constants.AUTONOMOUS_DRIVE_INTERVAL)
    
    def start(self):
        """Start the rover controller"""
        self._shutdown_event.clear()
        autonomous_thread = threading.Thread(target=self.autonomous_drive, daemon=True)
        autonomous_thread.start()
        self._threads.append(autonomous_thread)
        
        try:
            while not self._shutdown_event.is_set():
                # Simulate battery drain
                self.battery = max(0, self.battery - 0.1)
                time.sleep(Constants.STATUS_UPDATE_INTERVAL)
        except KeyboardInterrupt:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self._shutdown_event.set()
        self.px.forward(0)  # Stop movement
        self.px.set_dir_servo_angle(0)  # Center steering
        self.px.set_cam_pan_angle(0)  # Center camera
        self.px.set_cam_tilt_angle(0)
        
        # Wait for threads to finish
        for thread in self._threads:
            thread.join(timeout=1.0)
            
        Vilib.camera_close()
    
    def take_snapshot(self) -> dict:
        """Take a snapshot and save it"""
        try:
            # Get frame from vilib
            frame = Vilib.img
            if frame is None:
                self.add_event("ERROR", "Failed to take snapshot: No frame available")
                return {"success": False, "error": "No frame available"}
                
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{timestamp}.jpg"
            filepath = os.path.join(self.snapshots_dir, filename)
            
            self.add_event("STATUS", f"Saving snapshot to {filepath}")
            
            # Save the image
            cv2.imwrite(filepath, frame)
            
            # Keep only the last N snapshots
            snapshots = sorted([f for f in os.listdir(self.snapshots_dir) if f.startswith("snapshot_")])
            if len(snapshots) > self.max_snapshots:
                for old_file in snapshots[:-self.max_snapshots]:
                    old_path = os.path.join(self.snapshots_dir, old_file)
                    self.add_event("STATUS", f"Removing old snapshot: {old_file}")
                    os.remove(old_path)
            
            self.add_event("STATUS", f"Snapshot taken: {filename}")
            return {
                "success": True,
                "filename": filename,
                "timestamp": timestamp
            }
        except Exception as e:
            error_msg = f"Failed to take snapshot: {str(e)}"
            self.add_event("ERROR", error_msg)
            print(f"Snapshot error: {error_msg}")  # Console logging
            return {"success": False, "error": str(e)}
    
    def get_snapshots(self) -> list:
        """Get list of available snapshots"""
        try:
            snapshots = sorted([f for f in os.listdir(self.snapshots_dir) if f.startswith("snapshot_")])
            return [{
                "filename": f,
                "timestamp": datetime.strptime(f[9:-4], "%Y%m%d_%H%M%S").isoformat()
            } for f in snapshots]
        except Exception as e:
            self.add_event("ERROR", f"Failed to list snapshots: {str(e)}")
            return [] 