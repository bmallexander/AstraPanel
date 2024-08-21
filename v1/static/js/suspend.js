document.addEventListener('DOMContentLoaded', () => {
    const suspendButtons = document.querySelectorAll('.suspend-btn');
    
    suspendButtons.forEach(button => {
        button.addEventListener('click', () => {
            const containerId = button.getAttribute('data-container-id');
            suspendServer(containerId);
        });
    });
});

function suspendServer(containerId) {
    fetch('/api/suspend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: containerId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Server suspended successfully');
            // Update the UI or redirect as necessary
        } else {
            alert('Error suspending server: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
