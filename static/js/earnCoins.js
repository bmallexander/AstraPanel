// JavaScript for countdown timer
function startEarning() {
    // Disable the earn coins button to prevent multiple clicks
    document.getElementById('earn-coins-btn').disabled = true;

    // Set the countdown time (in seconds)
    var countdownTime = 180; // 3 minutes
    var timerDisplay = document.getElementById('timer');

    // Update timer display every second
    var countdownInterval = setInterval(function() {
        var minutes = Math.floor(countdownTime / 60);
        var seconds = countdownTime % 60;

        // Format the time display (e.g., 05:00)
        timerDisplay.textContent = (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;

        // Decrease countdown time
        countdownTime--;

        // Stop countdown when time hits zero
        if (countdownTime < 0) {
            clearInterval(countdownInterval);
            timerDisplay.textContent = '00:00';
            // Call a function to initiate earning process on backend
            earnCoins();
        }
    }, 1000);
}

// JavaScript function to initiate earning process (AJAX request to backend)
function earnCoins() {
    // Send AJAX request to your Flask backend
    fetch('/earn-coins', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}' // Include CSRF token if using Flask-WTF CSRF protection
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Handle successful response from backend
        alert('Coins earned successfully!');
        window.location.href = '/home'; // Redirect to home page after earning coins
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to earn coins. Please try again later.');
        window.location.href = '/home'; // Redirect to home page on error
    });
}
