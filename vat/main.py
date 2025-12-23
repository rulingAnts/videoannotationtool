import sys
import logging
import argparse
from PySide6.QtWidgets import QApplication

from vat.ui.app import VideoAnnotationApp
from vat.utils.resources import configure_opencv_ffmpeg, configure_pydub_ffmpeg


def main():
    parser = argparse.ArgumentParser(description="Video Annotation Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", type=str, help="Log file path")
    args = parser.parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_handlers = []
    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))
    if args.debug:
        log_handlers.append(logging.StreamHandler(sys.stdout))
    if log_handlers:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=log_handlers
        )
    logging.info("Starting Video Annotation Tool (PySide6 version)")
    configure_opencv_ffmpeg()
    configure_pydub_ffmpeg()
    app = QApplication(sys.argv)
    app.setApplicationName("Video Annotation Tool")
    window = VideoAnnotationApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
