# redteamscripts - Cyber Defense Techniques

Author: Me :)
Made for CSEC-473 Cyber Defense Techniques's Red Team Tool

## To set up
Follow these steps to set up the C2. Ultimately, it should work in any order, but I have tested it this way
1. Adjust the client script's variable that stores the Server's IP address to the IP address of the linux machine your server is running on.
2. Start the server script on a separate linux machine
3. Run the bash script. This will start the client script and alter its process name as well as clean up after itself. 
4. If running the shell command, start a listener using `nc -lvnp <port>`

Note: If the server isn't set up, then the client should still be able to run. It will just recieve a regular ICMP Echo Response from the server's machine if it is reachable. Currently, if the client is unable to send ping requests it will ~~error out and stop the script. I will probably fix this and have it keep attempting to ping or figure something out so the script remains active.~~ continue attempting to ping.

## C2 Client (client.py)
### Purpose
This script creates a persistent backdoor on a target system. It communicates with the attacker's machine by using ICMP packets, to avoid detection. Depending on the commands recieved by the attacker's machine, it can execute shell commands, or spawn a reverse shell as a separate process. 

#### Persistence Mechanisms
1. Creates a copy of itself to a location on the target system, ~~`/tmp/.hidden_icmp_client` (i will probably rename this to something more obscure soon)~~ `/tmp/.sysd`.
2. Creates an entry in crontab to restart on system reboot

## C2 Server (server.py)
### Purpose
This script listens for incoming ICMP packets from clients that are running the client script above. Attackers can then respond with commands that can either send commands, or spawn a reverse shell. It includes the following features:
1. Client Management - Has the ability to track multiple clients, where the attacker can then target a specific client to execute commands. It also will remove stale clients that do not respond within a defined period.
2. Console - As mentioned above, the attacker can utilize the console to send commands back to the client to execute, or spawn a reverse shell.

#### Commands
1. `clients` - Lists all the clients that are currently connected and pinging the server
2. `target <client_id>` - Each client generates a unique ID, that way it can be distinguished from other sessions. This command allows you to interact with a specific client so you can send commands to it.
3. `shell <port>` - Sends a command to the client to open up a reverse shell from the hardcoded IP address and the specified port, that way this script/beacon's chances of getting detected are minimized. Additionally, provides for a more intuitive and better way of interacting with a client machine.
4. `shell <IP> <port>` - Sends a command to the client to open up a reverse shell to the IP address specified on the port passed in, that way this script/beacon's chances of getting detected are minimized. Additionally, provides for a more intuitive and better way of interacting with a client machine.
5. `shell` - Sends a command to the client to open up a reverse shell, that way this script/beacon's chances of getting detected are minimized. Additionally, provides for a more intuitive and better way of interacting with a client machine.
6. `CMD:<command>` - Sends the written command to the client that gets executed.
7. `exit` - Terminates the server
8. `help` - Prints out the available commands and what they do
