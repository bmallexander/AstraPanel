// Function to add a working model animation overlay
window.add_working_model = function () {
    // Create a semi-transparent overlay div
    let blur = document.createElement("div");
    blur.setAttribute("style", "user-select:none;position: fixed; top:0px; left:0px; height:100%; width:100%; background:rgba(0,0,0,0.15); z-index: 9999999999999");

    // Add CSS styles for animation
    let css = document.createElement("style");
    css.innerHTML = `.animation-container {
        display: flex;
        position: absolute;
        bottom: 50%;
        right: 50%;
        align-items: center;
        text-align: center;
        transform: rotate(90deg) translate(-50%, -50%);
    }

    .letter.X {
        animation: move-letter_x 4s ease-in-out infinite;
    }
    .letter.Y {
        animation: move-letter_y 4s ease-in-out infinite;
    }
    .letter.Z {
        animation: move-letter_z 4s ease-in-out infinite;
    }

    @keyframes move-letter_x {
        0% {
            transform: rotate(0deg) translateX(150px) rotate(0deg);
        }
        50% {
            transform: rotate(360deg) translateX(20px) rotate(-360deg);
        }
        100% {
            transform: rotate(0deg) translateX(150px) rotate(0deg);
        }
    }
    @keyframes move-letter_y {
        0% {
            transform: rotate(360deg) translateX(150px) rotate(-360deg);
        }
        50% {
            transform: rotate(0deg) translateX(80px) rotate(0deg);
        }
        100% {
            transform: rotate(360deg) translateX(150px) rotate(-360deg);
        }
    }
    @keyframes move-letter_z {
        0% {
            transform: rotate(0deg) translateX(150px) rotate(0deg);
        }
        50% {
            transform: rotate(360deg) translateX(140px) rotate(-360deg);
        }
        100% {
            transform: rotate(0deg) translateX(150px) rotate(0deg);
        }  
    }`;

    // Create animation container with letters
    let animation_container = document.createElement("div");
    animation_container.className = "animation-container";
    animation_container.innerHTML = `<div class="letter X">🔴</div>
                                     <div class="letter Y">🟢</div>
                                     <div class="letter Z">🔵</div>`;

    // Append elements to the body
    blur.append(animation_container);
    document.body.append(blur);
    document.body.append(css);

    // Return references to the created elements (blur and css)
    return [blur, css];
}

// Function to make a POST request with JSON data
window.post = function (url, data) {
    return fetch(url, {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

// Function to handle server restart
async function restart(id) {
    let t = window.add_working_model(); // Display animation overlay
    let data = await (await window.post("/api/restart", { "id": id.split("/")[1] })).json(); // Send restart request
    if (data.success) {
        location.reload(); // Reload page on success
    } else {
        document.body.removeChild(t[0]); // Remove animation overlay on failure
        document.body.removeChild(t[1]); // Remove animation overlay CSS
        window.messagebox({ type: 0, message: "We were unable to restart the machine.\nTry again" }); // Show error message
    }
}

// Function to handle server start
async function start(id) {
    let t = window.add_working_model(); // Display animation overlay
    let data = await (await window.post("/api/start", { "id": id.split("/")[1] })).json(); // Send start request
    if (data.success) {
        location.reload(); // Reload page on success
    } else {
        document.body.removeChild(t[0]); // Remove animation overlay on failure
        document.body.removeChild(t[1]); // Remove animation overlay CSS
        window.messagebox({ type: 0, message: "We were unable to start the machine.\nTry again" }); // Show error message
    }
}

// Function to handle server stop
async function stop(id) {
    let t = window.add_working_model(); // Display animation overlay
    let data = await (await window.post("/api/stop", { "id": id.split("/")[1] })).json(); // Send stop request
    if (data.success) {
        location.reload(); // Reload page on success
    } else {
        document.body.removeChild(t[0]); // Remove animation overlay on failure
        document.body.removeChild(t[1]); // Remove animation overlay CSS
        window.messagebox({ type: 0, message: "We were unable to stop the machine.\nTry again" }); // Show error message
    }
}

// Function to handle server deletion
async function remove(id) {
    let tmp = window.promptbox({ message: "Type '" + id + "' in the box below to remove it" }); // Prompt user for confirmation
    if (tmp.trim() == id) { // Check user input
        let t = window.add_working_model(); // Display animation overlay
        let data = await (await window.post("/api/delete", { "id": id.split("/")[1] })).json(); // Send delete request
        if (data.success) {
            location.reload(); // Reload page on success
        } else {
            document.body.removeChild(t[0]); // Remove animation overlay on failure
            document.body.removeChild(t[1]); // Remove animation overlay CSS
            window.messagebox({ type: 0, message: "We were unable to delete the machine.\nTry again" }); // Show error message
        }
    }
}

// Function to open console for a server
function open_console(id) {
    window.open(`${location.protocol}/xterm?containerid=${id.split("/")[1]}`, "_blank"); // Open console in a new tab
}

// Load message_popups.js script after the page loads
var script = document.createElement("script");
script.src = "/static/js/message_popups.js";
document.body.append(script);
