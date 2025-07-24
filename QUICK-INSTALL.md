# Quick Linux Installation

## One-Command Installation

Run this single command to automatically install everything:

```bash
curl -fsSL https://raw.githubusercontent.com/LegendaryJay/Audiobook-Organizer/main/install-linux.sh | bash
```

Or download and run manually:

```bash
wget https://raw.githubusercontent.com/LegendaryJay/Audiobook-Organizer/main/install-linux.sh
chmod +x install-linux.sh
./install-linux.sh
```

## What the Script Does

The `install-linux.sh` script automatically:

1. **Detects your Linux distribution** (Ubuntu/Debian, CentOS/RHEL/Fedora, Arch)
2. **Installs all prerequisites** (Python 3, Node.js, Git, build tools)
3. **Handles distutils issues** automatically with multiple fallback strategies
4. **Clones the repository** to `~/Audiobook-Organizer`
5. **Sets up Python virtual environment** with compatible packages
6. **Installs and builds the frontend**
7. **Creates configuration files** with your custom paths
8. **Optionally creates systemd service** for auto-start
9. **Tests the installation** to ensure everything works
10. **Provides usage instructions**

## Interactive Configuration

The script will ask you for:

- **Installation directory** (default: `~/Audiobook-Organizer`)
- **Media directory** (where your audiobooks are, default: `~/audiobooks/media`)
- **Sorted directory** (where organized audiobooks go, default: `~/audiobooks/sorted`)
- **Whether to create systemd service** for auto-start

## Supported Distributions

- ✅ **Ubuntu/Debian** (18.04+, including Ubuntu 22.04/24.04)
- ✅ **CentOS/RHEL/Fedora** (CentOS 7+, RHEL 8+, Fedora 35+)
- ✅ **Arch Linux/Manjaro**
- ⚠️ **Other distributions** (manual package installation required)

## Error Handling

The script includes:

- **Automatic distutils fixes** for Python 3.10+/3.12+
- **Multiple package installation strategies** (pip, system packages, conda)
- **Fallback options** if virtual environment fails
- **Comprehensive error messages** with troubleshooting steps
- **Safe execution** (exits on errors, doesn't run as root)

## Post-Installation

After successful installation:

1. **Access the web interface**: `http://localhost:4000`
2. **Put audiobooks in**: The media directory you specified
3. **Start/stop service**: `sudo systemctl start/stop audiobook-organizer`
4. **View logs**: `sudo journalctl -u audiobook-organizer -f`

## Manual Installation

If the auto-installer fails, see the detailed [INSTALL-LINUX.md](INSTALL-LINUX.md) guide.

## Troubleshooting

If you encounter issues:

1. **Re-run the script** - it handles existing installations gracefully
2. **Check the logs** - script provides detailed error messages
3. **Try manual installation** - use INSTALL-LINUX.md as backup
4. **Open an issue** - with the error output for help

## What's Different from Manual Installation

The script handles all the tricky parts automatically:

- **Python 3.12 compatibility** - installs compatible NumPy/Pandas versions
- **Distutils missing** - tries multiple approaches automatically  
- **Package conflicts** - uses system packages as fallback
- **Virtual environment issues** - creates with `--system-site-packages` if needed
- **Permission problems** - sets up directories with correct ownership
- **Service configuration** - creates proper systemd service file

Just run the script and enjoy your audiobook organizer! 🎧📚
