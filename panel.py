import docker
import re
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for, session
app = Flask(__name__)

try:
    client = docker.from_env()
except docker.errors.DockerException as e:
    print(f"Error connecting to Docker: {e}")
    # exit(1)

SERVER_LIMIT   = 12
SITE_TITLE     = "VPSManager"
database_file  = 'database.txt'

def get_user_servers(user):
    servers = []
    if not os.path.exists(database_file):
        return servers
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line)
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

@app.route("/home")
def home():
    return render_template("homePage.html", site_title=SITE_TITLE, user_servers=get_user_servers(session.get("username")))
    
# @bot.tree.command(name="list", description="Lists all your servers")
# async def list_servers(interaction: discord.Interaction):
#     user = str(interaction.user)
#     servers = get_user_servers(user)
#     if servers:
#         embed = discord.Embed(title="Your Servers", color=0x00ff00)
#         for server in servers:
#             _, container_name, _ = server.split('|')
#             embed.add_field(name=container_name, value="Type: Dedicated Docker Container ", inline=False)
#         await interaction.response.send_message(embed=embed)
#     else:
#         await interaction.response.send_message(embed=discord.Embed(description="You have no servers.", color=0xff0000))

# @bot.tree.command(name="help", description="Shows the help message")
# async def help_command(interaction: discord.Interaction):
#     embed = discord.Embed(title="Help", color=0x00ff00)
#     embed.add_field(name="/deploy-ubuntu", value="Creates a new server with Ubuntu 22.04", inline=False)
#     embed.add_field(name="/deploy-debian", value="Creates a new server with Debian 12", inline=False)
#     embed.add_field(name="/deploy-alpine", value="Creates a new server with Alpine", inline=False)
#     embed.add_field(name="/remove <ssh_command/Name>", value="Removes a server", inline=False)
#     embed.add_field(name="/restart <ssh_command/Name>", value="Restart a server (Disabled)", inline=False)
#     embed.add_field(name="/start <ssh_command/Name>", value="Start a server (Disabled)", inline=False)
#     embed.add_field(name="/stop <ssh_command/Name>", value="Stop a server (Disabled)", inline=False)
#     embed.add_field(name="/list", value="List all your server", inline=False)
#     embed.add_field(name="/support", value="Provides support server link", inline=False)
#     await interaction.response.send_message(embed=embed)

# async def support(interaction: discord.Interaction):
#     await interaction.response.send_message(embed=discord.Embed(description="Join our support server: https://discord.gg/is-a-space", color=0x00ff00))

# async def get_ssh_session_line(container):
#     def get_ssh_session(logs):
#         match = re.search(r'ssh session: (ssh [^\n]+)', logs)
#         if match and "ro-" not in match.group(1):
#             return match.group(1)
#         return None

#     ssh_session_line = None
#     max_attempts = 300000
#     attempt = 0

#     while attempt < max_attempts:
#         logs = container.logs().decode('utf-8')
#         ssh_session_line = get_ssh_session(logs)
#         if ssh_session_line:
#             break
#         attempt += 1

#     return ssh_session_line

# async def create_server_task(interaction: discord.Interaction):
#     await interaction.response.send_message(embed=discord.Embed(description="Creating server, This takes a few seconds.\n```running apt update\nrunning apt install tmate -y\nrunning tmate -F```", color=0x00ff00))
#     user = str(interaction.user)
#     if count_user_servers(user) >= SERVER_LIMIT:
#         await interaction.followup.send(embed=discord.Embed(description="Error: Server Limit-reached\n\nLog: ```Failed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached```", color=0xff0000))
#         return

#     image = "ubuntu:22.04"
#     commands = """
#     apt update && \
#     apt install -y tmate && \
#     tmate -F
#     """

#     try:
#         container = client.containers.run(image, command="sh -c '{}'".format(commands), detach=True, tty=True)
#     except Exception as e:
#         await interaction.followup.send(embed=discord.Embed(description=f"Error creating container: {e}", color=0xff0000))
#         return

#     ssh_session_line = await get_ssh_session_line(container)
#     if ssh_session_line:
#         await interaction.user.send(embed=discord.Embed(description=f"### Successfully created VPS\n SSH Session Command: ```{ssh_session_line}```Powered by [AstraVM](https://discord.gg/bQvSuDfww8)\nOS:Ubuntu 22.04", color=0x00ff00))
#         add_to_database(user, container.name, ssh_session_line)
#         await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
#     else:
#         await interaction.followup.send(embed=discord.Embed(description="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", color=0xff0000))
#         container.stop()
#         container.remove()

# async def create_server_task_debian(interaction: discord.Interaction):
#     await interaction.response.send_message(embed=discord.Embed(description="Creating server, This takes a few seconds.\n\nLog:```running apt update\nrunning apt install tmate -y\nrunning tmate -F```", color=0x00ff00))
#     user = str(interaction.user)
#     if count_user_servers(user) >= SERVER_LIMIT:
#         await interaction.followup.send(embed=discord.Embed(description="Error: Server Limit-reached\n```Failed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached```", color=0xff0000))
#         return

#     image = "debian:12"
#     commands = """
#     apt update && \
#     apt install -y tmate && \
#     tmate -F
#     """

#     try:
#         container = client.containers.run(image, command="sh -c '{}'".format(commands), detach=True, tty=True)
#     except Exception as e:
#         await interaction.followup.send(embed=discord.Embed(description=f"Error creating container: {e}", color=0xff0000))
#         return

#     ssh_session_line = await get_ssh_session_line(container)
#     if ssh_session_line:
#         await interaction.user.send(embed=discord.Embed(description=f"### Successfully created VPS\n SSH Session Command: ```{ssh_session_line}```Powered by [AstraVM](https://discord.gg/bQvSuDfww8)\nOS: Debian 12", color=0x00ff00))
#         add_to_database(user, container.name, ssh_session_line)
#         await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
#     else:
#         await interaction.followup.send(embed=discord.Embed(description="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", color=0xff0000))
#         container.stop()
#         container.remove()