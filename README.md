# Rover Control Application

A web-based control interface for the Picar-X rover with camera streaming, object detection, and manual/autonomous control modes.

## Features

- Live video streaming from rover camera
- Manual and autonomous driving modes
- Camera pan/tilt controls
- Snapshot capture capability
- Object detection using YOLO
- Color analysis
- Event logging
- Responsive web interface

## Prerequisites

### Hardware
- Picar-X rover
- Raspberry Pi with camera module
- Network connection

### Software
- Python 3.7+
- pip (Python package installer)
- OpenCV
- SunFounder Vilib

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd rover-control
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Download YOLO model files:
```bash
# Create a models directory
mkdir models
cd models

# Download YOLOv3 weights (236MB)
wget https://pjreddie.com/media/files/yolov3.weights

# Download YOLOv3 configuration
wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg

# Download COCO class names
wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names

cd ..
```

4. Update the model paths in `rover_controller.py`:
```python
self.net = cv2.dnn.readNet(
    "models/yolov3.weights",
    "models/yolov3.cfg"
)

with open("models/coco.names", "r") as f:
    self.classes = [line.strip() for line in f.readlines()]
```

## Starting the Application

1. Make sure your Picar-X is powered on and connected to your network.

2. Start the rover control server:
```bash
python rover_server.py
```

3. Access the web interface:
- Open a web browser
- Navigate to `http://<raspberry-pi-ip>:8000`
- Default port is 8000

## Usage

### Manual Control
- Click "Manual Mode" to enable manual controls
- Use arrow buttons for movement
- Use camera controls to adjust view

### Object Detection
1. Click "Analyze Image" to perform object detection
2. Results will show in a popup modal with:
   - Annotated image
   - Detected objects with confidence scores
   - Dominant colors analysis
3. Press ESC to close the results modal

### Snapshots
- Click "Take Snapshot" to capture the current view
- View snapshots in the Snapshots tab
- Last 10 snapshots are preserved

## Event Types
- STATUS: System status updates
- CONTROL: Movement commands
- ANALYSIS: Object detection results
- WARNING: System warnings
- ERROR: Error messages

## File Structure
```
rover-control/
├── rover_server.py      # FastAPI server
├── rover_controller.py  # Rover control logic
├── rover_data.py       # Data models
├── templates/          # HTML templates
│   └── index.html
├── static/            # Static files
│   ├── css/
│   │   └── styles.css
│   └── snapshots/     # Captured images
└── models/           # YOLO model files
    ├── yolov3.weights
    ├── yolov3.cfg
    └── coco.names
```

## Troubleshooting

### Common Issues

1. Camera not working:
   - Check camera connection
   - Ensure camera is enabled in Raspberry Pi configuration
   - Verify camera permissions

2. Object detection fails:
   - Verify YOLO model files are downloaded correctly
   - Check file paths in code
   - Ensure OpenCV is installed with DNN support

3. Movement controls not responding:
   - Check if rover is in manual mode
   - Verify hardware connections
   - Check battery level

### Error Messages

- "Failed to capture frame": Camera access issue
- "Model file not found": YOLO model files missing
- "Movement command ignored": Wrong mode or hardware issue

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Local Development Setup

1. Download required vendor files:
```bash
# Create directories for vendor files
mkdir -p static/vendor/bootstrap/css
mkdir -p static/vendor/bootstrap/js
mkdir -p static/vendor/fontawesome/css
mkdir -p static/vendor/fontawesome/webfonts

# Download Bootstrap files
wget https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css -O static/vendor/bootstrap/css/bootstrap.min.css
wget https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js -O static/vendor/bootstrap/js/bootstrap.bundle.min.js

# Download Font Awesome files
wget https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css -O static/vendor/fontawesome/css/all.min.css
wget https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/webfonts/fa-solid-900.woff2 -O static/vendor/fontawesome/webfonts/fa-solid-900.woff2
wget https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/webfonts/fa-solid-900.ttf -O static/vendor/fontawesome/webfonts/fa-solid-900.ttf
```

2. Update Font Awesome CSS paths:
   After downloading the Font Awesome files, you'll need to update the font paths in the CSS file. Edit `static/vendor/fontawesome/css/all.min.css` and replace all references to webfonts with local paths:
   - Replace `../webfonts/` with `../webfonts/`
   - This ensures the fonts are loaded from your local server

Now the application can run without an internet connection, serving all resources locally.
