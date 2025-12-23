import os
import numpy as np
from pydub import AudioSegment
from PySide6.QtCore import QObject, Signal

class JoinWavsWorker(QObject):
    finished = Signal()
    error = Signal(str)
    success = Signal(str)

    def __init__(self, folder_path: str, output_file: str):
        super().__init__()
        self.folder_path = folder_path
        self.output_file = output_file

    def generate_click_sound_pydub(self, duration_ms: int, freq: int, rate: int):
        t = np.linspace(0, duration_ms / 1000, int(rate * duration_ms / 1000), endpoint=False)
        sine_wave = np.sin(2 * np.pi * freq * t)
        decay = np.linspace(1, 0, len(sine_wave))
        click_data = sine_wave * decay
        click_data = (click_data * 0.5 * (2**15 - 1)).astype(np.int16).tobytes()
        return AudioSegment(
            data=click_data,
            sample_width=2,
            frame_rate=rate,
            channels=1
        )

    def run(self):
        try:
            wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
            wav_files.sort()
            std_rate = 44100
            std_channels = 1
            std_sample_width = 2
            silence_segment = AudioSegment.silent(duration=500, frame_rate=std_rate)
            click_sound = self.generate_click_sound_pydub(duration_ms=5, freq=2000, rate=std_rate)
            click_segment = silence_segment + click_sound + silence_segment
            combined_audio = AudioSegment.empty()
            combined_audio = combined_audio.set_frame_rate(std_rate).set_channels(std_channels).set_sample_width(std_sample_width)
            for i, file in enumerate(wav_files):
                file_path = os.path.join(self.folder_path, file)
                audio = AudioSegment.from_file(file_path, format="wav")
                if audio.frame_rate != std_rate:
                    audio = audio.set_frame_rate(std_rate)
                if audio.channels != std_channels:
                    audio = audio.set_channels(std_channels)
                if audio.sample_width != std_sample_width:
                    audio = audio.set_sample_width(std_sample_width)
                combined_audio += audio
                if i < len(wav_files) - 1:
                    combined_audio += click_segment
            combined_audio.export(self.output_file, format="wav")
            self.success.emit(self.output_file)
        except Exception as e:
            self.error.emit(f"An error occurred while joining files:\n{e}")
        finally:
            self.finished.emit()
