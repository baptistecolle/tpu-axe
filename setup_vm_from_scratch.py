import subprocess
import os
import sys

GIT_USER_NAME = "Baptiste"
GIT_USER_EMAIL = "collebaptiste@gmail.com"

def install_uv():
   if os.path.exists(os.path.expanduser("~/.local/bin/uv")):
       print("uv already installed, skipping...")
       return
   print("Installing uv...")
   try:
       subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True, check=True)
   except subprocess.CalledProcessError as e:
       print(f"Error installing uv: {e}")
       sys.exit(1)
   os.environ["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"
   print("uv installed")

def setup_git():
    print("Setting up git...")
    try:
        subprocess.run(f"git config --global user.name '{GIT_USER_NAME}'", shell=True, check=True)
        subprocess.run(f"git config --global user.email '{GIT_USER_EMAIL}'", shell=True, check=True)
        subprocess.run("git config --global credential.helper store", shell=True, check=True)
        subprocess.run("git config --global core.excludesfile ~/.global_gitignore", shell=True, check=True)
        subprocess.run("mkdir -p ~/git", shell=True, check=True)
        print("git setup")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up git: {e}")
        sys.exit(1)
        
        
def setup_tpu_key():
    print("Setting up TPU SSH key...")
    try:
        subprocess.run("eval $(ssh-agent -s) && ssh-add ~/.ssh/tpu_key", shell=True, check=True)
        print("TPU SSH key setup complete")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up TPU SSH key: {e}")
        sys.exit(1)
    
def setup_optimum_tpu():
   print("Setting up optimum-tpu...")
   git_path = os.path.expanduser("~/git/optimum-tpu")
   if os.path.exists(git_path):
       print("optimum-tpu already cloned, skipping...")
   else:
       print("Cloning optimum-tpu...")
       try:
           subprocess.run("git clone https://github.com/huggingface/optimum-tpu.git ~/git/optimum-tpu", shell=True, check=True)
           print("optimum-tpu cloned")
       except subprocess.CalledProcessError as e:
           print(f"Error cloning optimum-tpu: {e}")
           sys.exit(1)
   print("optimum-tpu setup")
  
# NOT IN USED AS ALAVARO DOES NOT USE UV AND THE PROJECT IS NOT COMPATIBLE WITH IT
# def setup_uv_venv():
    
#     git_path = os.path.expanduser("~/git/optimum-tpu")
    
#     venv_path = os.path.join(git_path, ".venv")
#     if os.path.exists(venv_path):
#        print("virtual environment already created, skipping...")
#     else:
#        print("Creating virtual environment...")
#        uv_path = os.path.expanduser("~/.local/bin/uv")
#        try:
#            subprocess.run(f"{uv_path} venv", shell=True, check=True, cwd=git_path)
#         #    subprocess.run(f"{uv_path} pip install -e .", shell=True, check=True, cwd=git_path)
#            print("virtual environment created")
#        except subprocess.CalledProcessError as e:
#            print(f"Error creating virtual environment: {e}")
#            sys.exit(1)
    
#     print("Setting up virtual environment...")
#     cwd = os.path.expanduser("~/git/optimum-tpu")
#     uv_path = os.path.expanduser("~/.local/bin/uv")

#     subprocess.run(f"{uv_path} pip install 'torch==2.4.0' 'torchvision==0.19.0' --index-url https://download.pytorch.org/whl/cpu", shell=True, check=True, cwd=cwd)
#     subprocess.run(f"{uv_path} pip install 'torch_xla[tpu]~=2.4.0' -f https://storage.googleapis.com/libtpu-releases/index.html --prerelease=allow", shell=True, check=True, cwd=cwd)
#     subprocess.run(f"{uv_path} pip install transformers[sentencepiece] accelerate", shell=True, check=True, cwd=cwd)
#     subprocess.run(f"{uv_path} pip install -e .", shell=True, check=True, cwd=cwd)
#     print("Virtual environment setup")

def setup_bashrc():
    print("Setting up bashrc...")
    HF_TOKEN = os.getenv("HF_TOKEN")
    if HF_TOKEN:
        subprocess.run(f"echo 'export HF_TOKEN={HF_TOKEN}' >> ~/.bashrc", shell=True, check=True)
        print("HF_TOKEN set in bashrc")
    else:
        print("HF_TOKEN not set, skipping...")
    print("bashrc setup")
    
def setup_venv():
    git_path = os.path.expanduser("~/git/optimum-tpu")
    subprocess.run("python -m venv .venv", shell=True, check=True, cwd=git_path)
    
    # TODO MAYBE RUN SOME MAKEFILE CMDS TO INSTALL THE REST?
    subprocess.run("make test_installs", shell=True, check=True, cwd=git_path)
    
def setup_ubuntu_deps():
    print("Setting up ubuntu dependencies...")
    subprocess.run("sudo apt-get update && sudo apt-get install -y git python3-venv", shell=True, check=True)
    print("ubuntu dependencies setup")
   
def setup_docker():
    print("Setting up docker...")
    # Add user to docker group
    try:
        subprocess.run("sudo groupadd docker", shell=True, check=True)
    except subprocess.CalledProcessError:
        # Group already exists, continue
        pass
        
    subprocess.run("sudo usermod -aG docker $USER", shell=True, check=True)
    subprocess.run("newgrp docker", shell=True, check=True)
    
    # Set permissions for docker socket
    subprocess.run("sudo chown root:docker /var/run/docker.sock", shell=True, check=True)
    subprocess.run("sudo chmod 666 /var/run/docker.sock", shell=True, check=True)
    
    print("Docker setup complete")

def setup_vm_from_scratch():
    # install_uv()
    # setup_git()
    # setup_tpu_key()
    # setup_optimum_tpu()
    # setup_ubuntu_deps()
    # # setup_venv() 
    # setup_bashrc()
    setup_docker()
    
    
        
if __name__ == "__main__":
    setup_vm_from_scratch()