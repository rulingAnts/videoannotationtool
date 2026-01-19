import os
import tempfile
import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal


class ImageConvertWorker(QThread):
    finished = Signal(str)   # dst_path
    error = Signal(str)      # message
    canceled = Signal()      # canceled (not used, for parity)

    def __init__(self, src_path: str, dst_path: str):
        super().__init__()
        self.src_path = src_path
        self.dst_path = dst_path
        self.output_path: Optional[str] = None
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _convert_with_pillow(self, src: str, tmp_out: str) -> bool:
        try:
            from PIL import Image
            # Apply EXIF orientation so portrait images don't appear rotated
            try:
                from PIL import ImageOps
            except Exception:
                ImageOps = None
            try:
                import pillow_heif
                try:
                    pillow_heif.register_heif_opener()
                except Exception:
                    pass
            except Exception:
                pass
            im = Image.open(src)
            # Normalize mode
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            elif im.mode == "RGBA":
                im = im.convert("RGB")
            try:
                if ImageOps is not None:
                    im = ImageOps.exif_transpose(im)
            except Exception:
                pass
            im.save(tmp_out, format="JPEG", quality=92, subsampling="4:2:0", optimize=True)
            return os.path.getsize(tmp_out) > 0
        except Exception as e:
            try:
                logging.debug(f"ImageConvertWorker.pillow failed: {e}")
            except Exception:
                pass
            return False

    def _convert_with_qimage(self, src: str, tmp_out: str) -> bool:
        try:
            from PySide6.QtGui import QImage, QImageReader
            # Respect EXIF orientation via auto transform
            rdr = QImageReader(src)
            try:
                rdr.setAutoTransform(True)
            except Exception:
                pass
            qimg = rdr.read()
            if qimg.isNull():
                raise RuntimeError("QImage failed to load")
            if qimg.hasAlphaChannel():
                qimg = qimg.convertToFormat(QImage.Format_RGB888)
            if not qimg.save(tmp_out, "JPG"):
                raise RuntimeError("QImage save failed")
            return os.path.getsize(tmp_out) > 0
        except Exception as e:
            try:
                logging.debug(f"ImageConvertWorker.qimage failed: {e}")
            except Exception:
                pass
            return False

    def _convert_with_opencv(self, src: str, tmp_out: str) -> bool:
        try:
            import cv2
            img = cv2.imread(src, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise RuntimeError("OpenCV read failed")
            if len(img.shape) == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            ok = cv2.imwrite(tmp_out, img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            return ok and os.path.getsize(tmp_out) > 0
        except Exception as e:
            try:
                logging.debug(f"ImageConvertWorker.opencv failed: {e}")
            except Exception:
                pass
            return False

    def run(self):
        try:
            src = self.src_path
            dst = self.dst_path
            if not src or not os.path.exists(src):
                self.error.emit("Source image missing")
                return
            folder = os.path.dirname(dst) or os.getcwd()
            fd, tmp_out = tempfile.mkstemp(suffix=".jpg", dir=folder)
            os.close(fd)
            try:
                ok = self._convert_with_pillow(src, tmp_out)
                if not ok:
                    # macOS system fallback for HEIC via sips
                    try:
                        import subprocess
                        if os.name == 'posix' and os.path.exists('/usr/bin/sips'):
                            rc = subprocess.run(['/usr/bin/sips', '-s', 'format', 'jpeg', src, '--out', tmp_out], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            ok = (rc.returncode == 0) and os.path.getsize(tmp_out) > 0
                            if not ok:
                                logging.debug(f"ImageConvertWorker.sips failed: rc={rc.returncode}, err={(rc.stderr or b'').decode()[:200]}")
                    except Exception as e:
                        try:
                            logging.debug(f"ImageConvertWorker.sips exception: {e}")
                        except Exception:
                            pass
                if not ok:
                    ok = self._convert_with_qimage(src, tmp_out)
                if not ok:
                    ok = self._convert_with_opencv(src, tmp_out)
                if not ok:
                    raise RuntimeError("All image conversion methods failed")
                # Validate decodability
                try:
                    from PySide6.QtGui import QImageReader
                    rdr = QImageReader(tmp_out)
                    try:
                        rdr.setAutoTransform(True)
                    except Exception:
                        pass
                    test = rdr.read()
                    if test is None or test.isNull():
                        raise RuntimeError("Output not decodable")
                except Exception as e:
                    raise e
                os.replace(tmp_out, dst)
                self.output_path = dst
                self.finished.emit(dst)
            finally:
                try:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)
                except Exception:
                    pass
        except Exception as e:
            try:
                logging.error(f"ImageConvertWorker: {e}")
            except Exception:
                pass
            self.error.emit(str(e))
