import os
import sys
import subprocess
from pathlib import Path


def build_desktop_app():
    """Build desktop application với PyInstaller"""

    # Thư mục hiện tại
    current_dir = Path(__file__).parent
    desktop_dir = current_dir.parent / "desktop_app"
    dist_dir = current_dir.parent / "dist"

    # Di chuyển đến thư mục desktop_app
    os.chdir(desktop_dir)

    # Lệnh PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "AI_Video_Dubbing",
        "--windowed",  # Ứng dụng GUI
        "--onefile",  # Một file exe
        "--clean",  # Clean build
        "--distpath",
        str(dist_dir),
        "--add-data",
        f"{desktop_dir / 'ui'};ui",
        "--add-data",
        f"{desktop_dir / 'backend_manager.py'};.",
        "--hidden-import",
        "PyQt6.QtWebEngineWidgets",
        "--hidden-import",
        "requests",
        "main.py",
    ]

    print("Đang build desktop application...")
    print(f"Lệnh: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build thành công!")
        print(result.stdout)

        # Hiển thị file exe đã tạo
        exe_file = dist_dir / "AI_Video_Dubbing.exe"
        if exe_file.exists():
            print(f"File exe tạo ra: {exe_file}")
        else:
            print("Không tìm thấy file exe!")

    except subprocess.CalledProcessError as e:
        print("Build thất bại!")
        print(e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build_desktop_app()
