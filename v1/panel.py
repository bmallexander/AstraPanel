import docker, re, os, uuid, pty, os, subprocess, select, termios, struct, fcntl
from dataclasses import dataclass
from flask_socketio import SocketIO
from dotenv import load_dotenv
from CurrencyHandler import CurrencyManager
from datetime import datetime, timedelta
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from flask import jsonify, session
from flask import send_from_directory
from werkzeug.utils import secure_filename

import os
import io
import zipfile
import json

load_dotenv()

print("\nRunning startup.py\n")
import startup
startup.main()
print("\nFinished running startup.py\n")

from flask import Flask, render_template, redirect, url_for, request, session, copy_current_request_context
app = Flask(__name__)

from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

app.config["SECRET_KEY"] = "0xEssjBdpVDww8yoOhrrArNVIXsTx2QL13mA4AuhIawiCFvGpqSRk5fOFCcsoeXyB6"

app.config["DISCORD_CLIENT_ID"]     = os.environ["DISCORD_CLIENT_ID"]
app.config["DISCORD_CLIENT_SECRET"] = os.environ["DISCORD_CLIENT_SECRET"]
app.config["DISCORD_REDIRECT_URI"]  = os.environ["DISCORD_REDIRECT_URI"]
TMATE_API_KEY                       = os.environ["TMATE_API_KEY"]
SERVER_LIMIT                        = int(os.environ["SERVER_LIMIT"])
SITE_TITLE                          = os.environ["SITE_TITLE"]
database_file                       = os.environ["database_file"]
VM_IMAGES                           = os.environ["VM_IMAGES"].split(",")

UPLOAD_FOLDER = 'uploads'

ADMIN_USER_IDS = [1255309054167875637]

SUSPENDED_STATUS_FILE = 'suspended.json'


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


discord = DiscordOAuth2Session(app)
socketio = SocketIO(app, ping_interval=10, async_handlers=False)

last_earn_time = {}
currency_manager = CurrencyManager('user_currencies.json')

@dataclass
class Server:
    id: int
    container_name: str
    ssh_session_line: str
    status: int
    def __eq__(self, other):
        return (self.container_name == other.container_name)
    
@dataclass
class MsgColors:
    success=0
    error=1
    warning=2

def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

# def upload_to_container(container_id, file_stream, filename):
#     client = docker.from_env()
#     container = client.containers.get(container_id)
    
#     # Define container-specific path (assuming /uploads is writable)
#     container_path = f'/uploads/{filename}'

#     # Create a ZipFile object in memory
#     zip_stream = io.BytesIO()
#     with zipfile.ZipFile(zip_stream, 'w') as zip_file:
#         zip_file.writestr(filename, file_stream.read())

#     zip_stream.seek(0)
    
#     try:
#         # Upload the zip file to the Docker container
#         container.put_archive(container_path, zip_stream.read())
#     except docker.errors.APIError as e:
#         raise Exception(f"Error uploading file to container: {e}")


def get_user_plan(user):
    """
    Retrieves the user's plan from the database file.
    """
    if not os.path.exists(database_file):
        return "basic"  # Default plan if database file doesn't exist

    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                parts = line.strip().split('|')
                if len(parts) > 2:  # Assuming the plan is stored in the third part
                    return parts[2]  # The user's plan
    return "basic"  # Default plan if not found


def get_container_usage(container_id):
    try:
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)
        
        cpu_usage = stats['cpu_stats']['cpu_usage']['total_usage']
        memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  # Convert to MB
        
        return cpu_usage, memory_usage
    except Exception as e:
        print(f"Error fetching stats for container {container_id}: {e}")
        return None, None


def is_usage_exceeded(container_id, user_plan):
    cpu_usage, memory_usage = get_container_usage(container_id)
    
    if cpu_usage is None or memory_usage is None:
        return False
    
    with open('plans.json', 'r') as f:
        plans = json.load(f)
    
    plan_limits = plans.get(user_plan, {})
    
    cpu_limit = plan_limits.get('cpu_limit', float('inf'))
    memory_limit = plan_limits.get('memory_limit', float('inf'))
    
    if cpu_usage > cpu_limit or memory_usage > memory_limit:
        return True
    
    return False


def suspend_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.stop()
        
        user = discord.fetch_user()
        update_server_status(user.username, container.name, "suspended")
        
        # Load existing suspended status
        if os.path.exists(SUSPENDED_STATUS_FILE):
            with open(SUSPENDED_STATUS_FILE, 'r') as f:
                suspended_status = json.load(f)
        else:
            suspended_status = {}
        
        # Update the status
        suspended_status[container_id] = {
            'name': container.name,
            'status': 'suspended',
            'timestamp': datetime.now().isoformat()
        }
        
        # Save the updated status to the JSON file
        with open(SUSPENDED_STATUS_FILE, 'w') as f:
            json.dump(suspended_status, f, indent=4)
        
        print(f"Container {container_id} suspended due to exceeding resource limits.")
    except Exception as e:
        print(f"Error suspending container {container_id}: {e}")



def update_server_status(username, container_name, status):
    if not os.path.exists(database_file):
        print("Database file does not exist.")
        return
    
    with open(database_file, 'r') as f:
        lines = f.readlines()
    
    updated = False
    with open(database_file, 'w') as f:
        for line in lines:
            if line.startswith(f"{username}|{container_name}|"):
                f.write(f"{username}|{container_name}|{status}\n")
                updated = True
            else:
                f.write(line)
        
        if not updated:
            f.write(f"{username}|{container_name}|{status}\n")
    
    print("Updated status to:", status)




@app.route("/xterm")
@requires_authorization
def index():
    return render_template("terminal.html", SITE_TITLE=SITE_TITLE, CONTAINER_ID=request.args.get("containerid", ""))

@socketio.on("pty-input", namespace="/pty")
@requires_authorization
def pty_input(data):
    container_id = make_safe(request.args.get("containerid"))
    if session[f"fd-{container_id}"]:
        os.write(session[f"fd-{container_id}"], data["input"].encode())

@socketio.on("resize", namespace="/pty")
@requires_authorization
def resize(data):
    container_id = make_safe(request.args.get("containerid"))
    if session[f"fd-{container_id}"]:
        set_winsize(session[f"fd-{container_id}"], data["rows"], data["cols"])

def make_safe(cid):
    cid = cid.replace(" ", "")
    cid = "".join(list(filter(lambda s: (str.isalnum(s) or s == "_"), cid)))
    user = discord.fetch_user()
    servers = get_user_servers(user.username)
    if not Server(0, cid, "", 0) in servers:
        cid = "\033[0;31m this_is_not_your_server \033[0m"
    return cid

def custom_regex(str):
    regex = [" - - ","["," ",":",":","]"," ", "/socket.io/?containerid=", "&", "HTTP/1.1"]
    last_index = 0
    removed_lenght = 0
    for part in regex:
        if part in str:
            tmp_i = str.index(part)
            if (removed_lenght + tmp_i) > last_index:
                last_index = tmp_i
                str = str[tmp_i + len(part):]
                removed_lenght += tmp_i + len(part)
            else:
                return False
        else:
            return False
    return True

@socketio.on("connect", namespace="/pty")
@requires_authorization
def connect(*args, **kwargs):
    container_id = make_safe(request.args.get("containerid"))
    if session.get(f"proccess-{container_id}", False):
        return

    session[f"fd-{container_id}"] = session[f"exited-{container_id}"] = session[f"child_pid-{container_id}"] = None
    (child_pid, fd) = pty.fork()
    if child_pid == 0:
        "”"
        tmp_args = request.args.get("cmd_args",[])
        if not tmp_args == []:
            tmp_args = tmp_args.split(" ")
            subprocess.run(tmp_args)
        "”"
        subprocess.run(["docker", "exec", "-it", container_id, "/bin/bash"])
        return "this is astravm vpsmanager terminal close exit code"
    else:
        session[f"fd-{container_id}"] = fd
        session[f"child_pid-{container_id}"] = child_pid
        set_winsize(fd, 50, 50)
        
        @copy_current_request_context
        def read_and_forward_pty_output(container_id):
            max_read_bytes = 1024 * 20
            while True:
                socketio.sleep(0.01)
                if session[f"fd-{container_id}"] and session[f"child_pid-{container_id}"]:
                    timeout_sec = 0
                    (data_ready, _, _) = select.select([session[f"fd-{container_id}"]], [], [], timeout_sec)
                    if data_ready:
                        try:
                            if not session[f"exited-{container_id}"]:
                                output = os.read(session[f"fd-{container_id}"], max_read_bytes).decode(
                                    errors="ignore"
                                )
                                if "this is astravm vpsmanager terminal close exit code" in output or "ssl.SSLEOFError: EOF occurred in violation of protocol (_ssl.c:2426)" in output or custom_regex(output):
                                    socketio.emit("pty-output", {"output": "\n\n\n \033[0;31m Disconnected \033[0m", "close_con": True}, namespace="/pty")
                                else:
                                    socketio.emit("pty-output", {"output": output}, namespace="/pty")
                        except:
                            pass
                            # socketio.emit("pty-output", {"output": "\033[0;31m Unable to create connection to the machine \033[0m", "close_con": True}, namespace="/pty")
                            # socketio.server.disconnect(socketio)
        
        socketio.start_background_task(target=lambda: read_and_forward_pty_output(container_id))
        

@app.route("/callback")
def callback():
    discord.callback()
    return redirect(url_for("home"))

@app.route("/login")
def login():
    return discord.create_session()

@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for("login"))

try:
    client = docker.from_env()
except docker.errors.DockerException as e:
    print(f"Error connecting to Docker: {e}")
    exit(1)

def get_user_servers(user):
    servers = []
    count = 0
    if not os.path.exists(database_file):
        return servers
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                l = line.split("|")
                tmp = client.containers.get(l[1])
                servers.append(Server(id=count, container_name=l[1], ssh_session_line=l[2], status=(1 if tmp.status == "running" else 0)))
                count += 1
    return servers

def get_user_server_id(user):
    servers = []
    if not os.path.exists(database_file):
        return servers
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line.split("|")[1])
    return servers

def count_user_servers(user):
    count = 0
    if not os.path.exists(database_file):
        return count
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                count += 1
    return count
    
def add_to_database(user, container_name, ssh_session_line):
    with open(database_file, 'a') as f:
        f.write(f"{user}|{container_name}|{ssh_session_line}\n")
        
def remove_from_database(user, container_name):
    with open(database_file, "r") as f:
        data = f.read()
        for line in data.split("\n"):
            if line.startswith(f"{user}|{container_name}|"):
                data = data.replace(line, "")
        with open(database_file, "w") as f2:
            f2.write(data)
        
def check_id(id):
    user = discord.fetch_user()
    return (id in get_user_server_id(user.username))

@app.route("/")
def base():
    return redirect(url_for("home"))

@app.route("/home")
@requires_authorization
def home():
    user = discord.fetch_user()  # Assuming discord is initialized somewhere
    servers = get_user_servers(user.username)
    currency_balance = currency_manager.get_currency(user.id)  # Fetch user's currency balance
    return render_template("homePage.html", site_title=SITE_TITLE, servers=servers, user=user, servers_count=len(servers), currency_balance=currency_balance)
    


def load_coupons():
    with open('coupons.json', 'r') as f:
        return json.load(f)


@app.route("/coupons")
def coupons():
    coupons_data = load_coupons()
    return render_template("couponsPage.html", site_title=SITE_TITLE, coupons=coupons_data["coupons"])

@app.route("/claim_coupon", methods=["POST"])
@requires_authorization
def claim_coupon():
    coupon_code = request.json.get("coupon_code")
    user = discord.fetch_user()  # Assuming Discord authentication is used
    
    # Load coupons from JSON file
    coupons_data = load_coupons()  # Ensure load_coupons() returns the correct structure
    coupons = coupons_data.get("coupons", {})  # Get the "coupons" dictionary from loaded data
    
    # Check if coupon code exists
    if coupon_code in coupons:
        coupon_details = coupons[coupon_code]
        
        # Check if the coupon has expired
        if datetime.strptime(coupon_details["valid_until"], "%Y-%m-%d").date() < datetime.today().date():
            return jsonify({"success": False, "message": "Coupon has expired."})
        
        # Check if the coupon has reached its maximum claims
        if len(coupon_details["claimed_by"]) >= coupon_details["max_claims"]:
            return jsonify({"success": False, "message": "Coupon has reached its maximum claims."})
        
        # Check if the user has already claimed the coupon
        if user.id in coupon_details["claimed_by"]:
            return jsonify({"success": False, "message": "You have already claimed this coupon."})
        
        # If all checks pass, redeem the coupon
        coupon_details["claimed_by"].append(user.id)
        
        # Update the coupons.json file
        with open("coupons.json", "w") as f:
            json.dump(coupons_data, f, indent=4)
        
        # Perform any additional actions like adding currency to the user's account
        currency_manager.update_currency(user.id, coupon_details["amount"])
        
        return jsonify({"success": True, "message": f"You have successfully claimed {coupon_details['amount']} units."})
    else:
        return jsonify({"success": False, "message": "Invalid coupon code."})
    

    
    
@app.route("/create_new")
@requires_authorization
def create_new():
    user = discord.fetch_user()
    return render_template("newPage.html", site_title=SITE_TITLE, user=user, images=VM_IMAGES)

@app.route("/earn-coins", methods=["GET"])
def earn_coins():
    discord_user_id = session.get('DISCORD_USER_ID')
    discord_oauth2_token = session.get('DISCORD_OAUTH2_TOKEN')

    if discord_user_id is None or discord_oauth2_token is None:
        return redirect(url_for("login"))

    user_id = discord_user_id

    # Check last earning time for authenticated users only
    last_time = last_earn_time.get(user_id)
    if last_time and datetime.now() - last_time < timedelta(minutes=3):
        time_left = int((last_time + timedelta(minutes=3) - datetime.now()).total_seconds())
        return render_template("earnCoins.html", time_left=time_left)

    # Update user's coins and store last earning time
    currency_manager.update_currency(user_id, 5)
    last_earn_time[user_id] = datetime.now()

    # Calculate time left until next earning (3 minutes cooldown)
    time_left = 180  

    return render_template("earnCoins.html", time_left=time_left)



@app.route("/api/restart", methods=["POST"])
@requires_authorization
def restart():
    try:
        data = request.get_json().get("id")
        
        if not check_id(data):
            return jsonify({"success": False, "error": "Invalid server ID"}), 400
        
        container = client.containers.get(data)

        # Check if the container is suspended
        if is_suspended(container.id):
            return jsonify({"success": False, "error": "Container is suspended"}), 403

        container.restart(timeout=5)
        return jsonify({"success": True})
    except Exception as e:
        print("-" * os.get_terminal_size().columns, e, "-" * os.get_terminal_size().columns)
        return jsonify({"success": False, "error": "Error restarting server, You may be suspended !"}), 500

    
@app.route("/api/delete", methods=["POST"])
@requires_authorization
def delete():
    try:
        user = discord.fetch_user()
        data = request.get_json()["id"]
        if not check_id(data): return {"success": False, "error": "Error! :|"}
        tmp = client.containers.get(data)
        tmp.remove(v=True, force=True)
        remove_from_database(user.username, data)
        return {"success": True}
    except Exception as e:
        print("-"*os.get_terminal_size().columns, e, "-"*os.get_terminal_size().columns)
        return {"success": False, "error": "Error! :|"}
    
@app.route("/api/stop", methods=["POST"])
@requires_authorization
def stop():
    try:
        data = request.get_json()["id"]
        if not check_id(data): return {"success": False, "error": "Error! :|"}
        tmp = client.containers.get(data)
        tmp.stop(timeout=5)
        return {"success": True}
    except Exception as e:
        print("-"*os.get_terminal_size().columns, e, "-"*os.get_terminal_size().columns)
        return {"success": False, "error": "Error! :|"}
    
@app.route("/api/start", methods=["POST"])
@requires_authorization
def start():
    try:
        data = request.get_json()
        server_name = data.get("name")

        if not check_name(server_name):
            return jsonify({"success": False, "error": "Invalid server name"}), 400

        container = None
        for c in client.containers.list(all=True):
            if c.name == server_name:
                container = c
                break

        if container is None:
            return jsonify({"success": False, "error": "Container not found"}), 404

        # Check if the container is suspended
        if is_suspended(container.id):
            return jsonify({"success": False, "error": "Container is suspended"}), 403

        container.start()
        
        user = discord.fetch_user()
        update_server_status(user.username, container.name, "started")

        return jsonify({"success": True})
    except Exception as e:
        print("-" * 40, e, "-" * 40)
        return jsonify({"success": False, "error": "Error starting server, You may be suspended !"}), 500

def is_suspended(container_id):
    if not os.path.exists(SUSPENDED_STATUS_FILE):
        return False

    with open(SUSPENDED_STATUS_FILE, 'r') as f:
        suspended_status = json.load(f)

    return container_id in suspended_status and suspended_status[container_id]['status'] == 'suspended'




def get_ssh_session_line(container):
    def get_ssh_session(logs):
        match = re.search(r'ssh session: (ssh [^\n]+)', logs)
        if match and "ro-" not in match.group(1):
            return match.group(1)
        return None

    ssh_session_line = None
    max_attempts = 3000
    attempt = 0

    while attempt < max_attempts:
        logs = container.logs().decode('utf-8')
        ssh_session_line = get_ssh_session(logs)
        if ssh_session_line:
            break
        attempt += 1

    return ssh_session_line

@app.route("/server_creation")
@requires_authorization
def create_server_task():
    image = request.args.get("image")
    if not image in VM_IMAGES:
        return {"error": True, "message": f"Error: {image} is not in available images: {VM_IMAGES}", "message_color": MsgColors.warning}
    
    user = discord.fetch_user()
    user_plan = get_user_plan(user.username)  # Get user's plan
    
    if count_user_servers(user.username) >= SERVER_LIMIT:
        return {"error": True, "message": "Error: Server Limit-reached\n\nLogs:\nFailed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached", "message_color": MsgColors.warning}
    
    if is_usage_exceeded(user.username, user_plan):
        return {"error": True, "message": "Error: Exceeding resource usage limit. Please contact support.", "message_color": MsgColors.warning}
    
    commands = f"""/bin/sh /mnt/tmates/startup.sh -k {TMATE_API_KEY} -n {uuid.uuid4()} -F"""

    response = ""

    response += f"Creating container using {image} ...\n"

    try:
        container = client.containers.run(image, command="{}".format(commands), detach=True, tty=True, volumes={f"{os.getcwd()}/tmates": {'bind': '/mnt/tmates', 'mode': 'ro'}})
    except Exception as e:
        return {"error": True, "message":f"Error creating container: {e}", "message_color": MsgColors.error}

    response += "Container created ✅\n"

    response += "Checking machine's health ...\n"
    
    ssh_session_line = get_ssh_session_line(container)
    if ssh_session_line:
        add_to_database(user.username, container.name, ssh_session_line)
        response += "Successfully created VPS\n"
        return {"error": False, "output":response, "redirect": url_for("home")}
    else:
        container_logs = container.logs().decode("utf-8")
        container.stop()
        container.remove()
        return {"error": True, "message":"Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support." + "\n\nTechnical Logs: " + container_logs, "message_color":MsgColors.error}


@app.route("/admin")
@requires_authorization
def admin_panel():
    user = discord.fetch_user()
    if user.id not in ADMIN_USER_IDS:
        return "Unauthorized", 403  # Admin-only access

    all_servers = []
    for container in client.containers.list(all=True):
        server_status = {
            "id": container.id,
            "name": container.name,
            "status": container.status,
            "resources": get_container_usage(container.id)
        }
        all_servers.append(server_status)

    return render_template("admin_panel.html", servers=all_servers)



SUSPENDED_STATUS_FILE = 'suspended.json'

def update_suspended_status(container_name, status):
    # Load existing suspended status
    if os.path.exists(SUSPENDED_STATUS_FILE):
        with open(SUSPENDED_STATUS_FILE, 'r') as f:
            suspended_status = json.load(f)
    else:
        suspended_status = {}

    # Update the status
    suspended_status[container_name] = {
        'name': container_name,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }

    # Save the updated status to the JSON file
    with open(SUSPENDED_STATUS_FILE, 'w') as f:
        json.dump(suspended_status, f, indent=4)



def check_name(name):
    # Implement your validation logic here
    if not name or len(name) < 3:
        return False
    # Add more validation rules as needed
    return True

def update_server_status(username, container_name, status):
    # Placeholder for actual implementation
    # This could be a database update or another service call
    print(f"Updating status for {container_name} to {status} by {username}")


@app.route("/suspend", methods=["POST"])
@requires_authorization
def suspend():
    try:
        data = request.get_json()
        server_name = data.get("name")

        if not check_name(server_name):
            return jsonify({"success": False, "error": "Invalid server name"}), 400

        container = None
        for c in client.containers.list(all=True):
            if c.name == server_name:
                container = c
                break

        if container is None:
            return jsonify({"success": False, "error": "Container not found"}), 404

        container.stop()

        user = discord.fetch_user()
        update_server_status(user.username, container.name, "suspended")

        suspended_status = {}
        if os.path.exists(SUSPENDED_STATUS_FILE):
            with open(SUSPENDED_STATUS_FILE, 'r') as f:
                suspended_status = json.load(f)

        suspended_status[container.id] = {
            'name': container.name,
            'status': 'suspended',
            'timestamp': datetime.now().isoformat()
        }

        with open(SUSPENDED_STATUS_FILE, 'w') as f:
            json.dump(suspended_status, f, indent=4)

        return jsonify({"success": True})
    except Exception as e:
        print("-" * 40, e, "-" * 40)
        return jsonify({"success": False, "error": "Error suspending server"}), 500









# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

# @app.route("/file_explorer/<container_id>")
# @requires_authorization
# def file_explorer(container_id):
#     # Try to access the container
#     try:
#         container = client.containers.get(container_id)
#     except docker.errors.NotFound:
#         return jsonify({"error": True, "message": "Container not found on the host system"}), 404
#     except Exception as e:
#         return jsonify({"error": True, "message": f"Error accessing container: {e}"}), 500

#     # List files in the container
#     container_files = {}
#     try:
#         bits, stat = container.get_archive('/')
#         container_files[container_id] = [member['path'] for member in stat]
#     except Exception as e:
#         container_files[container_id] = [f"Error fetching files: {e}"]

#     # List files in the upload folder on the host system
#     local_files = os.listdir(app.config['UPLOAD_FOLDER'])

#     return render_template("file_manager.html", 
#                            uploaded_files=local_files, 
#                            container_files=container_files, 
#                            site_title=SITE_TITLE)





# @app.route("/upload/<container_id>", methods=['POST'])
# @requires_authorization
# def upload(container_id):
#     if 'file' not in request.files:
#         return jsonify({"message": "No file part"}), 400

#     file = request.files['file']

#     if file.filename == '':
#         return jsonify({"message": "No selected file"}), 400

#     if not allowed_file(file.filename):
#         return jsonify({"message": "Invalid file type"}), 400

#     try:
#         file_stream = io.BytesIO(file.read())
#         upload_to_container(container_id, file_stream, file.filename)
#         return jsonify({"message": "File uploaded successfully"}), 200
#     except Exception as e:
#         return jsonify({"message": str(e)}), 500




# @app.route("/download/<path:filename>")
# @requires_authorization
# def download(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# @app.route("/unzip/<filename>", methods=["POST"])
# @requires_authorization
# def unzip_file(filename):
#     file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
#     if not os.path.exists(file_path):
#         return jsonify({"success": False, "message": "File does not exist"})
    
#     if filename.rsplit('.', 1)[1].lower() != 'zip':
#         return jsonify({"success": False, "message": "Not a zip file"})

#     try:
#         with zipfile.ZipFile(file_path, 'r') as zip_ref:
#             extract_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0])
#             os.makedirs(extract_path, exist_ok=True)
#             zip_ref.extractall(extract_path)
#         return jsonify({"success": True, "message": "File unzipped successfully"})
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error unzipping file: {e}"})



if __name__ == "__main__":
    app.run(
        host="0.0.0.0", 
        port=5001, 
        ssl_context=(os.environ["SSL_CERTIFICATE_FILE"], os.environ["SSL_KEY_FILE"]), 
        debug=True
    )
