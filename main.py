import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication


# Configure logging
def setup_logging():
    """Thiết lập logging với thư mục tồn tại"""
    try:
        # Xác định thư mục log
        app_data_dir = Path(os.getenv("APPDATA", "."))
        log_dir = app_data_dir / "ai_dubbing"

        # Tạo thư mục nếu chưa tồn tại
        log_dir.mkdir(parents=True, exist_ok=True)

        # Đường dẫn file log
        log_file = log_dir / "app.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, mode="a", encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
            force=True,  # Ghi đè cấu hình logging hiện tại nếu có
        )

        logger = logging.getLogger(__name__)
        logger.info(f"Logging setup completed. Log file: {log_file}")
        return logger

    except Exception as e:
        # Fallback: chỉ log ra console nếu không thể tạo file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )

        logger = logging.getLogger(__name__)
        logger.warning(f"Could not setup file logging: {e}")
        return logger


def main():
    """Main application entry point"""
    # Setup logging trước
    logger = setup_logging()
    logger.info("Starting AI Video Dubbing Application")

    # Đặt attribute trước khi tạo QApplication
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("AI Video Dubbing")
    app.setApplicationVersion("1.0.0")

    try:
        # Import and create main window
        from ui.main_window import create_main_window

        window = create_main_window()
        window.show()

        # Run application
        logger.info("Application started successfully")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback

        traceback.print_exc()

        # Show error dialog
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None, "Lỗi khởi động", f"Không thể khởi động ứng dụng: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
