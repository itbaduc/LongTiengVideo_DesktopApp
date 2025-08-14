import os
import sys
import subprocess
import zipfile
import requests
import json
from pathlib import Path
import time
import logging
from typing import Optional
import shutil

logger = logging.getLogger(__name__)


class BackendManager:
    def __init__(self):
        self.app_data_dir = Path(os.getenv("APPDATA")) / "ai_dubbing"
        self.backend_dir = self.app_data_dir / "client_backend"
        self.backend_zip_path = self.app_data_dir / "python_client_backend.zip"
        self.process = None
        self.max_startup_retries = 3
        self.startup_delay = 5  # seconds
        # self.main_file_to_run = "main.py"
        self.main_file_to_run = "run.py"

    def ensure_app_data_dir(self):
        """Tạo thư mục app data nếu chưa tồn tại"""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"App data directory: {self.app_data_dir}")

    def is_backend_installed(self) -> bool:
        """Kiểm tra xem backend đã được cài đặt chưa"""
        python_exe_exists = self.get_python_executable()
        run_py = self.backend_dir / self.main_file_to_run

        run_py_exists = run_py.exists()

        return python_exe_exists and run_py_exists

    def download_backend(self, download_url: str, progress_callback=None) -> bool:
        """Tải backend zip từ URL với progress tracking"""
        try:
            logger.info(f"Đang tải backend từ: {download_url}")

            # Tạo thư mục nếu chưa có
            self.backend_zip_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(download_url, stream=True, timeout=600)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(self.backend_zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0 and progress_callback:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(int(progress))

            logger.info(f"Đã tải backend thành công: {self.backend_zip_path}")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi tải backend: {e}")
            return False

    def extract_backend(self, progress_callback=None) -> bool:
        """Giải nén backend zip"""
        try:
            logger.info(f"Đang giải nén backend từ: {self.backend_zip_path}")

            # Xóa thư mục backend cũ nếu tồn tại
            if self.backend_dir.exists():
                shutil.rmtree(self.backend_dir)

            # Giải nén
            with zipfile.ZipFile(self.backend_zip_path, "r") as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)

                for i, file_info in enumerate(file_list):
                    zip_ref.extract(file_info, self.app_data_dir)
                    if progress_callback and total_files > 0:
                        progress = int((i + 1) / total_files * 100)
                        progress_callback(progress)

            # Xóa file zip sau khi giải nén
            self.backend_zip_path.unlink(missing_ok=True)

            logger.info("Đã giải nén backend thành công")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi giải nén backend: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_python_executable(self) -> Optional[Path]:
        """Lấy đường dẫn tới python.exe trong Python portable"""
        if os.name == "nt":  # Windows
            python_exe = self.backend_dir / "python_portable" / "python.exe"
        else:  # Linux/Mac
            python_exe = self.backend_dir / "python_portable" / "bin" / "python"

        if python_exe.exists():
            return python_exe
        else:
            logger.error(f"Không tìm thấy Python executable: {python_exe}")
            return False

    def start_backend(self, status_callback=None) -> bool:
        """Khởi động backend service với retry mechanism"""
        for attempt in range(self.max_startup_retries):
            if status_callback:
                status_callback(
                    f"Đang khởi động backend (lần thử {attempt + 1}/{self.max_startup_retries})..."
                )

            if self._start_backend_once():
                # Kiểm tra backend sẵn sàng
                if self._wait_for_backend_ready(status_callback):
                    logger.info("Backend đã khởi động và sẵn sàng")
                    return True
                else:
                    logger.warning(
                        f"Backend khởi động nhưng không sẵn sàng (lần thử {attempt + 1})"
                    )
            else:
                logger.warning(f"Backend khởi động thất bại (lần thử {attempt + 1})")

            # Dừng backend nếu đang chạy
            self.stop_backend()

            if attempt < self.max_startup_retries - 1:
                if status_callback:
                    status_callback(f"Thử lại sau 5 giây...")
                time.sleep(5)

        logger.error("Backend khởi động thất bại sau tất cả các lần thử")
        return False

    def _start_backend_once(self) -> bool:
        """Khởi động backend một lần"""
        try:
            if not self.is_backend_installed():
                logger.error("Backend chưa được cài đặt")
                return False

            python_exe = self.get_python_executable()
            if not python_exe:
                return False

            run_py = self.backend_dir / self.main_file_to_run
            if not run_py.exists():
                logger.error(f"Không tìm thấy file {self.main_file_to_run}: {run_py}")
                return False

            # Kiểm tra xem backend đã chạy chưa
            if self.is_backend_running():
                logger.info("Backend đã đang chạy")
                return True

            # Khởi động backend
            logger.info("Đang khởi động backend service...")
            logger.info(f"Python: {python_exe}")
            logger.info(f"Script: {run_py}")

            # Sử dụng shell=True để đảm bảo môi trường chạy đúng
            self.process = subprocess.Popen(
                [str(python_exe), str(run_py)],
                cwd=str(self.backend_dir),
                # stdout=subprocess.PIPE,
                # stderr=subprocess.PIPE,
                # text=True,
                # creationflags=(
                #     subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                # ),
            )

            logger.info(f"Backend service started with PID: {self.process.pid}")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi khởi động backend: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _wait_for_backend_ready(self, status_callback=None) -> bool:
        """Chờ backend sẵn sàng"""
        import requests

        for i in range(30):  # Chờ tối đa 30 giây
            try:
                if status_callback:
                    status_callback(f"Đang kiểm tra trạng thái AI... ({i+1}/30)")

                response = requests.get(
                    "http://127.0.0.1:17199/v1/check/status", timeout=5
                )
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if (
                            data.get("status") == "ready"
                            and data.get("gpu") == "available"
                            and data.get("models") == "loaded"
                        ):
                            logger.info("Backend is healthy and ready!")
                            return True
                        else:
                            logger.info(f"Backend not ready yet: {data}")
                    except json.JSONDecodeError:
                        logger.info("Backend responded but not in JSON format")
                else:
                    logger.info(f"Backend returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.debug(f"Cannot connect to backend: {e}")

            time.sleep(1)

        logger.error("Backend không sẵn sàng trong thời gian quy định")
        return False

    def is_backend_running(self) -> bool:
        """Kiểm tra backend có đang chạy không"""
        if self.process is None:
            return False

        try:
            # Kiểm tra process còn sống không
            if self.process.poll() is None:
                return True
            else:
                self.process = None
                return False
        except:
            self.process = None
            return False

    def stop_backend(self):
        """Dừng backend service"""
        if self.process and self.process.poll() is None:
            try:
                logger.info("Đang dừng backend service...")
                if os.name == "nt":
                    # Windows: gửi tín hiệu CTRL_BREAK_EVENT
                    self.process.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
                else:
                    # Unix: gửi SIGTERM
                    self.process.terminate()

                try:
                    self.process.wait(timeout=15)  # Tăng timeout lên 15 giây
                except subprocess.TimeoutExpired:
                    logger.warning("Backend không phản hồi, buộc dừng...")
                    self.process.kill()
                    self.process.wait()

                logger.info("Backend service đã dừng")
            except Exception as e:
                logger.error(f"Lỗi khi dừng backend: {e}")

        self.process = None


# Singleton instance
backend_manager = BackendManager()
