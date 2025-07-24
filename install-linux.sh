#!/bin/bash

# Audiobook Organizer - Linux Auto-Installer
# This script automatically installs and configures the Audiobook Organizer on Linux

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
INSTALL_DIR="$HOME/Audiobook-Organizer"
MEDIA_DIR="$HOME/audiobooks/media"
SORTED_DIR="$HOME/audiobooks/sorted"
REPO_URL="https://github.com/LegendaryJay/Audiobook-Organizer.git"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        print_error "Cannot detect Linux distribution"
        exit 1
    fi
    print_status "Detected distribution: $DISTRO $VERSION"
}

# Function to install system packages
install_system_packages() {
    print_status "Installing system packages..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt update
            # Try to install distutils, fallback if not available
            sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools build-essential python3-wheel || true
            sudo apt install -y python3-distutils python3-setuptools-scm 2>/dev/null || print_warning "distutils not available, using alternatives"
            
            # Install system Python packages for backup
            sudo apt install -y python3-numpy python3-pandas python3-flask python3-flask-cors python3-mutagen python3-watchdog python3-pil python3-requests 2>/dev/null || print_warning "Some system Python packages not available"
            
            # Install Node.js
            if ! command -v node &> /dev/null; then
                print_status "Installing Node.js..."
                curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                sudo apt-get install -y nodejs
            fi
            
            # Install Git
            sudo apt install -y git
            ;;
            
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-venv python3-devel python3-setuptools build-essential
                sudo dnf install -y nodejs npm git
            else
                sudo yum install -y python3 python3-pip python3-venv python3-devel python3-setuptools
                sudo yum install -y nodejs npm git
            fi
            ;;
            
        arch|manjaro)
            sudo pacman -S --noconfirm python python-pip python-setuptools base-devel nodejs npm git
            ;;
            
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_status "Please install manually: python3, python3-pip, python3-venv, nodejs, npm, git"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
    
    print_success "System packages installed"
}

# Function to get user configuration
get_user_config() {
    echo
    print_status "Configuration Setup"
    echo "Please provide the following paths (or press Enter for defaults):"
    
    read -p "Installation directory [$INSTALL_DIR]: " user_install_dir
    INSTALL_DIR=${user_install_dir:-$INSTALL_DIR}
    
    read -p "Media directory (where your audiobooks are) [$MEDIA_DIR]: " user_media_dir
    MEDIA_DIR=${user_media_dir:-$MEDIA_DIR}
    
    read -p "Sorted directory (where organized audiobooks will go) [$SORTED_DIR]: " user_sorted_dir
    SORTED_DIR=${user_sorted_dir:-$SORTED_DIR}
    
    echo
    print_status "Configuration:"
    echo "  Installation: $INSTALL_DIR"
    echo "  Media: $MEDIA_DIR" 
    echo "  Sorted: $SORTED_DIR"
    echo
}

# Function to clone repository
clone_repository() {
    print_status "Cloning repository..."
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists"
        read -p "Remove and re-clone? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            print_status "Using existing directory"
            cd "$INSTALL_DIR"
            git pull origin main || print_warning "Could not update repository"
            return
        fi
    fi
    
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    print_success "Repository cloned"
}

# Function to set up Python backend
setup_backend() {
    print_status "Setting up Python backend..."
    cd "$INSTALL_DIR/backend"
    
    # Remove any existing virtual environment
    rm -rf venv .venv
    
    # Try different approaches for virtual environment
    if python3 -m venv --system-site-packages venv 2>/dev/null; then
        print_success "Created virtual environment with system packages"
        VENV_TYPE="system-site"
    elif python3 -m venv venv 2>/dev/null; then
        print_success "Created isolated virtual environment"
        VENV_TYPE="isolated"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install packages with multiple fallback strategies
    print_status "Installing Python packages..."
    
    if [ "$VENV_TYPE" = "system-site" ]; then
        # With system site packages, try installing what's missing
        pip install flask flask-cors mutagen watchdog pillow requests || print_warning "Some packages may already be installed system-wide"
    else
        # Try installing compatible versions first
        if pip install "numpy>=1.26.0" "pandas>=2.1.0" 2>/dev/null; then
            print_success "Installed NumPy and Pandas (Python 3.12 compatible)"
        else
            print_warning "Could not install latest NumPy/Pandas, trying alternatives..."
            pip install --no-build-isolation numpy pandas || pip install numpy==1.24.4 pandas==2.0.3
        fi
        
        # Install remaining packages
        pip install flask flask-cors mutagen watchdog pillow requests gunicorn
    fi
    
    # Create configuration file
    print_status "Creating configuration file..."
    cat > .env << EOF
# Media directories
MEDIA_ROOT=$MEDIA_DIR
DEST_ROOT=$SORTED_DIR

# Server settings
HOST=0.0.0.0
PORT=4000
DEBUG=True
EOF
    
    # Create required directories
    mkdir -p metadata covers
    mkdir -p "$MEDIA_DIR" "$SORTED_DIR"
    
    print_success "Backend setup complete"
}

# Function to set up frontend
setup_frontend() {
    print_status "Setting up frontend..."
    cd "$INSTALL_DIR/lunar-light"
    
    # Install Node.js dependencies
    npm install
    
    # Build frontend
    npm run build
    
    print_success "Frontend setup complete"
}

# Function to create systemd service
create_service() {
    read -p "Create systemd service for auto-start? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    print_status "Creating systemd service..."
    
    sudo tee /etc/systemd/system/audiobook-organizer.service > /dev/null << EOF
[Unit]
Description=Audiobook Organizer Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/backend/venv/bin
ExecStart=$INSTALL_DIR/backend/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable audiobook-organizer
    
    print_success "Systemd service created and enabled"
    
    read -p "Start the service now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start audiobook-organizer
        print_success "Service started"
    fi
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    cd "$INSTALL_DIR/backend"
    source venv/bin/activate
    
    # Test Python imports
    if python3 -c "import flask, mutagen, watchdog, PIL, requests, pandas, numpy; print('All imports successful')" 2>/dev/null; then
        print_success "Python dependencies test passed"
    else
        print_error "Python dependencies test failed"
        return 1
    fi
    
    # Check if frontend was built
    if [ -d "$INSTALL_DIR/lunar-light/dist" ]; then
        print_success "Frontend build test passed"
    else
        print_error "Frontend build test failed"
        return 1
    fi
    
    print_success "Installation test completed successfully"
}

# Function to display completion information
show_completion_info() {
    echo
    print_success "Installation completed successfully!"
    echo
    echo "Configuration:"
    echo "  Installation Directory: $INSTALL_DIR"
    echo "  Media Directory: $MEDIA_DIR"
    echo "  Sorted Directory: $SORTED_DIR"
    echo "  Configuration File: $INSTALL_DIR/backend/.env"
    echo
    echo "To start the application manually:"
    echo "  cd $INSTALL_DIR/backend"
    echo "  source venv/bin/activate"
    echo "  python app.py"
    echo
    echo "The web interface will be available at:"
    echo "  http://localhost:4000"
    echo "  http://$(hostname -I | awk '{print $1}'):4000"
    echo
    echo "To check service status (if installed):"
    echo "  sudo systemctl status audiobook-organizer"
    echo
    echo "To view logs:"
    echo "  sudo journalctl -u audiobook-organizer -f"
    echo
    echo "Put your audiobook files in: $MEDIA_DIR"
    echo "Organized audiobooks will go to: $SORTED_DIR"
    echo
}

# Function to handle errors
handle_error() {
    print_error "Installation failed at step: $1"
    echo
    echo "You can try:"
    echo "1. Run the script again"
    echo "2. Check the manual installation guide: INSTALL-LINUX.md"
    echo "3. Use the troubleshooting section in the guide"
    echo
    exit 1
}

# Main installation function
main() {
    echo "======================================"
    echo "  Audiobook Organizer Auto-Installer"
    echo "======================================"
    echo
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this script as root"
        exit 1
    fi
    
    # Trap errors
    trap 'handle_error "Unknown error"' ERR
    
    print_status "Starting installation..."
    
    detect_distro || handle_error "Distribution detection"
    get_user_config || handle_error "User configuration"
    install_system_packages || handle_error "System package installation"
    clone_repository || handle_error "Repository cloning"
    setup_backend || handle_error "Backend setup"
    setup_frontend || handle_error "Frontend setup"
    create_service || handle_error "Service creation"
    test_installation || handle_error "Installation testing"
    
    show_completion_info
    
    print_success "All done! 🎉"
}

# Run main function
main "$@"
