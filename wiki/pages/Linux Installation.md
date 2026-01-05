🏠 [`realbot-g3` Wiki Home](../README.md)

# 🐧 Linux Installation & Headless Setup

This guide covers how to set up RealBot G3 on Linux, including how to run it on a server without a GUI (headless) for 24/7 hunting.

## 1. System Requirements

You will need **Python 3.13** and a few system libraries for emulation and audio.

### Install Dependencies
Run the command for your distribution:

**Ubuntu & Derivatives (Mint, Pop!_OS):**
If `apt` says it cannot locate `python3.13`, you need to add the deadsnakes PPA:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
```
Then install the dependencies:
```bash
sudo apt install python3.13 python3.13-venv python3-tk libmgba0.10 portaudio19-dev
```
*Note: If `apt` selects `libmgba0.10t64` instead of `libmgba0.10`, that is fine.*

**Debian:**
Debian does not support PPAs. If Python 3.13 is not in your repositories, you may need to build it from source or use `testing`/`unstable` repos.
```bash
sudo apt update
sudo apt install python3.13 python3.13-venv python3-tk libmgba0.10 portaudio19-dev
```
*Note: Even for headless mode, `libmgba` is required. If `libmgba0.10` isn't in your repos, you can download the .deb from [mgba.io](https://mgba.io/downloads.html).*

**Arch Linux:**
```bash
sudo pacman -S python python-virtualenv tk libmgba portaudio
```

---

## 2. Setup the Bot

1. **Clone the Repo:**
   ```bash
   git clone https://github.com/realgarit/realbot-G3.git
   cd realbot-G3
   ```

2. **Create a Virtual Environment:**
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate
   ```

3. **Add your ROMs:**
   Place your official Pokémon `.gba` files into the `roms/` folder.

---

## 3. Running Headless (SSH Workflow)

If you are connecting to a Linux machine via SSH, closing your terminal will normally kill the bot. To keep it running 24/7, we recommend using **`tmux`**.

### Using `tmux` (Recommended)

1. **Install tmux:**
   ```bash
   sudo apt install tmux  # Ubuntu/Debian
   sudo pacman -S tmux    # Arch
   ```

2. **Start a new session:**
   ```bash
   tmux new -s shiny-hunt
   ```

3. **Start the bot in Headless Mode:**
   You **must** use the `-hl` flag to prevent the bot from trying to open a GUI window:
   ```bash
   source venv/bin/activate
   python realbot.py [ProfileName] -hl
   ```

4. **Detach from the session:**
   Press `Ctrl + B`, then let go and press `D`. 
   You can now safely close your SSH connection!

5. **Reattach later:**
   To check on your progress, log back in and run:
   ```bash
   tmux attach -t shiny-hunt
   ```

### Running Multiple Instances
To maximize encounters, you can run multiple bots in separate tmux windows or sessions. 
**Important**: Each instance MUST use a unique profile name (e.g., `Realgar1`, `Realgar2`) to avoid database corruption.

```bash
# In tmux window 1
python realbot.py Realgar1 -hl

# In tmux window 2
python realbot.py Realgar2 -hl
```

---

## 4. Troubleshooting

- **Audio Errors**: If the bot crashes with audio errors on a server, ensure `portaudio19-dev` is installed. You can also disable audio output with the `-na` flag.
- **Permission Denied**: If the bot cannot download `libmgba-py` during the first run, ensure your user has write permissions to the bot directory.
