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

def upload_to_container(container_id, file_stream, filename):
    client = docker.from_env()
    container = client.containers.get(container_id)
    
    # Create a ZipFile object in memory
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w') as zip_file:
        zip_file.writestr(filename, file_stream.read())

    zip_stream.seek(0)
    
    # Upload the zip file to the Docker container
    container.put_archive('/path/in/container', zip_stream.read())


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
        data = request.get_json()["id"]
        if not check_id(data): return {"success": False, "error": "Error! :|"}
        tmp = client.containers.get(data)
        tmp.restart(timeout=5)
        return {"success": True}
    except Exception as e:
        print("-"*os.get_terminal_size().columns, e, "-"*os.get_terminal_size().columns)
        return {"success": False, "error": "Error! :|"}
    
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
        data = request.get_json()["id"]
        if not check_id(data): return {"success": False, "error": "Error! :|"}
        tmp = client.containers.get(data)
        tmp.start()
        return {"success": True}
    except Exception as e:
        print("-"*os.get_terminal_size().columns, e, "-"*os.get_terminal_size().columns)
        return {"success": False, "error": "Error! :|"}

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
def create_server_task():
    image = request.args.get("image")
    if not image in VM_IMAGES:
        return {"error": True, "message": f"Error: {image} is not in available images: {VM_IMAGES}", "message_color": MsgColors.warning}
    user = discord.fetch_user()
    if count_user_servers(user.username) >= SERVER_LIMIT:
        return {"error": True, "message": "Error: Server Limit-reached\n\nLogs:\nFailed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached", "message_color": MsgColors.warning}

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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

@app.route("/files", methods=["GET"])
@requires_authorization
def list_files():
    user = discord.fetch_user()
    servers = get_user_servers(user.username)
    
    # List files in local directory
    local_files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    container_files = {}
    for server in servers:
        container = client.containers.get(server.container_name)
        try:
            # Get list of files from container's directory
            bits, stat = container.get_archive('/path/in/container')
            file_list = []
            for member in stat:
                file_list.append(member['path'])
            container_files[server.container_name] = file_list
        except Exception as e:
            container_files[server.container_name] = [f"Error fetching files: {e}"]

    return render_template("file_manager.html", uploaded_files=local_files, container_files=container_files, site_title=SITE_TITLE)


@app.route("/upload", methods=["POST"])
@requires_authorization
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Upload to Docker container
        container_id = request.form.get('container_id')  # Get container ID from form data
        if container_id:
            try:
                upload_to_container(container_id, file, filename)
                return jsonify({"success": True, "message": "File uploaded successfully to container"})
            except Exception as e:
                return jsonify({"success": False, "message": f"Error uploading to container: {e}"})
        
        return jsonify({"success": True, "message": "File uploaded successfully"})
    
    return jsonify({"success": False, "message": "Invalid file format. Only .zip files are allowed"})

@app.route("/download/<filename>", methods=["GET"])
@requires_authorization
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/unzip/<filename>", methods=["POST"])
@requires_authorization
def unzip_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File does not exist"})
    
    if filename.rsplit('.', 1)[1].lower() != 'zip':
        return jsonify({"success": False, "message": "Not a zip file"})

    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            extract_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0])
            os.makedirs(extract_path, exist_ok=True)
            zip_ref.extractall(extract_path)
        return jsonify({"success": True, "message": "File unzipped successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error unzipping file: {e}"})


if __name__ == "__main__":
    app.run(ssl_context=(os.environ["SSL_CERTIFICATE_FILE"], os.environ["SSL_KEY_FILE"]), debug=True, port=5001)
