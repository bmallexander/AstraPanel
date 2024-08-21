function suspendServer(serverName) {
    fetch('/api/suspend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: serverName })  // Send server name in the request
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Server suspended successfully');
            location.reload(); // Refresh the page to reflect changes
        } else {
            alert('Error suspending server: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
