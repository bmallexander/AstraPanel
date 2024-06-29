import docker
import re
import os
import uuid
from dataclasses import dataclass
from dotenv import load_dotenv
from terminal import terminal
load_dotenv()

from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)

from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

app.secret_key = "0xEssjBdpVDww8yoOhrrArNVIXsTx2QL13mA4AuhIawiCFvGpqSRk5fOFCcsoeXyB6"

app.config["DISCORD_CLIENT_ID"] = "" #Discord client Id from dev panel
app.config["DISCORD_CLIENT_SECRET"] = "" 
app.config["DISCORD_REDIRECT_URI"] = "https://127.0.0.1:5000/callback"
TMATE_API_KEY  = "" #tmate api key(I already got one for astravm)

SERVER_LIMIT   = 12
SITE_TITLE     = "VPSManager"
database_file  = 'database.txt'
VM_IMAGES = ["ubuntu:22.04","ubuntu:20.04","debian:12","debian:11"]

discord = DiscordOAuth2Session(app)

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


@dataclass
class Server:
    id: int
    container_name: str
    ssh_session_line: str
    status: int
    
@dataclass
class MsgColors:
    success=0
    error=1
    warning=2

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
    with open(database_file, "w+") as f:
        data = f.read()
        for line in data.split("\n"):
            if line.startswith(f"{user}|{container_name}|"):
                data = data.replace(line, "")
        f.write(data)
        
def check_id(id):
    user = discord.fetch_user()
    return (id in get_user_server_id(user.username))

@app.route("/")
def base():
    return redirect(url_for("home"))

@app.route("/home")
@requires_authorization
def home():
    user = discord.fetch_user()
    servers = get_user_servers(user.username)
    return render_template("homePage.html", site_title=SITE_TITLE, servers=servers, user=user, servers_count=len(servers))
    
@app.route("/create_new")
@requires_authorization
def create_new():
    user = discord.fetch_user()
    return render_template("newPage.html", site_title=SITE_TITLE, user=user, images=VM_IMAGES)


@app.route("/api/restart", methods=["POST"])
@requires_authorization
def restart():
    try:
        data = request.get_json()["id"]
        if not check_id(data): return {"success": False, "error": "Error! :|"}
        tmp = client.containers.get(data)
        tmp.restart(timeout=5)
        return {"success": True}
    except:
        #not returning the error log to avoid hackers using the response to know what data is required ;)
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
    except:
        #not returning the error log to avoid hackers using the response to know what data is required ;)
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
    except:
        #not returning the error log to avoid hackers using the response to know what data is required ;)
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
    except:
        #not returning the error log to avoid hackers using the response to know what data is required ;)
        return {"success": False, "error": "Error! :|"}

def get_ssh_session_line(container):
    def get_ssh_session(logs):
        match = re.search(r'ssh session: (ssh [^\n]+)', logs)
        if match and "ro-" not in match.group(1):
            return match.group(1)
        return None

    ssh_session_line = None
    max_attempts = 300000
    attempt = 0

    while attempt < max_attempts:
        logs = container.logs().decode('utf-8')
        ssh_session_line = get_ssh_session(logs)
        if ssh_session_line:
            break
        attempt += 1

    return ssh_session_line

def create_server_task(image):
    """```  running apt update
            running apt install tmate -y
            running tmate -F```"""
    
    user = discord.fetch_user()
    if count_user_servers(user.username) >= SERVER_LIMIT:
        return redirect(url_for('home', message="Error: Server Limit-reached\n\nLogs:\nFailed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached", message_color=MsgColors.warning))

    commands = f"""
    apt update && \
    apt install -y tmate && \
    tmate -k {TMATE_API_KEY} -n {uuid.uuid4()} -F
    """

    try:
        container = client.containers.run(image, command="sh -c '{}'".format(commands), detach=True, tty=True)
    except Exception as e:
        return redirect(url_for('home', message=f"Error creating container: {e}", message_color=MsgColors.error))

    ssh_session_line = get_ssh_session_line(container)
    if ssh_session_line:
        add_to_database(user.username, container.name, ssh_session_line)
        return redirect(url_for('home', message="Successfully created VPS", message_color=MsgColors.success))
    else:
        container.stop()
        container.remove()
        return redirect(url_for('home', message="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", message_color=MsgColors.error))

if __name__ == "__main__":
    # app.run(ssl_context='adhoc', debug=True)
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    application = DispatcherMiddleware(app, {
        '/xterm': terminal
    })