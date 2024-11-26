#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import re
from pathlib import Path
import typer
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Environment variables with defaults
USERNAME = os.getenv('USERNAME', 'baptiste')
SSH_CONFIG_PATH = os.path.expanduser("~/.ssh/config")
TPU_MANAGER_PATH = os.path.expanduser('~/Git/tpu-manager')
DATABASE_PATH = os.path.join(TPU_MANAGER_PATH, "database.json")
ZONES = [
        "us-central1-a",
        "us-east5-a",
        "us-east5-b",
        "us-east5-c",
        "us-south1-a",
        "us-west1-c",
        "us-west4-a",
        "us-west4-b"
    ]

class TPU(BaseModel):
    name: str
    zone: str
    ip: str
    
class Disk(BaseModel):
    name: str
    zone: str

class Database(BaseModel):
    tpus: List[TPU]
    disks: List[Disk]



def get_tpu_name(zone: str, number_of_tpu: int):
    return f"baptiste-tpu-{number_of_tpu}-{zone}"

def update_ssh_config(new_ip):
    """Update ~/.ssh/config with new IP address"""
    if not os.path.exists(SSH_CONFIG_PATH):
        print(f"SSH config file not found at {SSH_CONFIG_PATH}")
        return

    try:
        with open(SSH_CONFIG_PATH, 'r') as f:
            lines = f.readlines()

        # Create backup
        backup_path = SSH_CONFIG_PATH + '.bak'
        with open(backup_path, 'w') as f:
            f.writelines(lines)

        # Find and update the tpu entry
        in_tpu_section = False
        for i, line in enumerate(lines):
            if line.strip() == 'Host tpu':
                in_tpu_section = True
            elif line.strip().startswith('Host ') and in_tpu_section:
                in_tpu_section = False
            elif in_tpu_section and line.strip().startswith('Hostname '):
                lines[i] = f'    Hostname {new_ip}\n'
                break

        with open(SSH_CONFIG_PATH, 'w') as f:
            f.writelines(lines)
        
        print(f"Updated SSH config with new IP: {new_ip}")

    except Exception as e:
        print(f"Error updating SSH config: {e}")
        print(f"Original error: {str(e)}")
        sys.exit(1)

app = typer.Typer()

@app.command()
def refresh():
    """Refresh database with current TPUs and disks"""
    print("Refreshing database...")
    
    tpus = []
    disks = []
    
    # Define zones to check
    zones = [
        "us-central1-a",
        "us-east5-a", 
        "us-east5-b",
        "us-east5-c",
        "us-south1-a",
        "us-west1-c",
        "us-west4-a",
        "us-west4-b"
    ]
    
    # Get TPUs
    for zone in zones:
        list_cmd = [
            "gcloud", "compute", "tpus", "tpu-vm", "list",
            "--format=json",
            "--filter=name~baptiste",
            f"--zone={zone}"
        ]
        
        try:
            result = subprocess.run(list_cmd, check=True, capture_output=True, text=True)
            tpu_list = json.loads(result.stdout)
            
            for tpu in tpu_list:
                ip = None
                if 'networkEndpoints' in tpu:
                    for endpoint in tpu['networkEndpoints']:
                        if 'accessConfig' in endpoint and 'externalIp' in endpoint['accessConfig']:
                            ip = endpoint['accessConfig']['externalIp']
                            break
                
                if ip:
                    tpus.append(TPU(
                        name=tpu['name'],
                        zone=zone,
                        ip=ip
                    ))
                    
        except Exception as e:
            print(f"Error getting TPUs in zone {zone}: {e}")
            continue
            
    # Get Disks
    for zone in zones:
        list_cmd = [
            "gcloud", "compute", "disks", "list",
            "--format=json",
            "--filter=name~baptiste",
            f"--zone={zone}"
        ]
        
        try:
            result = subprocess.run(list_cmd, check=True, capture_output=True, text=True)
            disk_list = json.loads(result.stdout)
            
            for disk in disk_list:
                disks.append(Disk(
                    name=disk['name'],
                    zone=zone
                ))
                    
        except Exception as e:
            print(f"Error getting disks in zone {zone}: {e}")
            continue
    
    # Create and save database
    db = Database(tpus=tpus, disks=disks)
    
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with open(DATABASE_PATH, "w") as f:
        f.write(db.model_dump_json(indent=2))
        
    print(f"Database refreshed and saved to {DATABASE_PATH}")
    return db

def load_database() -> Database:
    """Load database from disk"""
    try:
        with open(DATABASE_PATH) as f:
            return Database.model_validate_json(f.read())
    except FileNotFoundError:
        print("No database found, refreshing...")
        return refresh()
    except Exception as e:
        print(f"Error loading database: {e}")
        return Database(tpus=[], disks=[])
    
@app.command()
def show():
    """Show database"""
    db = load_database()
    print(db.model_dump_json(indent=2))

@app.command()
def list(
):
    """List all TPU VMs with 'baptiste' in name across specific zones"""
    print(f"Listing all TPU VMs with 'baptiste' in name across specific zones\n")
    
    # Define the specific zones to check
    zones = [
        "us-central1-a",
        "us-east5-a",
        "us-east5-b",
        "us-east5-c",
        "us-south1-a",
        "us-west1-c",
        "us-west4-a",
        "us-west4-b"
    ]
    
    for zone in zones:
        # print(f"Checking zone: {zone}")
        
        list_cmd = [
            "gcloud", "compute", "tpus", "tpu-vm", "list", "--format=json", "--filter=name~baptiste", f"--zone={zone}"
        ]
        
        try:
            result = subprocess.run(list_cmd, check=True, capture_output=True, text=True)
            tpus = json.loads(result.stdout)
            
            if not tpus:
                # print("No TPU VMs found in this zone")
                continue
                
            for tpu in tpus:
                print(f"Name: {tpu.get('name', 'N/A')}")
                print(f"State: {tpu.get('state', 'N/A')}")
                print(f"Type: {tpu.get('acceleratorType', 'N/A')}")
                if 'networkEndpoints' in tpu:
                    for endpoint in tpu['networkEndpoints']:
                        if 'accessConfig' in endpoint and 'externalIp' in endpoint['accessConfig']:
                            print(f"IP: {endpoint['accessConfig']['externalIp']}")
                print()
                
        except subprocess.CalledProcessError as e:
            print(f"Error listing TPU VMs in zone {zone}: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON output in zone {zone}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error in zone {zone}: {e}")
            sys.exit(1)

@app.command()
def start(
    tpu_name: str = typer.Option(..., help="Name of the TPU VM"),
    zone: str = typer.Option(..., help="Zone of the TPU VM")
):
    """Start TPU VM and update SSH config with new IP"""
    print(f"Starting TPU VM {tpu_name} in zone {zone}...")
    
    # Start TPU VM and capture output
    start_cmd = [
        "gcloud", "compute", "tpus", "tpu-vm", "start",
        tpu_name,
        f"--zone={zone}",
        "--format=json"
    ]
    
    try:
        result = subprocess.run(start_cmd, check=True, capture_output=True, text=True)
        start_output = json.loads(result.stdout)
        
        # Parse the operation response to get the IP
        if isinstance(start_output, list):
            start_output = start_output[0]
        
        if 'response' in start_output and 'networkEndpoints' in start_output['response']:
            network_endpoints = start_output['response']['networkEndpoints']
            for endpoint in network_endpoints:
                if 'accessConfig' in endpoint and 'externalIp' in endpoint['accessConfig']:
                    external_ip = endpoint['accessConfig']['externalIp']
                    update_ssh_config(external_ip)
                    print(f"TPU VM started successfully. External IP: {external_ip}")
                    break
            else:
                print("Warning: Could not find external IP in start command output")
        else:
            print("Warning: Unexpected response format from start command")
            
    except subprocess.CalledProcessError as e:
        print(f"Error starting TPU VM: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
        
@app.command()
def stop(
    tpu_name: str = typer.Option(..., help="Name of the TPU VM"),
    zone: str = typer.Option(..., help="Zone of the TPU VM")
):
    """Stop TPU VM"""
    print(f"Stopping TPU VM {tpu_name} in zone {zone}...")
    
    stop_cmd = [
        "gcloud", "compute", "tpus", "tpu-vm", "stop",
        tpu_name,
        f"--zone={zone}"
    ]
    
    try:
        subprocess.run(stop_cmd, check=True)
        print("TPU VM stopped successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping TPU VM: {e}")
        sys.exit(1)

@app.command()
def update_ip(
    ip_address: str = typer.Argument(..., help="IP address for manual update"),
):
    """Manually update SSH config with provided IP"""
    # Basic IP address validation
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, ip_address):
        typer.echo("Invalid IP address format")
        raise typer.Exit(1)
    
    update_ssh_config(ip_address)\

@app.command()
def setup_alias():
    """Setup alias for tpu-manager in ~/.zshrc for easy access on local computer"""
    
    tpu_dotfiles_path = os.path.expanduser('~/Git/tpu-manager')
    alias_command = f'alias tpu-manager="{tpu_dotfiles_path}/.venv/bin/python3 {tpu_dotfiles_path}/tpu_manager.py"'
    with open(os.path.expanduser('~/.zshrc'), 'a') as f:
        f.write(alias_command + '\n')
    print(f"Alias set up in ~/.zshrc: tpu-manager")
    
@app.command()
def setup_vm():
    """Setup a TPU VM (from scratch or from existing VM)"""
    subprocess.run(["scp", "tpu_key", "tpu:~/.ssh/tpu_key"])
    subprocess.run(["scp", "tpu_key.pub", "tpu:~/.ssh/tpu_key.pub"])
    subprocess.run(["scp", ".global_gitignore", "tpu:~/.global_gitignore"])
    subprocess.run(["scp", "setup_vm_from_scratch.py", "tpu:~/setup_vm_from_scratch.py"])
    
    # Pass HF_TOKEN through SSH environment
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("HF_TOKEN not found in environment")
        sys.exit(1)
        
    subprocess.run(["ssh", "tpu", f"HF_TOKEN={hf_token}", "python3", "setup_vm_from_scratch.py"])

@app.command()
def backup_download():
    """Backup all folders in .global_gitignore on optimum-tpu to local mac"""
    os.makedirs("backup", exist_ok=True)
    with open(".global_gitignore", "r") as f:
        folders = [folder.strip() for folder in f.read().splitlines() if folder.strip()]
    
    for folder in folders:
        try:
            # Check if remote folder exists before attempting rsync
            check_cmd = ["ssh", "tpu", f"test -d ~/git/optimum-tpu/{folder}"]
            subprocess.run(check_cmd, check=True)
            
            # If folder exists, do the rsync
            subprocess.run(["rsync", "-avz", f"tpu:~/git/optimum-tpu/{folder}", f"./backup/{folder}"], check=True)
            print(f"Successfully backed up {folder}")
        except subprocess.CalledProcessError:
            print(f"Skipping {folder} - folder does not exist on remote machine")
            continue

@app.command()
def backup_upload():
    """Upload all folders in backup/ to optimum-tpu"""
    if not os.path.exists("backup"):
        print("No backup folder found")
        return
        
    # Get list of folders in backup/
    folders = [f for f in os.listdir("backup") if os.path.isdir(os.path.join("backup", f))]
    
    for folder in folders:
        try:
            # Create remote folder if it doesn't exist
            subprocess.run(["ssh", "tpu", f"mkdir -p ~/git/optimum-tpu/{folder}"], check=True)
            
            # Upload folder
            subprocess.run(["rsync", "-avz", f"./backup/{folder}", "tpu:~/git/optimum-tpu/"], check=True)
            print(f"Successfully uploaded {folder}")
        except subprocess.CalledProcessError as e:
            print(f"Error uploading {folder}: {e}")
            continue
        
def get_disk_name(zone: str):
    return f"baptiste-disk-{zone}"

@app.command()
def create_tpu_vm(
        zone: str = typer.Argument(..., help="Zone to create the TPU VM in"),
        number_of_tpu: int = typer.Option(8, help="Number of TPU on the VM"),
        version: str = typer.Option("v2-alpha-tpuv5-lite", help="TPU software version")
):
    """Create a TPU VM"""
    tpu_name = get_tpu_name(zone, number_of_tpu)
    # Compute accelerator type from number of TPUs
    accelerator_type = f"v5litepod-{number_of_tpu}"
    try:
        subprocess.run([
            "gcloud", "compute", "tpus", "tpu-vm", "create", 
            tpu_name,
            f"--zone={zone}",
            f"--version={version}",
            f"--accelerator-type={accelerator_type}"
        ], check=True)
        print(f"Successfully created TPU VM {tpu_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating TPU VM: {e}")
        sys.exit(1)

def _create_disk(zone: str, size: int, disk_type: str):
    """Helper function to create a disk"""
    disk_name = get_disk_name(zone)
    try:
        cmd = [
            "gcloud", "compute", "disks", "create", disk_name,
            "--size", str(size),
            "--zone", zone,
            "--type", disk_type
        ]
        subprocess.run(cmd, check=True)
        print(f"Successfully created disk {disk_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating disk: {e}")
        sys.exit(1)

def _attach_disk(zone: str, number_of_tpu: int, mode: str):
    """Helper function to attach a disk"""
    tpu_name = get_tpu_name(zone, number_of_tpu)
    disk_name = get_disk_name(zone)
    
    try:
        cmd = [
            "gcloud", "alpha", "compute", "tpus", "tpu-vm", "attach-disk",
            tpu_name,
            "--zone", zone,
            "--disk", disk_name,
            "--mode", mode
        ]
        subprocess.run(cmd, check=True)
        print(f"Successfully attached disk {disk_name} to TPU VM {tpu_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error attaching disk: {e}")
        sys.exit(1)

def _setup_disk_mount(zone: str, number_of_tpu: int):
    """Helper function to setup disk mount"""
    tpu_name = get_tpu_name(zone, number_of_tpu)
    
    try:
        # Create mount point directory
        cmd = [
            "gcloud", "compute", "tpus", "tpu-vm", "ssh",
            tpu_name,
            "--worker=all",
            "--command=sudo mkdir -p /mnt/disks/persist/data/baptiste",
            "--zone", zone
        ]
        subprocess.run(cmd, check=True)
        print(f"Successfully created mount point on TPU VM {tpu_name}")

        # Mount the disk
        cmd = [
            "gcloud", "compute", "tpus", "tpu-vm", "ssh",
            tpu_name,
            "--worker=all", 
            "--command=sudo mount -o discard,defaults /dev/sdb /mnt/disks/persist",
            "--zone", zone
        ]
        subprocess.run(cmd, check=True)
        print(f"Successfully mounted disk on TPU VM {tpu_name}")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up disk mount point: {e}")
        sys.exit(1)

@app.command()
def create_and_setup_disk(
    zone: str = typer.Argument(..., help="Zone to create and setup the disk in"),
    number_of_tpu: int = typer.Option(1, help="Number of TPU on the VM"),
    size: int = typer.Option(500, help="Size of disk in GB"),
    disk_type: str = typer.Option("pd-balanced", help="Type of disk (pd-balanced, pd-ssd, pd-standard)"),
    mode: str = typer.Option("read-write", help="Disk mode (read-write or read-only)")
):
    """Create a new persistent disk, attach it to TPU VM and setup mount point"""
    _create_disk(zone, size, disk_type)
    _attach_disk(zone, number_of_tpu, mode)
    _setup_disk_mount(zone, number_of_tpu)

@app.command()
def create_disk(
    zone: str = typer.Argument(..., help="Zone to create the disk in"),
    size: int = typer.Option(500, help="Size of disk in GB"),
    disk_type: str = typer.Option("pd-balanced", help="Type of disk (pd-balanced, pd-ssd, pd-standard)")
):
    """Create a new persistent disk"""
    _create_disk(zone, size, disk_type)

@app.command()
def attach_disk(
    zone: str = typer.Option(..., help="Zone where the disk and TPU VM are located"),
    number_of_tpu: int = typer.Option(1, help="Number of TPU on the VM to attach the disk to"),
    mode: str = typer.Option("read-write", help="Disk mode (read-write or read-only)")
):
    """Attach a persistent disk to a TPU VM instance"""
    _attach_disk(zone, number_of_tpu, mode)

@app.command()
def setup_blank_disk_on_tpu(
    zone: str = typer.Option(..., help="Zone where the TPU VM is located"),
    number_of_tpu: int = typer.Option(1, help="Number of TPU on the VM to setup disk on")
):
    """Setup persistent disk mount point on TPU VM"""
    _setup_disk_mount(zone, number_of_tpu)
    
@app.command()
def list_zones():
    """List all available zones"""
    for zone in ZONES:
        print(zone)

if __name__ == "__main__":
    app()