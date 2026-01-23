#!/usr/bin/env python3
"""
GPO Fishing Macro - Dependency Installation Script
This script installs all required dependencies for the GPO fishing macro

Usage:
    python3 install_dependencies.py
"""

import subprocess
import sys
import os
import platform
import shutil


def run_command(cmd, description, check=True):
    """Run a command and return success status"""
    print(f"  {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0 and check:
            print(f"    Warning: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def check_python_version():
    """Check if Python 3.8+ is installed"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("\n✗ Error: Python 3.8 or higher is required.")
        print(f"  You have Python {version.major}.{version.minor}.{version.micro}")
        print("  Download from: https://www.python.org/downloads/")
        return False
    print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_homebrew():
    """Check if Homebrew is installed"""
    if shutil.which("brew"):
        print("  ✓ Homebrew installed")
        return True
    print("  ! Homebrew not found - will attempt to install")
    return False


def install_homebrew():
    """Install Homebrew"""
    print("\nInstalling Homebrew...")
    install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    try:
        result = subprocess.run(
            install_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if result.returncode == 0:
            print("  ✓ Homebrew installed successfully")
            return True
        else:
            print(f"  Error installing Homebrew: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  Error: Homebrew installation timed out")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def install_tesseract():
    """Install Tesseract OCR using Homebrew"""
    # Check if already installed
    if shutil.which("tesseract"):
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ Tesseract already installed: {result.stdout.strip()}")
                return True
        except:
            pass
    
    print("  Installing Tesseract OCR...")
    
    # Try to install
    success = run_command(
        "brew install tesseract",
        "Installing Tesseract"
    )
    
    if success:
        # Verify installation
        if shutil.which("tesseract"):
            try:
                result = subprocess.run(
                    ["tesseract", "--version"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"  ✓ Tesseract installed: {result.stdout.strip()}")
                    return True
            except:
                pass
    
    print("  ! Tesseract installation may have failed")
    return False


def install_python_packages():
    """Install required Python packages"""
    packages = [
        "customtkinter",
        "pynput", 
        "Pillow",
        "numpy",
        "mss",
        "pytesseract",
        "pyobjc"
    ]
    
    print("\n  Installing Python packages...")
    
    # Upgrade pip first
    print("    Upgrading pip...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True
    )
    
    # Install packages
    success_count = 0
    for package in packages:
        print(f"    Installing {package}...", end=" ")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓")
            success_count += 1
        else:
            print("✗")
            print(f"      Error: {result.stderr.strip()[:100]}")
    
    return success_count == len(packages)


def verify_imports():
    """Verify all Python imports work"""
    print("\n  Verifying imports...")
    
    modules = [
        ("customtkinter", "Modern GUI framework"),
        ("pynput.mouse", "Mouse input"),
        ("pynput.keyboard", "Keyboard input"),
        ("PIL.Image", "Image processing (Pillow)"),
        ("numpy", "Numerical operations"),
        ("mss", "Screen capture"),
        ("pytesseract", "OCR for text detection"),
        ("Quartz", "macOS graphics API"),
        ("AppKit", "macOS application API"),
        ("Foundation", "macOS Foundation API"),
    ]
    
    all_passed = True
    for module_name, description in modules:
        try:
            # Handle special cases
            if module_name == "pynput.mouse":
                from pynput import mouse
            elif module_name == "pynput.keyboard":
                from pynput import keyboard
            elif module_name == "PIL.Image":
                from PIL import Image
            else:
                __import__(module_name)
            print(f"    ✓ {module_name}")
        except ImportError as e:
            print(f"    ✗ {module_name} - {e}")
            all_passed = False
    
    return all_passed


def check_tesseract_path():
    """Check if Tesseract is accessible"""
    if shutil.which("tesseract"):
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"    ✓ Tesseract: {result.stdout.strip()}")
                return True
        except:
            pass
    
    print("    ⚠ Tesseract not found in PATH")
    print("      Devil fruit detection may not work.")
    print("      Install with: brew install tesseract")
    return False


def print_instructions():
    """Print next steps for the user"""
    print("\n" + "=" * 50)
    print("✓ INSTALLATION COMPLETE!")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Run the macro: python3 gpo_mac_macro.py")
    print("  2. Configure detection areas (click 'Change Area')")
    print("  3. Set your water point in the Pre-cast tab")
    print("  4. Press '[' to start fishing!")
    print("\nIMPORTANT - Grant Accessibility Permissions:")
    print("  System Settings → Privacy & Security → Accessibility")
    print("  Add your terminal app or Python to the list.")
    print("\nIf Tesseract wasn't installed:")
    print("  Run: brew install tesseract")


def main():
    """Main installation function"""
    print("\n" + "=" * 50)
    print("GPO Fishing Macro - Dependency Installer")
    print("=" * 50)
    
    # Check OS
    if platform.system() != "Darwin":
        print("\n✗ Error: This script is for macOS only.")
        print("  The GPO fishing macro requires macOS APIs (Quartz, CGEvent).")
        sys.exit(1)
    
    print(f"\nDetected: macOS {platform.mac_ver()[0]}")
    
    # Check Python version
    print("\n[1/4] Checking Python installation...")
    if not check_python_version():
        sys.exit(1)
    
    # Check/Install Homebrew
    print("\n[2/4] Checking Homebrew...")
    if not check_homebrew():
        if install_homebrew():
            # Need to update PATH for current session
            os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")
    
    # Install Tesseract
    print("\n[3/4] Installing Tesseract OCR...")
    install_tesseract()
    
    # Install Python packages
    print("\n[4/4] Installing Python packages...")
    packages_ok = install_python_packages()
    
    # Verify everything
    print("\n" + "-" * 50)
    print("Verification:")
    print("-" * 50)
    verify_imports()
    check_tesseract_path()
    
    # Print instructions
    if packages_ok:
        print_instructions()
    else:
        print("\n" + "=" * 50)
        print("⚠ Some packages failed to install")
        print("=" * 50)
        print("Please check the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()

