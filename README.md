# GPO Fishing Macro for macOS

An automated fishing macro for Grand Piece Online (GPO) on Roblox, designed specifically for macOS. Features include auto-cast fishing, PID controller for catching mechanics, auto-buy bait, and auto-store devil fruits. Vibecoding core

## Features

- 🎣 **Auto-Fishing**: Automatically casts and catches fish using PID controller
- 🖱️ **PID Control**: Smooth bar control for optimal catching
- 🛒 **Auto-Buy Bait**: Automatically purchases common bait at set intervals
- 🍎 **Auto-Store Devil Fruits**: Detects and stores devil fruit drops
- 🎨 **Modern UI**: Built with CustomTkinter for a clean dark theme
- ⌨️ **Hotkey Support**: Customizable hotkeys for all actions
- 🔧 **Visual Area Selection**: Draggable overlays for configuring detection areas

## Requirements

### System Requirements
- **macOS** (This macro uses macOS-specific APIs: Quartz, CGEvent, AppKit)
- Python 3.8 or higher
- Roblox installed
- Administrator permissions may be required for input injection

### Python Dependencies

Install all required Python packages:

```bash
pip install customtkinter pynput Pillow numpy mss pytesseract pyobjc
```

**Package Details:**
| Package | Purpose |
|---------|---------|
| `customtkinter` | Modern GUI framework |
| `pynput` | Mouse and keyboard input monitoring |
| `Pillow` | Image processing for screenshots |
| `numpy` | Numerical operations for color detection |
| `mss` | Fast screen capture |
| `pytesseract` | OCR for devil fruit text detection |
| `pyobjc` | macOS native APIs (Quartz, AppKit, Foundation) |

### System Dependencies

#### Tesseract OCR (Optional - for devil fruit detection)

**Install via Homebrew:**
```bash
# If you don't have Homebrew, install it first:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Tesseract:
brew install tesseract
```

**Verify installation:**
```bash
tesseract --version
```

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   (Or install manually as shown above)

3. **Install Tesseract OCR** (for devil fruit detection):
   ```bash
   brew install tesseract
   ```

4. **Run the macro:**
   ```bash
   python3 gpo_mac_macro.py
   ```

## Initial Setup

### 1. Configure Detection Areas

When you first run the macro, you'll need to set up the detection areas:

1. Click **"Change Area ([)"** button
2. A blue overlay will appear - drag/resize it to cover the **fishing bar area**
3. A green overlay will appear - drag/resize it to cover the **loot drop area**
4. Click anywhere to close the overlays and save positions

### 2. Set Water Point

1. Go to the "Pre-cast" tab
2. Click **"Set Water Point"**
3. Click on the water where you want to cast your line
4. The coordinates will be saved automatically

### 3. Configure Auto-Buy Bait (Optional)

1. Go to the "Pre-cast" tab
2. Enable **"Enable Auto Buy"** checkbox
3. Click **"Set Left Point"** - click on the left buy button in the shop
4. Click **"Set Middle Point"** - click on the middle/confirm button
5. Click **"Set Right Point"** - click on the right buy button
6. Set **"Loops Per Purchase"** to how many catches before buying bait

### 4. Configure Auto-Store Devil Fruit (Optional)

1. Go to the "Pre-cast" tab
2. Enable **"Enable Auto Store"** checkbox
3. Click **"Set Store Fruit Point"** - click on the fruit storage NPC
4. Set the **hotkey numbers** for:
   - Devil Fruit (number key)
   - Rod (number key)
   - Anything else (number key - used for anti-macro detection)

### 5. Configure Timeout

In the "Post-cast" tab:
- Set **"Waiting Timeout"** to maximum seconds to wait for a bite before recasting

## Usage

### Hotkeys

| Action | Default Key | Description |
|--------|-------------|-------------|
| Start/Stop | `[` | Toggle macro on/off |
| Change Area | `]` | Configure detection areas |
| Exit | `F3` | Exit the application |

### Running the Macro

1. Open Roblox and start Grand Piece Online
2. Go to a fishing spot
3. Run the macro: `python3 gpo_mac_macro.py`
4. Press `[` to start fishing
5. Press `[` again to stop

### Tips for Best Results

- **Always run Roblox in windowed or borderless windowed mode**
- **Set your graphics quality to a level where the fishing bar is clearly visible**
- **The macro works best when the fishing bar has high contrast**
- **Test your detection areas before extended use**
- **Keep the macro window visible (not minimized)**

## Troubleshooting

### Macro Not Responding to Hotkeys

1. Make sure the macro window has focus when pressing hotkeys
2. Check that pynput has permissions: System Preferences → Security & Privacy → Accessibility

### Permission Issues (macOS)

If you get permission errors for keyboard/mouse input:

1. **Accessibility Permissions:**
   ```
   System Settings → Privacy & Security → Accessibility
   ```
   Add Python or your terminal app to the list

2. **Input Monitoring Permissions:**
   ```
   System Settings → Privacy & Security → Input Monitoring
   ```
   Add Python or your terminal app to the list

### Tesseract/OCR Not Working

1. Verify Tesseract is installed: `tesseract --version`
2. If not found, add to PATH or create symlink:
   ```bash
   sudo ln -s /opt/homebrew/bin/tesseract /usr/local/bin/tesseract
   ```
3. Ensure `pytesseract` can find Tesseract:
   ```python
   import pytesseract
   print(pytesseract.get_tesseract_version())
   ```

### Blue Color Not Detecting

1. Check your detection area covers the fishing bar
2. The bar color is RGB(107, 168, 248) - make sure this color is visible
3. Lower graphics quality for better color contrast
4. Avoid having other blue objects in the detection area

### Creating Standalone App (Optional)

To create a standalone `.app` file:

```bash
# Install py2app
pip install py2app

# Create the app
python setup.py py2app

# The app will be in dist/gpo_mac_macro.app
```

## File Structure

```
GPO fishing macro 7_mac/
├── gpo_mac_macro.py      # Main application
├── setup.py              # Setup script for py2app
├── gpo_mac_macro.spec    # PyInstaller spec file
├── GPOsettings.json      # Saved settings (created after first run)
├── README.md             # This file
└── fishing_screenshots/  # Debug screenshots folder
```

## Settings File

Settings are automatically saved to `GPOsettings.json`. You can back up this file to preserve your configuration.

Example structure:
```json
{
    "water_point": [1920, 1080],
    "left_point": [100, 200],
    "middle_point": [300, 400],
    "right_point": [500, 600],
    "bar_area": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
    "drop_area": {"x1": 400, "y1": 100, "x2": 600, "y2": 300},
    "auto_buy_common_bait": true,
    "loops_per_purchase": 100
}
```

## Notes

- This macro is **macOS-only** due to its use of Quartz/CGEvent APIs
- Using macros in online games may violate terms of service - use at your own risk
- The macro requires the Roblox window to be visible and not obscured
- For best results, use a screen resolution of 1920x1080 or higher

## Credits

Built with Python and:
- CustomTkinter
- pynput
- mss
- numpy
- pytesseract

