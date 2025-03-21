#!/bin/bash

# Array of target machines with credentials for initial setup
# Format: "username:password@ip_address"
MACHINES=(
    "CAgrupnin:Guard!an_7th@10.10.1.2"
    "CAgrupnin:Guard!an_7th@10.10.1.3"
    "LCoramar:@rchitect_@rcane@10.10.2.2"
    "LCoramar:@rchitect_@rcane@10.10.2.3"
    "LSeelie:H3ralds_Tom3@10.10.3.2"
    "LSeelie:H3ralds_Tom3@10.10.3.3"
    "VChloras:B3tray3r_Gods@10.10.4.2"
    "VChloras:B3tray3r_Gods@10.10.4.3"
)

# Set up timing log file
TIMING_LOG="deployment_timing.log"
echo "Deployment Timing Log - $(date)" > $TIMING_LOG

# Function to log timing
log_timing() {
    local section=$1
    local start_time=$2
    local end_time=$3
    local duration=$((end_time - start_time))
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $section completed in ${duration} seconds" >> $TIMING_LOG
    echo "Completed $section in ${duration} seconds"
}

# Repository URL 
REPO_URL="https://github.com/arogoff/cdt-comp2.git"

# Script to run from the repository
SCRIPT_PATH="run.sh"

# SSH key path
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_KEY_PUB="$HOME/.ssh/id_ed25519.pub"

# Function to set up SSH keys for a single machine
setup_ssh_key_for_machine() {
    local machine_start_time=$(date +%s)
    # Parse the machine string
    local machine=$1
    local username=$(echo $machine | grep -o '^[^:]*')
    local ip=$(echo $machine | grep -o '[^@]*$')
    local password=$(echo $machine | sed -E 's/^[^:]*://;s/@[^@]*$//')
    local user_host="$username@$ip"
    
    echo "Copying SSH key to $user_host..."
    
    # Create a temporary expect script for this machine
    local expect_script=$(mktemp)
    
    cat > "$expect_script" << EOL
#!/usr/bin/expect -f
spawn ssh-copy-id -i $SSH_KEY_PUB -o StrictHostKeyChecking=no $user_host
expect "password:"
send "$password\r"
expect eof

spawn ssh -o StrictHostKeyChecking=no $user_host
expect "password:"
send "$password\r"
expect "\\\$"
# Set up passwordless sudo first
send "echo '$password' | sudo -S bash -c 'echo \"$username ALL=(ALL) NOPASSWD: ALL\" > /etc/sudoers.d/$username && chmod 440 /etc/sudoers.d/$username'\r"
expect "\\\$"
# Now use sudo for package management
send "sudo apt-get update -y\r"
expect "\\\$"
send "sudo apt-get install -y git python3 python3-pip\r"
expect "\\\$"
send "exit\r"
expect eof
EOL
    
    chmod +x "$expect_script"
    
    # Run the expect script
    "$expect_script" > "setup_log_${ip}.txt" 2>&1
    
    # Clean up
    rm "$expect_script"
    
    local machine_end_time=$(date +%s)
    echo "SSH key setup completed for $user_host in $((machine_end_time - machine_start_time)) seconds" >> $TIMING_LOG
    echo "SSH key setup completed for $user_host in $((machine_end_time - machine_start_time)) seconds"
}

# Function to set up SSH keys in parallel
setup_ssh_keys_parallel() {
    local ssh_key_start_time=$(date +%s)
    
    # Generate SSH key if it doesn't exist - USING ED25519 FOR FASTER GENERATION
    if [ ! -f "$SSH_KEY" ]; then
        local key_gen_start=$(date +%s)
        echo "Generating new SSH key pair using Ed25519 (faster)..."
        ssh-keygen -t ed25519 -f "$SSH_KEY" -N ""
        local key_gen_end=$(date +%s)
        log_timing "SSH key generation" $key_gen_start $key_gen_end
    else
        echo "SSH key already exists at $SSH_KEY"
    fi

    # Copy SSH public key to all machines in parallel
    echo "Copying SSH public key to all target machines in parallel..."
    
    local pids=()
    for machine in "${MACHINES[@]}"; do
        setup_ssh_key_for_machine "$machine" &
        pids+=($!)
    done
    
    # Wait for all parallel processes to complete
    echo "Waiting for all SSH key setups to complete..."
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    local ssh_key_end_time=$(date +%s)
    log_timing "SSH key setup (total)" $ssh_key_start_time $ssh_key_end_time
}

# Function to run the setup on each machine using SSH keys
run_deployment() {
    local deploy_start_time=$(date +%s)
    
    echo "Starting deployment on all machines..."
    
    local pids=()
    local machine_start_times=()
    local machine_ips=()
    
    for machine in "${MACHINES[@]}"; do
        # Parse the machine string
        local username=$(echo $machine | cut -d':' -f1)
        local ip=$(echo $machine | cut -d'@' -f2)
        local user_host="$username@$ip"
        
        echo "Starting deployment for $user_host..."
        local machine_start=$(date +%s)
        machine_start_times+=($machine_start)
        machine_ips+=($ip)
        
        # Use SSH with key-based authentication
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$user_host" << EOF > "log_${ip}.txt" 2>&1 &
            echo "[$ip] Updating and installing packages..."
            start_time=\$(date +%s)
            
            # Ensure packages are installed
            sudo apt-get update -y
            pkg_update_time=\$(date +%s)
            
            sudo apt-get install -y git python3 python3-pip
            pkg_install_time=\$(date +%s)
            
            echo "[$ip] Cloning repository..."
            if [ ! -d "cdt-comp2" ]; then
                git clone "$REPO_URL" -b main
            else
                cd cdt-comp2 && git pull && cd ..
            fi
            git_clone_time=\$(date +%s)
            
            echo "[$ip] Running script with sudo..."
            cd cdt-comp2
            chmod +x "$SCRIPT_PATH"
            sudo ./"$SCRIPT_PATH"
            script_run_time=\$(date +%s)
            
            echo "[$ip] Setup completed"
EOF
        
        pids+=($!)
        echo "Deployment initiated for $user_host (check log_${ip}.txt for progress)"
    done
    
    echo "All deployment processes have been initiated in parallel!"
    echo "To monitor progress, check the log files: log_*.txt"
    
    # Wait for all background processes to complete
    echo "Waiting for all machines to complete setup..."
    for i in "${!pids[@]}"; do
        wait ${pids[$i]}
        local machine_end=$(date +%s)
        local machine_duration=$((machine_end - machine_start_times[$i]))
        echo "Deployment for ${machine_ips[$i]} completed in ${machine_duration} seconds" >> $TIMING_LOG
    done
    
    local deploy_end_time=$(date +%s)
    log_timing "Deployment (total)" $deploy_start_time $deploy_end_time
    
    echo "All machines have completed their setup processes!"
}

# Main script
main_start_time=$(date +%s)
echo "Starting automated SSH setup and deployment process..."

# Check if expect is installed (needed for initial setup only)
if ! command -v expect &> /dev/null; then
    local expect_install_start=$(date +%s)
    echo "Installing expect for initial setup..."
    sudo apt-get update -y
    sudo apt-get install -y expect
    local expect_install_end=$(date +%s)
    log_timing "Expect installation" $expect_install_start $expect_install_end
fi

# Setup SSH keys and passwordless sudo in parallel
setup_ssh_keys_parallel

# Run deployment using SSH keys in parallel
run_deployment

main_end_time=$(date +%s)
log_timing "ENTIRE PROCESS" $main_start_time $main_end_time

echo "Full automation process completed!"
echo "Timing summary saved to $TIMING_LOG"

# Display timing summary
echo "========== TIMING SUMMARY =========="
cat $TIMING_LOG
echo "==================================="
