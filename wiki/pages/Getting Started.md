🏠 [`realbot-g3` Wiki Home](../README.md)

# ❓ Getting Started

## Supported Operating Systems

<img src="../images/os_windows.png" alt="Windows" style="max-width: 80px"> <img src="../images/os_apple.png" alt="MacOS" style="max-width: 80px"> <img src="../images/os_ubuntu.png" alt="Ubuntu" style="max-width: 80px"> <img src="../images/os_debian.png" alt="Debian" style="max-width: 80px"> <img src="../images/os_pop.png" alt="PopOS" style="max-width: 80px"> <img src="../images/os_arch.png" alt="Arch Linux" style="max-width: 80px">

- Windows
- MacOS
- Linux, tested and confirmed working on the following distros:
  - Ubuntu 24.04
  - Debian 12
  - Pop!\_OS 22.04 LTS
  - Arch Linux

## What You'll Need

### Windows
- **Python 3.13** ([Download 64-bit installer](https://www.python.org/downloads/windows/))
  - **Important**: Check the box `Add Python to PATH` during installation.
  - Python 3.13 includes **Tkinter 9**, which is required for the bot's UI to look correct and fix scaling issues.

### Linux (Ubuntu/Debian/Arch)
- See the [Linux Installation guide](/wiki/pages/Linux%20Installation.md).

### macOS
- See the [macOS Installation guide](/wiki/pages/MacOS%20Installation.md).

---

## Download the Bot

### Stable Version
> **Coming Soon!** 
We are currently working on our first stable release for RealBot G3. Please use the Dev Version for now.

### Dev Version
Get the latest code directly from GitHub:

1.  **Download ZIP**: Go to [realgarit/realbot-G3](https://github.com/realgarit/realbot-G3), click **Code** > **Download ZIP`.
2.  **Git Clone**:
    ```bash
    git clone https://github.com/realgarit/realbot-G3.git
    ```

---

## Setup & Run

### 1. Set up a Virtual Environment (Recommended)
Using a `venv` keeps the bot's libraries separate from your system.

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Linux:**
```bash
python3.13 -m venv venv
source venv/bin/activate
```
*(You'll need to run the activate command every time you open a new terminal)*

### 2. Add ROMs
Place your **official** Pokémon .gba ROMs into the `roms/` folder.

### 3. Run the Bot
The bot handles its own requirements installation.

**Windows:**
```powershell
python realbot.py
```

**Linux:**
```bash
python3.13 realbot.py
```

Follow the on-screen prompts to create your profile!

---

## Tips & Troubleshooting

-   **Escape 100%**: Your lead Pokémon must be able to flee battles, or the bot will get stuck.
-   **Key Mappings**: Default controls are standard mGBA. Customize them in `profiles/config.yml` or check the [Key Mappings](pages/Configuration%20-%20Key%20Mappings.md) page.
-   **Updates**: Back up your `profiles/` folder before updating!
-   **Linux Audio**: If you get audio errors, ensure `portaudio19-dev` is installed.

## Importing Saves
1.  In mGBA, go to **File** > **Save State File...** and save a file.
2.  Run RealBot, choose a profile name, and select **Load Existing Save`.
3.  Support file types: `.ss1` (mGBA save states).

---

## Advanced Options

If you want to run the bot with specific settings from the terminal:

```text
python realbot.py [profile_name] [options]
```

### Common Options:
- `-d` or `--debug`: Opens a debug menu with extra info.
- `-m [MODE]`: Starts the bot in a specific mode (like `Spin` or `Fishing`).
- `-s [SPEED]`: Sets the initial speed (1x, 2x, etc.). Use `0` for unthrottled speed.
- `-nv`: Starts with video turned off.
- `-na`: Starts with audio turned off.
