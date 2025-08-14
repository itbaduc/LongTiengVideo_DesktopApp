import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QLabel,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QFont
import logging

# Import backend manager
from backend_manager import backend_manager

logger = logging.getLogger(__name__)


class BackendSetupWorker(QThread):
    """Worker thread để cài đặt và khởi động backend"""

    progress = pyqtSignal(str, int)  # message, progress_percent
    status = pyqtSignal(str)  # status message
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            # Setup backend
            backend_manager.ensure_app_data_dir()

            # Kiểm tra backend đã cài đặt chưa
            if not backend_manager.is_backend_installed():
                self.status.emit("Đang tải backend...")
                self.progress.emit("Đang tải backend...", 10)

                if not backend_manager.download_backend(
                    self.download_url,
                    progress_callback=lambda p: self.progress.emit(
                        f"Đang tải: {p}%", p
                    ),
                ):
                    self.finished.emit(False, "Không thể tải backend")
                    return

                self.progress.emit("Đang giải nén backend...", 70)
                if not backend_manager.extract_backend(
                    progress_callback=lambda p: self.progress.emit(
                        f"Đang giải nén: {p}%", 70 + int(p * 0.2)
                    )
                ):
                    self.finished.emit(False, "Không thể giải nén backend")
                    return

                self.progress.emit("Đã cài đặt backend", 90)

            # Khởi động backend
            self.status.emit("Đang khởi động backend...")
            if backend_manager.start_backend(status_callback=self.status.emit):
                self.finished.emit(True, "Backend đã sẵn sàng")
            else:
                self.finished.emit(False, "Không thể khởi động backend sau 3 lần thử")

        except Exception as e:
            logger.error(f"Lỗi trong worker: {e}")
            import traceback

            traceback.print_exc()
            self.finished.emit(False, f"Lỗi: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trình duyệt Đơn giản")
        self.setGeometry(100, 100, 1400, 900)

        # Thiết lập phong cách tổng thể (theme tối)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { 
                background-color: #1a1a1a; 
                color: #ffffff; 
            }
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                margin: 5px 0px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:checked {
                background-color: #4a90e2;
            }
            QPushButton:checked:hover {
                background-color: #5a9ee5;
            }
            QFrame#content_frame {
                background-color: #252525;
                border-radius: 10px;
            }
        """
        )

        # Widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout chính (chia 2 cột)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Cột bên trái (menu)
        left_column = QFrame()
        left_column.setFixedWidth(180)
        left_column.setStyleSheet("background-color: #202020; border-radius: 10px;")
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        # Thay thế 'path/to/your/logo.png' bằng đường dẫn thực tế đến file logo của bạn.
        # Nếu bạn muốn sử dụng văn bản như trong PDF, hãy dùng:
        logo_pixmap = QPixmap()  # Tạo pixmap rỗng
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_text = QLabel("合")
        logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_text.setStyleSheet("color: white; font-size: 48px; font-weight: bold;")
        logo_text.setFont(QFont("Arial", 48, QFont.Weight.Bold))

        left_layout.addWidget(logo_text)
        left_layout.addSpacing(20)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Các nút menu với biểu tượng
        self.menu_buttons = []
        # Đường dẫn đến các file icon. Bạn cần tải các icon phù hợp và đặt đường dẫn chính xác.
        # Dưới đây là ví dụ với tên file, bạn cần thay thế bằng đường dẫn thực tế.
        button_configs = [
            ("Home", "home.png", "https://www.google.com"),
            ("YouTube", "youtube.png", "https://www.youtube.com"),
            ("Udemy", "udemy.png", "https://www.udemy.com"),
            ("DeepLearning", "learning.png", "https://www.deeplearning.ai"),
        ]

        for name, icon_file, url in button_configs:
            button = QPushButton(name)
            button.setCheckable(True)
            button.setFixedHeight(50)
            button.setFont(QFont("Arial", 12))
            # Thử tải và đặt icon. Nếu file không tồn tại, sẽ không có icon.
            try:
                # Thay 'icons/' bằng thư mục chứa icon của bạn.
                button.setIcon(QIcon(f"icons/{icon_file}"))
                button.setIconSize(QSize(24, 24))
            except:
                pass  # Bỏ qua nếu không tìm thấy icon
            button.setLayoutDirection(
                Qt.LayoutDirection.LeftToRight
            )  # Đặt icon ở bên phải
            button.clicked.connect(lambda checked, u=url: self.load_page(u))
            left_layout.addWidget(button)
            self.menu_buttons.append(button)

        # Khoảng trống linh hoạt để đẩy các nút lên trên
        left_layout.addStretch()

        # Cột bên phải (nội dung web)
        right_column = QFrame()
        right_column.setObjectName("content_frame")  # Để áp dụng style CSS
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Tạo QWebEngineView
        self.browser = QWebEngineView()
        # Tải trang mặc định
        self.browser.load(QUrl("https://www.google.com"))
        right_layout.addWidget(self.browser)

        # Thêm cột vào layout chính
        main_layout.addWidget(left_column)
        main_layout.addWidget(right_column, 1)  # Cột phải chiếm phần còn lại

        # Chọn nút đầu tiên
        if self.menu_buttons:
            self.menu_buttons[0].setChecked(True)

    def log_message(self, message):
        """Thêm message vào log area"""
        self.setup_log.append(f"[{self.get_current_time()}] {message}")
        logger.info(message)

    def get_current_time(self):
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    def start_backend_setup(self):
        """Bắt đầu quá trình cài đặt và khởi động backend"""
        # TODO: Thay bằng URL thật
        download_url = "http://127.0.0.1:17199/static/python_client_backend.zip"

        self.log_message("Bắt đầu cài đặt backend...")

        self.setup_thread = BackendSetupWorker(download_url)
        self.setup_thread.progress.connect(self.update_progress)
        self.setup_thread.status.connect(self.update_status)
        self.setup_thread.finished.connect(self.on_setup_finished)
        self.setup_thread.start()

    def update_progress(self, message, percent):
        """Cập nhật tiến trình"""
        self.setup_status.setText(message)
        self.setup_progress.setValue(percent)
        self.log_message(message)

    def update_status(self, message):
        """Cập nhật trạng thái"""
        self.setup_status.setText(message)
        self.log_message(message)

    def on_setup_finished(self, success, message):
        """Xử lý khi setup hoàn tất"""
        if success:
            self.log_message("✓ " + message)
            self.backend_ready = True
            self.switch_to_main_interface()
        else:
            self.log_message("✗ " + message)
            QMessageBox.critical(self, "Lỗi", message)
            QApplication.quit()

    def load_page(self, url):
        """Tải trang web và cập nhật trạng thái nút."""
        self.browser.load(QUrl(url))
        for button in self.menu_buttons:
            button.setChecked(button.sender() == button)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Thiết lập attribute trước khi tạo cửa sổ nếu cần
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
