import sys
import logging
import argparse
import os
from PySide6.QtWidgets import QApplication

from vat.ui.app import VideoAnnotationApp
from vat.utils.resources import configure_opencv_ffmpeg, configure_pydub_ffmpeg


def main():
    parser = argparse.ArgumentParser(description="Video Annotation Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", type=str, help="Log file path")
    args = parser.parse_args()
    # Always enable file logging to a default path so the in-app viewer works
    log_level = logging.DEBUG if args.debug else logging.INFO
    default_log_dir = os.path.expanduser("~/.videooralannotation")
    try:
        os.makedirs(default_log_dir, exist_ok=True)
    except Exception:
        pass
    log_file_path = args.log_file or os.path.join(default_log_dir, "app.log")
    handlers = [logging.FileHandler(log_file_path)]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    logging.info("Starting Video Annotation Tool (PySide6 version)")
    configure_opencv_ffmpeg()
    configure_pydub_ffmpeg()
    # Graceful exit on macOS: project does not officially support macOS runtime
    if sys.platform == "darwin" and os.environ.get("VAT_ALLOW_MAC") != "1":
        logging.error("macOS is not officially supported. Please use Windows (recommended) or Linux.")
        print("Video Annotation Tool: macOS is not officially supported. Set VAT_ALLOW_MAC=1 to run anyway.")
        sys.exit(64)
    app = QApplication(sys.argv)
    app.setApplicationName("Video Annotation Tool")
    window = VideoAnnotationApp()
    try:
        # Provide log file path to the in-app viewer regardless of CLI flags
        window.log_file_path = log_file_path
    except Exception:
        pass
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
