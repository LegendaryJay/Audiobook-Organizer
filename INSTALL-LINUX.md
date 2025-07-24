# Audiobook Organizer - Linux Installation Guide

## Prerequisites

1. **Python 3.8+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv python3-dev python3-setuptools
   
   # For Ubuntu 22.04+ (Python 3.10+) - Try these if distutils missing
   sudo apt install python3-distutils python3-setuptools-scm || echo "distutils not available, using alternatives"
   # Alternative if distutils unavailable:
   sudo apt install build-essential python3-wheel
   
   # CentOS/RHEL/Fedora
   sudo dnf install python3 python3-pip python3-venv python3-devel python3-setuptools
   # or for older versions: sudo yum install python3 python3-pip python3-venv python3-devel
   
   # Arch Linux
   sudo pacman -S python python-pip python-setuptools
   ```

2. **Node.js 18+ (for frontend)**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   
   # CentOS/RHEL/Fedora
   curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
   sudo dnf install nodejs npm
   
   # Arch Linux
   sudo pacman -S nodejs npm
   ```

3. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt install git
   
   # CentOS/RHEL/Fedora
   sudo dnf install git
   
   # Arch Linux
   sudo pacman -S git
   ```

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/LegendaryJay/Audiobook-Organizer.git
cd Audiobook-Organizer
```

### 2. Set Up Python Backend

#### Create Virtual Environment
```bash
cd backend

# Create virtual environment (using 'venv' without dot)
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Verify activation (should show the venv path)
which python
which pip
```

#### Install Python Dependencies
```bash
# Make sure virtual environment is activated (you should see (venv) in your prompt)
source venv/bin/activate

# Upgrade pip first to avoid issues
pip install --upgrade pip setuptools wheel

# For Python 3.12+, install compatible versions first
pip install numpy>=1.26.0 pandas>=2.1.0

# Install remaining dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables
Create a `.env` file in the backend directory:
```bash
nano .env
```

Add your paths (adjust to your Linux paths):
```bash
# Media directories - CHANGE THESE TO YOUR PATHS
MEDIA_ROOT=/home/username/audiobooks/media
DEST_ROOT=/home/username/audiobooks/sorted

# Optional: Server settings
HOST=0.0.0.0
PORT=4000
DEBUG=True
```

#### Create Required Directories
```bash
# Create metadata and covers directories
mkdir -p metadata covers

# Create your media directories (adjust paths as needed)
mkdir -p /home/username/audiobooks/media
mkdir -p /home/username/audiobooks/sorted
```

### 3. Set Up Frontend

#### Install Frontend Dependencies
```bash
cd ../lunar-light
npm install
```

#### Build Frontend
```bash
npm run build
```

### 4. Configure System Service (Optional)

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/audiobook-organizer.service
```

Add the following content (adjust paths):
```ini
[Unit]
Description=Audiobook Organizer Backend
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/Audiobook-Organizer/backend
Environment=PATH=/home/username/Audiobook-Organizer/backend/venv/bin
ExecStart=/home/username/Audiobook-Organizer/backend/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable audiobook-organizer
sudo systemctl start audiobook-organizer
```

## Running the Application

### Manual Start (Development)

#### Start Backend
```bash
cd backend
source venv/bin/activate
python app.py
```

#### Start Frontend (Development Mode)
In a new terminal:
```bash
cd lunar-light
npm run dev
```

### Production Mode

#### Start Backend Only (serves built frontend)
```bash
cd backend
source venv/bin/activate
python app.py
```

The backend will serve the built frontend at `http://localhost:4000`

## Configuration

### Environment Variables

The application uses these environment variables (set in `backend/.env`):

- `MEDIA_ROOT`: Path to your audiobook files (default: `/home/username/audiobooks/media`)
- `DEST_ROOT`: Path where organized audiobooks will be moved (default: `/home/username/audiobooks/sorted`)
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `4000`)
- `DEBUG`: Enable debug mode (default: `True`)

### File Permissions

Ensure the application has read/write access to your directories:
```bash
# Make sure your user owns the directories
sudo chown -R $USER:$USER /home/username/audiobooks/

# Set appropriate permissions
chmod -R 755 /home/username/audiobooks/
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER /path/to/audiobooks/
   
   # Fix permissions
   chmod -R 755 /path/to/audiobooks/
   ```

2. **Python Module Not Found**
   ```bash
   # Check if you're in the right directory
   pwd  # Should show /path/to/Audiobook-Organizer/backend
   ls   # Should show app.py, requirements.txt, venv/
   
   # Make sure virtual environment exists and is activated
   source venv/bin/activate
   
   # You should see (venv) in your prompt. If not, recreate:
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   
   # Upgrade pip and setuptools first
   pip install --upgrade pip setuptools wheel
   
   # Reinstall requirements
   pip install -r requirements.txt
   ```

3. **Distutils Error (Python 3.10+)**
   ```bash
   # This error occurs when NumPy tries to build from source on Python 3.12+
   
   # Option 1: Install system packages first (easiest fix)
   sudo apt install python3-numpy python3-pandas python3-flask python3-flask-cors 
   sudo apt install python3-mutagen python3-watchdog python3-pil python3-requests
   
   # Then use system-site-packages venv:
   python3 -m venv --system-site-packages venv
   source venv/bin/activate
   
   # Option 2: Install newer compatible versions
   pip install --upgrade pip setuptools wheel
   pip install numpy>=1.26.0 pandas>=2.1.0  # Python 3.12 compatible versions
   pip install flask flask-cors mutagen watchdog pillow requests
   
   # Option 3: Force build with system tools
   sudo apt install python3-dev build-essential
   pip install --no-build-isolation numpy pandas
   pip install flask flask-cors mutagen watchdog pillow requests
   
   # Option 4: Use conda instead of pip
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh -b
   ~/miniconda3/bin/conda create -n audiobook python=3.11
   ~/miniconda3/bin/conda activate audiobook
   ~/miniconda3/bin/conda install numpy pandas flask requests pillow
   pip install flask-cors mutagen watchdog
   ```

4. **Virtual Environment Path Issues**
   ```bash
   # If you get "no such file or directory" for venv paths:
   cd backend
   ls -la  # Check if 'venv' directory exists
   
   # If missing, recreate virtual environment:
   rm -rf venv .venv  # Remove any existing venv folders
   python3 -m venv venv
   source venv/bin/activate
   
   # Verify paths:
   echo $VIRTUAL_ENV  # Should show /full/path/to/backend/venv
   which python       # Should show /full/path/to/backend/venv/bin/python
   which pip          # Should show /full/path/to/backend/venv/bin/pip
   ```

4. **Port Already in Use**
   ```bash
   # Check what's using port 4000
   sudo netstat -tulpn | grep :4000
   
   # Kill the process or change PORT in .env file
   ```

5. **Frontend Build Fails**
   ```bash
   # Clear node modules and reinstall
   cd lunar-light
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

6. **Alternative Installation (If Virtual Environment Fails)**
   ```bash
   # Method 1: System packages (Ubuntu/Debian)
   sudo apt install python3-flask python3-flask-cors python3-mutagen 
   sudo apt install python3-watchdog python3-pil python3-requests 
   sudo apt install python3-pandas python3-numpy
   
   # Run directly without virtual environment
   cd backend
   python3 app.py
   
   # Method 2: User installation (no sudo needed)
   cd backend
   python3 -m pip install --user -r requirements.txt
   python3 app.py
   
   # Method 3: Force installation without build isolation
   python3 -m venv venv
   source venv/bin/activate
   pip install --no-build-isolation --upgrade pip setuptools wheel
   pip install --no-build-isolation -r requirements.txt
   ```

6. **If Nothing Works - Docker Alternative**
   ```bash
   # Create a simple Dockerfile in the backend directory
   cat > Dockerfile << 'EOF'
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 4000
   CMD ["python", "app.py"]
   EOF
   
   # Build and run with Docker
   docker build -t audiobook-organizer .
   docker run -p 4000:4000 -v /path/to/your/audiobooks:/media audiobook-organizer
   ```

### Logs

Check application logs:
```bash
# If using systemd service
sudo journalctl -u audiobook-organizer -f

# If running manually, logs appear in terminal
```

## File Structure on Linux

```
/home/username/Audiobook-Organizer/
├── backend/
│   ├── venv/                 # Python virtual environment
│   ├── metadata/             # Audiobook metadata files
│   ├── covers/               # Cover images
│   ├── .env                  # Environment configuration
│   ├── app.py                # Main backend application
│   └── requirements.txt      # Python dependencies
├── lunar-light/
│   ├── dist/                 # Built frontend files
│   ├── src/                  # Frontend source code
│   └── package.json          # Node.js dependencies
└── README.md

/home/username/audiobooks/      # Your audiobook directories
├── media/                      # Source audiobook files
└── sorted/                     # Organized audiobook files
```

## Accessing the Application

Once running, access the web interface at:
- **Local**: `http://localhost:4000`
- **Network**: `http://your-server-ip:4000`

## Updates

To update the application:
```bash
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
cd ../lunar-light
npm install
npm run build
```

Then restart the service:
```bash
sudo systemctl restart audiobook-organizer
```
