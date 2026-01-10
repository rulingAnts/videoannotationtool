import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse
import os
from PySide6.QtWidgets import QApplication

# Allow running this file directly (e.g., `python /path/to/vat/main.py`) by
# ensuring the repository root is on sys.path so `import vat...` works.
try:
    from vat.ui.app import VideoAnnotationApp
    from vat.utils.resources import configure_opencv_ffmpeg, configure_pydub_ffmpeg
except ModuleNotFoundError as e:
    if e.name == 'vat':
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from vat.ui.app import VideoAnnotationApp
        from vat.utils.resources import configure_opencv_ffmpeg, configure_pydub_ffmpeg
    else:
        raise


def main():
    parser = argparse.ArgumentParser(description="Visual Stimulus Kit Tool")
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
    class YamlFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            # ISO timestamp
            ts = self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z")
            def esc(s: str) -> str:
                try:
                    s = str(s)
                except Exception:
                    s = ""
                # escape single quotes for YAML single-quoted scalars
                return s.replace("'", "''")
            msg = esc(record.getMessage())
            name = esc(record.name)
            module = esc(record.module)
            func = esc(record.funcName)
            level = esc(record.levelname)
            line = record.lineno if isinstance(record.lineno, int) else 0
            # inline YAML mapping to keep one line per entry
            return (
                f"{{ts: '{ts}', level: '{level}', logger: '{name}', module: '{module}', func: '{func}', line: {line}, msg: '{msg}'}}"
            )

    file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(YamlFormatter())
    handlers = [file_handler]
    if args.debug:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(YamlFormatter())
        handlers.append(stream_handler)
    logging.basicConfig(level=log_level, handlers=handlers)
    logging.info("Starting Visual Stimulus Kit Tool (PySide6 version)")
    configure_opencv_ffmpeg()
    configure_pydub_ffmpeg()
    app = QApplication(sys.argv)
    app.setApplicationName("Visual Stimulus Kit Tool")
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
