import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Thêm QSize nếu chưa có
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal, QSize
import logging
from const import DOWNLOAD_AI_SERVICE_PACKAGE

# Import backend manager
from backend_manager import backend_manager

logger = logging.getLogger(__name__)

# Xác định đường dẫn tới thư mục icons
# Giả định thư mục icons nằm cùng cấp với ui/main_window.py
# Nếu khác, hãy điều chỉnh đường dẫn tương ứng
CURRENT_DIR = Path(__file__).parent.resolve()
ICONS_DIR = CURRENT_DIR.parent / "icons"  # Điều hướng lên một cấp từ ui/


class BackendSetupWorker(QThread):
    """Worker thread để cài đặt và khởi động backend"""

    progress = pyqtSignal(str, int)  # message, progress_percent
    status = pyqtSignal(str)  # status message
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self):
        super().__init__()

        # TODO: Thay bằng URL thật
        download_url = DOWNLOAD_AI_SERVICE_PACKAGE
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
        self.backend_ready = False
        self.setup_thread = None
        self.init_ui()
        self.start_backend_setup()

    def init_ui(self):
        self.setWindowTitle("AI Video Dubbing")
        self.setGeometry(100, 100, 1200, 1000)

        # Central widget
        central_widget = QWidget()
        central_widget.setMinimumWidth(1200)
        central_widget.setMinimumHeight(1000)

        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Setup phase - hiển thị khi đang cài đặt backend
        self.setup_widget = QWidget()
        self.setup_layout = QVBoxLayout(self.setup_widget)
        self.setup_layout.setContentsMargins(10, 10, 10, 10)

        self.setup_title = QLabel("Đang chuẩn bị ứng dụng...")
        self.setup_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setup_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.setup_layout.addWidget(self.setup_title)

        self.setup_status = QLabel("Đang khởi tạo...")
        self.setup_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setup_layout.addWidget(self.setup_status)

        self.setup_progress = QProgressBar()
        self.setup_progress.setRange(0, 100)
        self.setup_layout.addWidget(self.setup_progress)

        self.setup_log = QTextEdit()
        self.setup_log.setMaximumHeight(150)
        self.setup_log.setReadOnly(True)
        self.setup_layout.addWidget(self.setup_log)

        main_layout.addWidget(self.setup_widget)

        # Main app widget - ẩn khi đang setup
        self.main_widget = QWidget()
        self.main_widget.setVisible(False)
        main_layout.addWidget(self.main_widget)

        # Create splitter for 2-column layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)  # Width of the divider
        splitter.setChildrenCollapsible(
            False
        )  # Ngăn không cho các panel collapse hoàn toàn

        # Left column (menu panel)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 10, 5, 10)  # Giảm margin trái/phải
        left_layout.setSpacing(15)  # Tăng spacing giữa các phần tử
        left_panel.setFixedWidth(150)  # Tăng width một chút để đủ chỗ cho icon + text

        # --- Logo ---
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Load logo pixmap
        logo_path = ICONS_DIR / "logo.svg"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # Scale pixmap, giữ aspect ratio
            scaled_pixmap = pixmap.scaled(
                QSize(80, 80),  # Kích thước mong muốn
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback nếu không tìm thấy logo.png
            self.logo_label.setText("AI Dub")
            self.logo_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        # Đặt size policy để label không chiếm không gian dư thừa
        self.logo_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.logo_label.setMinimumHeight(90)  # Đảm bảo có không gian cho logo

        left_layout.addWidget(self.logo_label)

        # Menu buttons
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setSpacing(8)  # Khoảng cách giữa các menu buttons
        self.menu_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )  # Căn các buttons lên trên

        # --- Hàm helper để tạo menu button ---
        def create_menu_button(icon_name: str, text: str, url: str = None):
            """Tạo một menu button với icon và text"""
            button = QPushButton(text)
            button.setIconSize(QSize(24, 24))  # Kích thước icon

            # Load icon
            icon_path = ICONS_DIR / f"{icon_name}.png"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                button.setIcon(icon)
            else:
                # Nếu không có icon, có thể để trống hoặc dùng text thay thế
                # Ở đây chúng ta vẫn giữ text và không có icon
                pass

            # Căn text sang phải, icon sang trái
            button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            # Có thể điều chỉnh stylesheet nếu cần
            # button.setStyleSheet("text-align: left; padding: 5px;")

            if url:
                button.clicked.connect(lambda _, u=url: self.load_url(u))
            return button

        # --- Tạo các menu buttons ---
        # Trang chủ
        self.home_button = create_menu_button(
            "home", "Trang chủ", "https://www.youtube.com"
        )
        # YouTube
        self.youtube_button = create_menu_button(
            "youtube", "YouTube", "https://www.youtube.com"
        )
        # Udemy
        self.udemy_button = create_menu_button(
            "udemy", "Udemy", "https://www.udemy.com"
        )
        # Deeplearning
        self.deeplearning_button = create_menu_button(
            "deeplearning", "DeepLearning", "https://www.deeplearning.ai"
        )
        # Cài đặt
        self.settings_button = create_menu_button("setting", "Cài đặt")
        self.settings_button.clicked.connect(self.show_settings)

        # Add buttons to menu layout
        self.menu_layout.addWidget(self.home_button)
        self.menu_layout.addWidget(self.youtube_button)
        self.menu_layout.addWidget(self.udemy_button)
        self.menu_layout.addWidget(self.deeplearning_button)
        self.menu_layout.addWidget(self.settings_button)
        self.menu_layout.addStretch(1)  # Đẩy các buttons lên trên

        # Add menu layout to left panel
        left_layout.addLayout(self.menu_layout)

        # Right column (content area)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Web view
        self.web_view = QWebEngineView()
        right_layout.addWidget(self.web_view)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set initial sizes (left: 150px cố định, right: phần còn lại)
        # Vì left_panel.setFixedWidth(150), nên kích thước này sẽ được giữ nguyên

        # Add splitter to main widget layout
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Bỏ margin cho main layout
        self.main_layout.addWidget(splitter)

    def log_message(self, message):
        """Thêm message vào log area"""
        self.setup_log.append(f"[{self.get_current_time()}] {message}")
        logger.info(message)

    def get_current_time(self):
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    def start_backend_setup(self):
        """Bắt đầu quá trình cài đặt và khởi động backend"""

        self.log_message("Bắt đầu cài đặt backend...")

        self.setup_thread = BackendSetupWorker()
        self.setup_thread.progress.connect(self.update_progress)
        self.setup_thread.status.connect(self.update_status)
        self.setup_thread.finished.connect(self.on_setup_finished)
        self.setup_thread.start()

        # self.on_setup_finished(True, "Backend đã sẵn sàng")  # Giả lập thành công

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

    def switch_to_main_interface(self):
        """Chuyển sang giao diện chính"""
        self.setup_widget.setVisible(False)
        self.main_widget.setVisible(True)
        self.load_youtube()

    def load_youtube(self):
        """Tải YouTube trong web view"""
        self.load_url("https://www.youtube.com")

    def load_url(self, url):
        """Tải URL trong web view"""
        # Loại bỏ khoảng trắng thừa nếu có
        clean_url = url.strip()
        self.web_view.load(QUrl(clean_url))

    def refresh_web_view(self):
        """Làm mới web view"""
        self.web_view.reload()

    def show_settings(self):
        """Hiển thị cài đặt"""
        # Placeholder for settings functionality
        QMessageBox.information(
            self, "Cài đặt", "Tính năng cài đặt sẽ được triển khai sau"
        )

    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        self.log_message("Đang đóng ứng dụng...")
        # backend_manager.stop_backend()
        event.accept()


def create_main_window():
    """Factory function để tạo main window"""
    return MainWindow()
