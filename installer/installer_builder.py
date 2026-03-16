"""
TG-PY Installer Builder
Automated script to build TG-PY.exe and create installer package.

Requirements:
    - Python 3.8+
    - Inno Setup installed (https://jrsoftware.org/isdl.php)
    - All dependencies from requirements.txt

Usage:
    python installer_builder.py
    OR
    run build_installer.bat
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# ── Colors for console output ────────────────────────────────────────────────
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_step(text):
    print(f"{Colors.CYAN}▶ {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"  {text}")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_OUTPUT = DIST_DIR

# ── Helper Functions ──────────────────────────────────────────────────────────

def check_python():
    """Check Python version."""
    print_step("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro} OK")
    return True

def check_inno_setup():
    """Check if Inno Setup is installed."""
    print_step("Checking Inno Setup...")
    
    # Common installation paths
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    iscc_path = None
    for path in possible_paths:
        if os.path.exists(path):
            iscc_path = path
            break
    
    # Also check PATH
    if not iscc_path:
        try:
            result = subprocess.run(
                ["where", "ISCC"],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0 and result.stdout.strip():
                iscc_path = result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
    
    if iscc_path:
        print_success(f"Inno Setup found: {iscc_path}")
        return iscc_path
    else:
        print_error("Inno Setup not found!")
        print_info("Download from: https://jrsoftware.org/isdl.php")
        print_info("Install and run this script again.")
        return None

def clean_builds():
    """Clean old build artifacts."""
    print_step("Cleaning old builds...")
    
    cleaned = []
    
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        cleaned.append(str(DIST_DIR))
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        cleaned.append(str(BUILD_DIR))
    
    # Clean __pycache__ folders
    for pycache in PROJECT_ROOT.glob("**/__pycache__"):
        shutil.rmtree(pycache)
        cleaned.append(str(pycache))
    
    if cleaned:
        print_success(f"Cleaned {len(cleaned)} items")
    else:
        print_info("Nothing to clean")
    
    return True

def install_dependencies():
    """Install required dependencies."""
    print_step("Installing dependencies...")
    
    requirements = PROJECT_ROOT / "requirements.txt"
    if not requirements.exists():
        print_warning("requirements.txt not found, skipping...")
        return True
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-q"],
            check=True,
            cwd=str(PROJECT_ROOT)
        )
        
        # Also install build tools
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "certifi", "pyinstaller", "-q"],
            check=True
        )
        
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def build_application():
    """Build TG-PY.exe using build.bat."""
    print_step("Building TG-PY.exe...")
    
    build_script = PROJECT_ROOT / "build.bat"
    if not build_script.exists():
        print_error("build.bat not found!")
        return False
    
    try:
        # Run build.bat
        result = subprocess.run(
            ["cmd", "/c", str(build_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        
        # Check if TG-PY.exe was created
        tgpy_exe = DIST_DIR / "TG-PY.exe"
        if tgpy_exe.exists():
            file_size = tgpy_exe.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            print_success(f"TG-PY.exe built successfully ({file_size_mb:.1f} MB)")
            return True
        else:
            print_error("TG-PY.exe not created!")
            if result.stdout:
                print_info("Output:")
                print(result.stdout)
            if result.stderr:
                print_error("Errors:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print_error(f"Build failed: {e}")
        return False

def build_installer(iscc_path):
    """Build installer using Inno Setup."""
    print_step("Building installer package...")
    
    setup_script = SCRIPT_DIR / "setup.iss"
    if not setup_script.exists():
        print_error("setup.iss not found!")
        return False
    
    try:
        result = subprocess.run(
            [iscc_path, str(setup_script)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error("Inno Setup compilation failed!")
            if result.stderr:
                print_error(result.stderr)
            return False
        
        # Find the output file
        version = "1.0.0"  # Could be extracted from version_info.txt
        installer_name = f"TG-PY-Setup-v{version}.exe"
        installer_path = INSTALLER_OUTPUT / installer_name
        
        if installer_path.exists():
            file_size = installer_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            print_success(f"Installer created: {installer_name} ({file_size_mb:.1f} MB)")
            return True
        else:
            # Try to find any .exe in dist folder
            exe_files = list(INSTALLER_OUTPUT.glob("TG-PY-Setup-*.exe"))
            if exe_files:
                installer_path = exe_files[0]
                file_size = installer_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                print_success(f"Installer created: {installer_path.name} ({file_size_mb:.1f} MB)")
                return True
            else:
                print_error("Installer file not found in dist folder!")
                return False
                
    except Exception as e:
        print_error(f"Installer build failed: {e}")
        return False

def show_summary():
    """Show build summary."""
    print_header("BUILD SUMMARY")
    
    # List files in dist folder
    if DIST_DIR.exists():
        files = list(DIST_DIR.iterdir())
        if files:
            print_info(f"Files in dist/ folder:")
            for f in files:
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print_info(f"  📄 {f.name} ({size_mb:.1f} MB)")
        else:
            print_warning("dist/ folder is empty")
    
    print_info("")
    print_info("Distribution:")
    print_info("  📦 Send 'TG-PY-Setup-v*.exe' to users")
    print_info("  🔧 Admin panel is separate (TG-PY-Admin.exe)")
    print_info("")
    print_info("User Installation:")
    print_info("  1. User runs TG-PY-Setup-v*.exe")
    print_info("  2. Installs to C:\\Program Files (x86)\\TG-PY")
    print_info("  3. Creates desktop shortcut")
    print_info("  4. Auto-creates runtime folders")
    print_info("")

# ── Main Build Process ────────────────────────────────────────────────────────

def main():
    """Main build process."""
    print_header("TG-PY INSTALLER BUILDER")
    print_info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Python: {sys.version}")
    print_info(f"Working Directory: {PROJECT_ROOT}")
    
    # Step 1: Check Python
    if not check_python():
        sys.exit(1)
    
    # Step 2: Check Inno Setup
    iscc_path = check_inno_setup()
    if not iscc_path:
        print_warning("Continuing without installer build (TG-PY.exe only)")
    
    # Step 3: Clean old builds
    if not clean_builds():
        sys.exit(1)
    
    # Step 4: Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Step 5: Build application
    print_header("STEP 1: Building Application")
    if not build_application():
        sys.exit(1)
    
    # Step 6: Build installer (if Inno Setup available)
    if iscc_path:
        print_header("STEP 2: Building Installer")
        if not build_installer(iscc_path):
            print_warning("Installer build failed, but TG-PY.exe is ready")
    
    # Step 7: Show summary
    print_header("BUILD COMPLETE")
    show_summary()
    
    print_success("Done! 🎉")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_error("Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print("\n")
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
