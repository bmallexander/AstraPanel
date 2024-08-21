// Function to handle suspending a server
function suspendServer(serverName) {
    // Confirm action with the user
    const confirmation = confirm(`Are you sure you want to suspend ${serverName}?`);
    if (!confirmation) {
        return; // Exit if the user cancels
    }

    // Make an HTTP request to suspend the server
    fetch('/suspend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: serverName })
    })
    .then(response => response.json())
    .then(data => {
        // Handle response from the server
        if (data.success) {
            alert(`${serverName} has been suspended.`);
            location.reload(); // Reload the page to update the status
        } else {
            alert(`Failed to suspend ${serverName}.`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while suspending the server.');
    });
}



