class EventsTable {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.events = [];
        this.sortField = 'timestamp';
        this.sortAscending = false;
        this.init();
    }

    init() {
        // Create table structure
        this.container.innerHTML = `
            <table class="events-table">
                <thead>
                    <tr>
                        <th data-sort="timestamp">Time ▼</th>
                        <th data-sort="rover_id">Rover ID</th>
                        <th data-sort="event_type">Event Type</th>
                        <th data-sort="msg">Message</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `;

        // Add click handlers for sorting
        const headers = this.container.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.addEventListener('click', () => this.handleSort(header.dataset.sort));
        });
    }

    handleSort(field) {
        if (this.sortField === field) {
            this.sortAscending = !this.sortAscending;
        } else {
            this.sortField = field;
            this.sortAscending = true;
        }
        
        this.updateTable();
        
        // Update header indicators
        const headers = this.container.querySelectorAll('th');
        headers.forEach(header => {
            if (header.dataset.sort === field) {
                header.innerHTML = header.textContent.replace(/[▼▲]/, '') + 
                    (this.sortAscending ? ' ▲' : ' ▼');
            } else {
                header.innerHTML = header.textContent.replace(/[▼▲]/, '');
            }
        });
    }

    addEvent(event) {
        event.timestamp = new Date().toISOString(); // Add timestamp for sorting
        this.events.unshift(event);
        this.updateTable();
    }

    updateTable() {
        const sortedEvents = [...this.events].sort((a, b) => {
            let comparison = 0;
            if (a[this.sortField] < b[this.sortField]) comparison = -1;
            if (a[this.sortField] > b[this.sortField]) comparison = 1;
            return this.sortAscending ? comparison : -comparison;
        });

        const tbody = this.container.querySelector('tbody');
        tbody.innerHTML = sortedEvents.map(event => `
            <tr>
                <td>${new Date(event.timestamp).toLocaleString()}</td>
                <td>${event.rover_id}</td>
                <td>${event.event_type}</td>
                <td>${event.msg}</td>
            </tr>
        `).join('');
    }
} 