# Development Environment Setup

## Setting Up PowerShell 7 for PyCharm

### Installing PowerShell 7

1. **Download PowerShell 7**:
   - Visit the official PowerShell GitHub releases page: https://github.com/PowerShell/PowerShell/releases
   - Download the latest stable PowerShell 7.x MSI installer for Windows (e.g., `PowerShell-7.4.1-win-x64.msi`)

2. **Install PowerShell 7**:
   - Run the downloaded MSI installer
   - Follow the installation wizard instructions
   - Make sure to select the option to "Add PowerShell to PATH environment variable" during installation
   - Complete the installation

3. **Verify Installation**:
   - Open a new Command Prompt or Windows Terminal
   - Run `pwsh -version` to confirm PowerShell 7 is installed correctly
   - You should see output indicating PowerShell 7.x

### Configuring PyCharm to Use PowerShell 7

1. **Open PyCharm**:
   - Launch PyCharm IDE

2. **Configure Terminal Settings**:
   - Go to File → Settings (or press Ctrl+Alt+S)
   - Navigate to Tools → Terminal
   - In the "Shell path" field, enter: `pwsh.exe`
   - Click "Apply" and "OK"

3. **Verify Configuration**:
   - Open a new terminal in PyCharm (Alt+F12)
   - The terminal should now be running PowerShell 7
   - You can verify by running `$PSVersionTable` which should show version 7.x

### Benefits of Using PowerShell 7 with PyCharm

- Improved performance compared to older PowerShell versions
- Better compatibility with modern scripting features
- Enhanced tab completion and command prediction
- Improved error handling and debugging capabilities
- Cross-platform support if you work across different operating systems

### Troubleshooting

If PyCharm cannot find PowerShell 7:
- Ensure PowerShell 7 is in your PATH environment variable
- Try using the full path to the PowerShell executable: `C:\Program Files\PowerShell\7\pwsh.exe`
- Restart PyCharm after making configuration changes