# MuMuPlayer / LDPlayer Game Automation System (OpenClaw)

A Python-based automation framework for Android Emulators (primarily **MuMuPlayer 12**, with backward compatibility for LDPlayer) that uses computer vision to perform complex game workflows, such as automated account switching and login.

## Project Overview

The system is designed to automate specific tasks within a mobile game running on MuMuPlayer (or LDPlayer). It uses a "Step-Action-Verify" loop:
1.  **Step**: Define a logical goal (e.g., "Login").
2.  **Action**: Identify a UI element using template matching and click it.
3.  **Verify**: Check if the next expected UI element appears or if the current one disappears.

The project also handles common interruptions like resource downloads, update prompts, and network disconnections automatically.

## Core Technologies

-   **Python 3**: The primary language for logic and orchestration.
-   **OpenCV (cv2)**: Used for high-performance image template matching (`TM_CCOEFF_NORMED`).
-   **PyAutoGUI / pygetwindow**: Used for mouse control, window management, and screen capture.
-   **psutil**: Used for managing emulator processes (monitoring, killing, and restarting).
-   **NumPy**: Used for efficient image data manipulation.
-   **MuMuManager CLI / Winreg**: Used to automatically locate and control the MuMuPlayer emulator (with registry auto-detection).

## Project Structure

-   `main_controller.py`: The main entry point. Handles configuration loading, logger setup, and execution flow.
-   `config.json`: Configuration file for local paths (`mumu_exe`, `dnplayer_exe`, `python_exe`), VM instance index (`vm_index`), and global settings.
-   `modules/`:
    -   `game_bot.py`: Implements the `GameBot` class which defines the high-level business logic, window activation, and automation sequences.
    -   `template_matcher.py`: A robust vision engine that supports multiple template images per logical target using OpenCV.
    -   `emulator_manager.py`: Utilities for starting, stopping, controlling, and locating the MuMu/LDPlayer emulator. Supports official `MuMuManager.exe` CLI control.
    -   `logger.py`: Centralized logging configuration.
    -   `visual_bot.py`: (Legacy/Alternative) Vision utilities using PyAutoGUI's native methods.
-   `assets/`: A directory containing subfolders for each UI element. Each folder (e.g., `assets/start/`) can contain multiple images to improve recognition across different resolutions or states.
-   `switch_mumu_account.bat` / `switch_dn_account.bat`: Helper batch scripts for executing account switching logic.
-   `locate_emulator.py`: Diagnostic utility to find and focus the emulator window.

## Getting Started

### Prerequisites

Ensure you have the following Python packages installed:
```bash
pip install pyautogui opencv-python numpy psutil pygetwindow pywin32
```

### Configuration

1.  Open `config.json`.
2.  Verify the `mumu_exe` path matches your local MuMu installation (defaults to `H:\Netease\MuMuPlayer\nx_main\MuMuNxMain.exe` and `MuMuManager.exe`).
3.  Set `vm_index` to your desired instance (default: `"1"` or `"auto"`).
4.  Adjust `click_confidence` (default `0.8`) if the bot is failing to find UI elements or clicking incorrectly.

### Running the Bot

Execute via batch script:
```cmd
switch_mumu_account.bat
```
Or directly with Python:
```bash
python main_controller.py
```

## Development Conventions

-   **Templates**: When adding new UI elements, create a folder in `assets/` and place one or more `.png` or `.jpg` screenshots of the target element inside.
-   **Flow Control**: New automation sequences should be added to the `steps` list in `modules/game_bot.py`.
-   **Interrupts**: Global interrupt checks (like "Offline Retry") should be added to `GameBot.check_interrupts()` to ensure they are checked during every step.
-   **Logging**: Use the provided `log` object to record information, warnings, and errors. Logs are saved to the file specified in `config.json` (default `bot_run.log`).
