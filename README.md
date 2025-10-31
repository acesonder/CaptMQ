# CaptMQ - OUTSINC VR Experience

A VR-compatible web application designed for Meta Quest 3S headsets.

## Features

### Splash Screen
- Beautiful blue sunny sky background with animated rolling clouds
- "OUTSINC" branding in large, extruded gothic letters with black outer glow effect
- Smooth fade-in/fade-out animations transitioning to the main menu

### Main Menu
- Dark evening sky background with twinkling and moving stars
- Menu options in white gothic letters:
  - New Game
  - Settings
  - Options
  - Quit

## VR Compatibility

This webapp is designed to work with Meta Quest 3S and other WebXR-compatible VR headsets:
- Responsive design that adapts to VR displays
- Touch and controller input support
- WebXR API integration for VR session detection

## How to Use

### On Desktop/Browser
1. Open `index.html` in a modern web browser
2. Watch the splash screen animation
3. The main menu will appear automatically after 9 seconds

### On Meta Quest 3S
1. Open the Meta Quest Browser
2. Navigate to the hosted URL of this application
3. The webapp will automatically detect VR capabilities
4. Use your VR controllers to interact with menu items

## Local Development

To run locally:
```bash
python3 -m http.server 8080
```

Then navigate to `http://localhost:8080/index.html`

## Technical Details

- Pure HTML/CSS/JavaScript - no dependencies required
- CSS animations for smooth visual effects
- WebXR API support for VR device detection
- Gamepad API integration for VR controller support
- Touch-friendly interface for VR interactions

## Screenshots

**Splash Screen:**
![Splash Screen](https://github.com/user-attachments/assets/2cbb9e0d-fbca-477d-a0bd-cdee8385ef7a)

**Main Menu:**
![Main Menu](https://github.com/user-attachments/assets/7046d9f8-9e64-48e2-aa79-f8db754dc45a)