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
import numpy as np
from PIL import Image
import colorsys

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
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RoverController, cls).__new__(cls)
        return cls._instance

    def __init__(self, rover_id: int = 1, rover_name: str = "rover_1"):
        # Only initialize once
        if not RoverController._initialized:
            self.px = Picarx()
            self.event_buffer = EventBuffer()
            self.running = True
            self.mode = "manual"
            self.rover_id = rover_id
            self.rover_name = rover_name
            self.battery = 100  # Mock battery level
            
            # Initialize camera and servos
            self.px.set_dir_servo_angle(Constants.CAMERA_DEFAULT_ANGLE)
            self.px.set_cam_pan_angle(Constants.CAMERA_DEFAULT_ANGLE)
            self.px.set_cam_tilt_angle(Constants.CAMERA_DEFAULT_ANGLE)
            
            self.add_event("STATUS", "Camera streaming started on port 9000")
            
            self._shutdown_event = threading.Event()
            self._threads = []
            
            # Create snapshots directory if it doesn't exist
            self.snapshots_dir = "static/snapshots"
            os.makedirs(self.snapshots_dir, exist_ok=True)
            self.max_snapshots = 10  # Keep last 10 snapshots
            
            RoverController._initialized = True

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = cls(*args, **kwargs)
        return cls._instance

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

    def initialize_vision(self):
        """Initialize vision capabilities"""
        Vilib.camera_start(vflip=False, hflip=True)
        Vilib.display(local=True, web=True)
        
        # Load YOLO model
        self.net = cv2.dnn.readNet(
            "yolov3.weights",
            "yolov3.cfg"
        )
        
        # Load class names
        with open("coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        # Get output layer names
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]

    def analyze_current_view(self):
        """Analyze the current camera view for objects and colors"""
        try:
            # Capture current frame using Vilib.img
            frame = Vilib.img
            if frame is None:
                return {'success': False, 'error': 'Failed to capture frame'}

            height, width = frame.shape[:2]

            # Create blob from image
            blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            self.net.setInput(blob)
            outs = self.net.forward(self.output_layers)

            # Process detections
            class_ids = []
            confidences = []
            boxes = []

            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > 0.5:  # Confidence threshold
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            # Apply non-max suppression
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
            
            # Process results
            objects = []
            for i in range(len(boxes)):
                if i in indexes:
                    objects.append({
                        'class': self.classes[class_ids[i]],
                        'confidence': confidences[i]
                    })

                    # Draw detection on frame
                    x, y, w, h = boxes[i]
                    label = f"{self.classes[class_ids[i]]}: {confidences[i]:.2f}"
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Convert frame to RGB format for color analysis
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            colors = self._analyze_colors(frame_rgb)
            
            # Save the annotated frame
            cv2.imwrite("static/latest_analysis.jpg", frame)

            # Log the analysis results
            if objects:
                object_names = [obj['class'] for obj in objects]
                self.add_event("ANALYSIS", f"Objects detected: {', '.join(object_names)}")
            else:
                self.add_event("ANALYSIS", "No objects detected")

            if colors:
                color_names = [f"{color['name']} ({(color['percentage'] * 100):.1f}%)" for color in colors[:3]]
                self.add_event("ANALYSIS", f"Dominant colors: {', '.join(color_names)}")
            
            return {
                'success': True,
                'objects': objects,
                'colors': colors,
                'image_url': '/static/latest_analysis.jpg'
            }
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")  # Add debug print
            self.add_event("ERROR", f"Analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _analyze_colors(self, frame, num_colors=5):
        """Analyze dominant colors in the frame"""
        try:
            # Convert to PIL Image
            img = Image.fromarray(frame)
            
            # Resize for faster processing
            img = img.resize((150, 150))
            
            # Get colors from image
            pixels = np.float32(img).reshape(-1, 3)
            
            # Use k-means to find dominant colors
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
            flags = cv2.KMEANS_RANDOM_CENTERS
            _, labels, palette = cv2.kmeans(pixels, num_colors, None, criteria, 10, flags)
            
            # Calculate color percentages
            _, counts = np.unique(labels, return_counts=True)
            total_pixels = sum(counts)
            percentages = counts / total_pixels
            
            # Convert RGB to HSV for color naming
            colors = []
            for color, percentage in zip(palette, percentages):
                rgb = color / 255
                hsv = colorsys.rgb_to_hsv(*rgb)
                color_name = self._get_color_name(hsv)
                
                colors.append({
                    'name': color_name,
                    'percentage': float(percentage)
                })
            
            # Sort by percentage
            colors.sort(key=lambda x: x['percentage'], reverse=True)
            return colors
            
        except Exception as e:
            print(f"Error analyzing colors: {e}")
            return []

    def _get_color_name(self, hsv):
        """Convert HSV values to color names"""
        h, s, v = hsv
        
        # Convert hue to 360 degree format
        h *= 360
        
        if s < 0.1:
            if v < 0.2:
                return "black"
            elif v > 0.8:
                return "white"
            return "gray"
            
        if h < 30:
            return "red"
        elif h < 90:
            return "yellow"
        elif h < 150:
            return "green"
        elif h < 210:
            return "cyan"
        elif h < 270:
            return "blue"
        elif h < 330:
            return "magenta"
        else:
            return "red" 