// Function to add a working model animation overlay
window.addWorkingModel = function () {
    // Create a semi-transparent overlay
    const overlay = document.createElement("div");
    overlay.style.cssText = "user-select:none;position:fixed;top:0;left:0;height:100%;width:100%;background:rgba(0,0,0,0.15);z-index:9999999999999";

    // Add CSS styles for animation
    const styles = document.createElement("style");
    styles.innerHTML = `
        .animation-container {
            display: flex;
            position: absolute;
            bottom: 50%;
            right: 50%;
            align-items: center;
            text-align: center;
            transform: rotate(90deg) translate(-50%, -50%);
        }
        .letter.X { animation: move-letter-x 4s ease-in-out infinite; }
        .letter.Y { animation: move-letter-y 4s ease-in-out infinite; }
        .letter.Z { animation: move-letter-z 4s ease-in-out infinite; }
        
        @keyframes move-letter-x {
            0% { transform: rotate(0deg) translateX(150px); }
            50% { transform: rotate(360deg) translateX(20px) rotate(-360deg); }
            100% { transform: rotate(0deg) translateX(150px); }
        }
        @keyframes move-letter-y {
            0% { transform: rotate(360deg) translateX(150px); }
            50% { transform: rotate(0deg) translateX(80px); }
            100% { transform: rotate(360deg) translateX(150px); }
        }
        @keyframes move-letter-z {
            0% { transform: rotate(0deg) translateX(150px); }
            50% { transform: rotate(360deg) translateX(140px) rotate(-360deg); }
            100% { transform: rotate(0deg) translateX(150px); }
        }`;

    // Create animation container with letters
    const animationContainer = document.createElement("div");
    animationContainer.className = "animation-container";
    animationContainer.innerHTML = `
        <div class="letter X">🔴</div>
        <div class="letter Y">🟢</div>
        <div class="letter Z">🔵</div>`;

    // Append elements to the overlay
    overlay.append(animationContainer);
    document.body.append(overlay);
    document.body.append(styles);

    return [overlay, styles];
}

// Function to make a POST request with JSON data
window.post = async function (url, data) {
    const response = await fetch(url, {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response.json();
}

// Function to handle server operations
async function handleServerOperation(endpoint, id, successMessage, errorMessage) {
    const overlayData = window.addWorkingModel(); // Show overlay
    const response = await window.post(endpoint, { id: id.split("/")[1] });

    if (response.success) {
        location.reload(); // Reload on success
    } else {
        // Remove overlay on failure
        document.body.removeChild(overlayData[0]);
        document.body.removeChild(overlayData[1]);
        window.messagebox({ type: 0, message: errorMessage });
    }
}

// Function to restart server
async function restart(id) {
    await handleServerOperation("/api/restart", id, "Restarting...", "Unable to restart the machine. Please try again.");
}

// Function to start server
async function start(id) {
    await handleServerOperation("/api/start", id, "Starting...", "Unable to start the machine. Please try again.");
}

// Function to stop server
async function stop(id) {
    await handleServerOperation("/api/stop", id, "Stopping...", "Unable to stop the machine. Please try again.");
}

// Function to delete server
async function remove(id) {
    const confirmation = window.promptbox({ message: `Type '${id}' to confirm deletion` });

    if (confirmation.trim() === id) {
        await handleServerOperation("/api/delete", id, "Deleting...", "Unable to delete the machine. Please try again.");
    }
}

// Function to open console for a server
function openConsole(id) {
    window.open(`${location.protocol}/xterm?containerid=${id.split("/")[1]}`, "_blank");
}

// Load message popups script after the page loads
const script = document.createElement("script");
script.src = "/static/js/message_popups.js";
document.body.append(script);
