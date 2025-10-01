# Video Annotation Tool for Linguistic Fieldwork

A simple and robust video annotation tool designed to streamline data collection and analysis for linguistic fieldwork.

Download the latest build for Windows (x64) [here](https://drive.google.com/file/d/1Cos0r0hxpJkkUguE0EgueQcGlUY7-u3b/view?usp=sharing).

## About the Project

This application provides a user-friendly graphical interface for linguists and researchers to manage video and audio data. It is built to assist in the tedious but critical task of transcribing and annotating oral data.

The tool allows users to select a folder of video files, play them back, and record synchronized audio annotations. It includes features for organizing, managing, and exporting audio files, with native support for workflows common in linguistic research.

## Key Features

  * **Synchronous Video Playback & Audio Recording:** Record audio annotations while watching video playback.
  * **Intuitive User Interface:** A simple, easy-to-use interface built with `tkinter`.
  * **Multi-language Support:** The application's interface is available in multiple languages, including English, Bahasa Indonesia, 한국어 (Korean), Nederlands, Português (Brasil), Español (Latinoamérica), and Afrikaans.
  * **Linguistic Software Integration:** Seamlessly export all audio annotations into a single file for use in software like **SayMore** or **ELAN**, or open them directly in **Ocenaudio** for advanced editing.
  * **Metadata Management:** Easily create and edit a `metadata.txt` file for each project, ensuring your data is well-documented.
  * **Audio File Management:** Import, export, and clear recorded `.wav` files with a single click.

## Getting Started

### Prerequisites

  * **Python 3.11**: This script is specifically built and tested for Python 3.11. **It will not work with Python 3.12 or higher** due to compatibility issues with some dependencies.
  * **FFmpeg**: You must have FFmpeg installed and in your system's PATH. You can download it from the official [FFmpeg website](https://ffmpeg.org/download.html).

### Installation

1.  Clone this repository to your local machine:
    ```bash
    git clone https://github.com/rulingAnts/videoannotationtool.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd videoannotationtool
    ```
3.  Install the required Python libraries. It is highly recommended to use a virtual environment.
    ```bash
    pip install opencv-python Pillow pyaudio pydub numpy
    ```

## Usage

1.  Run the application from your terminal:
    ```bash
    python3.11 videoannotation.py
    ```
2.  Click the **"Select Folder"** button to choose a directory containing your video files.
3.  Select a video from the list on the left.
4.  Use the video and audio controls on the right to play the video, record audio, and manage your annotations.
5.  Edit project metadata using the text box on the left, and remember to click **"Save"**.
6.  Use the various export buttons to manage your audio data and prepare it for further analysis.

## Contributing

We welcome contributions from the community\! If you encounter a bug, have a feature request, or would like to contribute code, please follow our [CONTRIBUTING.md](https://www.google.com/search?q=CONTRIBUTING.md) guidelines.

## License

This software is released under the **GNU Affero General Public License, Version 3 (AGPL-3.0)**. The AGPL is a strong copyleft license that ensures the freedom of the software for all users. Any modifications or derivative works must also be licensed under the same terms, guaranteeing that this project will always remain free and open for the benefit of the linguistic community.

A copy of the full license text can be found in the [LICENSE](https://www.google.com/search?q=LICENSE) file.

## Acknowledgments

  * Built using the following fantastic open-source libraries: `opencv-python`, `Pillow`, `pyaudio`, `pydub`, and `numpy`.
  * The project benefits from a global perspective, thanks to contributions of the following language translations: Bahasa Indonesia, 한국어, Nederlands, Português, Español, and Afrikaans.
