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
    const carouselContainer = document.getElementById('carousel-container');
    const isFirst = carouselContainer.children.length === 0;
    
    const item = document.createElement('div');
    item.className = `carousel-item ${isFirst ? 'active' : ''}`;
    
    const img = document.createElement('img');
    img.src = imageUrl;
    img.className = 'd-block w-100';
    img.style.height = '400px';  // Fixed height for carousel
    img.style.objectFit = 'cover';  // Maintain aspect ratio
    
    item.appendChild(img);
    carouselContainer.appendChild(item);
}

// Add this function to handle media container height
function adjustMediaContainerHeight() {
    const leftColumn = document.querySelector('.left-column');
    const mediaCard = document.querySelector('.media-card');
    
    if (leftColumn && mediaCard) {
        const leftColumnHeight = leftColumn.offsetHeight;
        mediaCard.style.height = `${leftColumnHeight}px`;
    }
}

// Update the initialization function
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
    const eventsTable = new EventsTable('events-container');

    // Update your websocket message handler
    eventsSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        eventsTable.addEvent(data);
    };

    // Add height adjustment
    adjustMediaContainerHeight();
    
    // Handle window resize
    window.addEventListener('resize', adjustMediaContainerHeight);
    
    // Handle tab changes (in case they affect height)
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', adjustMediaContainerHeight);
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);

// Make sure the height is adjusted after all content is loaded
window.addEventListener('load', adjustMediaContainerHeight); 