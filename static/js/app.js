let lastHeartbeat = 0;

// Update rover status
function updateStatus(data) {
    document.getElementById('rover-id').textContent = data.rover_id;
    document.getElementById('rover-name').textContent = data.rover_name;
    document.getElementById('battery-level').textContent = data.battery;
    document.getElementById('last-heartbeat').textContent = new Date(data.timestamp * 1000).toLocaleString();
    
    const statusIndicator = document.getElementById('connection-status');
    if (Date.now() / 1000 - data.timestamp < 10) {
        statusIndicator.className = 'status-indicator online';
    } else {
        statusIndicator.className = 'status-indicator offline';
    }
}

// Add new event to the events widget
function addEvent(event) {
    const eventsWidget = document.getElementById('events-widget');
    const eventElement = document.createElement('div');
    eventElement.innerHTML = `<p><strong>${new Date().toLocaleString()}</strong>: ${event.event_type} - ${event.msg}</p>`;
    eventsWidget.appendChild(eventElement);
    eventsWidget.scrollTop = eventsWidget.scrollHeight;
}

// Control mode change handler
document.getElementById('control-mode').addEventListener('change', function(e) {
    const manualControls = document.getElementById('manual-controls');
    manualControls.style.display = e.target.value === 'manual' ? 'block' : 'none';
});

// Rover control function
function control(command) {
    fetch('/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command: command })
    });
}

// Camera control function
function cameraControl(direction) {
    fetch('/camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ direction: direction })
    });
}

// Add image to gallery
function addImage(imageUrl) {
    const gallery = document.getElementById('image-gallery');
    const img = document.createElement('img');
    img.src = imageUrl;
    gallery.appendChild(img);
    gallery.scrollLeft = gallery.scrollWidth;
}

// Initialize application
function initializeApp() {
    // Poll for heartbeat updates
    setInterval(async () => {
        try {
            const response = await fetch('/latest_heartbeat');
            const data = await response.json();
            if (data) {
                updateStatus(data);
            }
        } catch (error) {
            console.error('Error fetching heartbeat:', error);
        }
    }, 1000);

    // WebSocket connection for events
    const eventsSocket = new WebSocket(`ws://${window.location.host}/ws/events`);
    eventsSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addEvent(data);
    };
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp); 