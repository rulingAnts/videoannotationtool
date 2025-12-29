# Visual Stimulus Kit Tool for Linguistic Fieldwork

A simple and robust tool for working with visual stimulus kits, designed to streamline data collection and analysis for linguistic fieldwork.

Download the latest portable build for Windows (x64) [here](https://github.com/rulingAnts/videoannotationtool/releases/latest). 
This runs right out of the download folder without any further installation or setup necessary.

## About the Project

This application provides a user-friendly graphical interface for linguists and researchers to manage video and audio data. It is built to assist in the tedious but critical task of transcribing and annotating oral data.

The tool allows users to select a folder of video files, play them back, and record synchronized audio annotations. It includes features for organizing, managing, and exporting audio files, with native support for workflows common in linguistic research.

## Key Features

  * **Synchronous Video Playback & Audio Recording:** Record audio annotations while watching video playback.
  * **Intuitive User Interface:** A simple, easy-to-use interface built with `PySide6` (Qt for Python).
  * **Multi-language Support:** The application's interface is available in multiple languages, including English, Bahasa Indonesia, 한국어 (Korean), Nederlands, Português (Brasil), Español (Latinoamérica), and Afrikaans.
  * **Linguistic Software Integration:** Seamlessly export all audio annotations into a single file for use in software like [**SayMore**](https://software.sil.org/saymore/) or [**ELAN**](https://archive.mpi.nl/tla/elan/download), or open them directly in [**Ocenaudio**](https://www.ocenaudio.com/) for advanced editing _(the app also generates clicks between each individual oral annotations in the combined audio file for clarity when segmenting and transcribing)_.
  * **Metadata Management:** Easily create and edit a `metadata.txt` file for each project, ensuring your data is well-documented.
  * **Audio File Management:** Import, export, and clear recorded `.wav` files with a single click.

---

## Usage and Recommended Stimulus Kits

To get started quickly, you can use established, cross-culturally validated **video stimulus materials**. Simply download a kit, place the video files in a folder, and load that folder into the application using the **"Select Folder"** button.

1. Click the "Select Folder" button to choose a directory containing your video files.
  
2. Select a video from the list on the left.
  
3. Use the video and audio controls on the right to play the video, record audio, and manage your annotations.
  
4. Edit project metadata using the text box on the left, and remember to click "Save".
  
5. Use the various export buttons to manage your audio data and prepare it for further analysis.
  

### General Stimulus Kits (Max Planck Institute for Psycholinguistics)

These kits include video files widely used for the elicitation of verbal behavior and semantics:

- **MPI Field Manuals and Stimulus Materials:** A repository of fieldwork manuals and stimulus materials, including many sets of video stimuli. *Free registration is often required for access.*
  
  - **Link:** [https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_00_0000_0000_0021_DC42_E](https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_00_0000_0000_0021_DC42_E)

- **MPI Staged Event Videos:** A series of video sets designed to explore features of event representation in the language of study, in particular, multi-verb constructions, event typicality, and event complexity.. (highly recommended for languages with serial verbs and clause chaining)
  
  - **Link:** [https://hdl.handle.net/1839/becc2150-e760-4270-aa0b-481511f88f1b](https://hdl.handle.net/1839/becc2150-e760-4270-aa0b-481511f88f1b)

- **The Pear Story:** A famous, silent 6-minute video designed to elicit narrative discourse, often used to study grammar, narrative structure, and reference tracking. The video file can be downloaded and used directly.
  
  - **Link:** [https://hdl.handle.net/1839/00-0000-0000-0015-690E-8](https://hdl.handle.net/1839/00-0000-0000-0015-690E-8)

### Kits for Participant Reference & Case Alignment

For researchers focusing on grammar, case systems, and how participants are introduced and tracked in discourse (e.g., switch reference, zero anaphora, ergativity, pronouns), these resources include ready-to-use video clips:

- **Cut and Break Clips:** A stimulus set of short video clips designed to elicit descriptions of cutting, breaking, and related events, which often prompt the use of different case/alignment patterns and argument structure.
  
  - **Resource Link (Includes video files):** [https://hdl.handle.net/1839/9271a14b-a214-419f-a968-3e7fc9bad5fa](https://hdl.handle.net/1839/9271a14b-a214-419f-a968-3e7fc9bad5fa)
- **Caused Positions:** A set of video stimuli for eliciting descriptions of caused motion and placement events, useful for investigating transitivity and argument roles.
  
  - **Resource Link (Includes video files):** [https://hdl.handle.net/1839/a43eb64c-cf57-4461-b6a7-d6512f5f8d84](https://hdl.handle.net/1839/a43eb64c-cf57-4461-b6a7-d6512f5f8d84)

---

## Getting Started

For most users, we highly recommend using the **portable build for Windows (x64)** linked at the top of this page.

## For Developers & Contributors (Installing from Source):

### Prerequisites

  * **Python 3.11+**: This application is built for Python 3.11 and newer (tested with 3.11 and 3.12). The UI has been migrated from Tkinter to PySide6 for improved stability on macOS and Windows.
  * **FFmpeg**: You must have FFmpeg installed and in your system's PATH. You can download it from the official [FFmpeg website](https://ffmpeg.org/download.html).
  * **System dependencies (Linux)**: On Linux, you may need to install additional packages for Qt/PySide6:
    ```bash
    # Ubuntu/Debian
    sudo apt-get install libgl1-mesa-glx libegl1 libxkbcommon-x11-0
    
    # For audio support
    sudo apt-get install portaudio19-dev
    ```

### Installation

1.  **Clone this repository to your local machine:**
    ```bash
    git clone https://github.com/rulingAnts/videoannotationtool.git
    cd videoannotationtool
    ```

2.  **Install Python Libraries:** It is *highly recommended* to use a virtual environment.
    ```bash
    # Create the virtual environment
    python3.11 -m venv venv
    
    # Activate the environment (Windows)
    .\venv\Scripts\activate
    
    # Activate the environment (Linux/macOS)
    source venv/bin/activate
    
    # Install the required packages
    pip install -r requirements.txt
    ```

3.  **Run the application from your terminal:**
    ```bash
    python3.11 videoannotation.py
    ```

## Usage

1.  Run the application from your terminal (or double-click the portable app "Video Annotation Tool.exe"):
    ```bash
    python3.11 videoannotation.py
    ```
2.  Click the **"Select Folder"** button to choose a directory containing your video files.
3.  Select a video from the list on the left.
4.  Use the video and audio controls on the right to play the video, record audio, and manage your annotations.
5.  Edit project metadata using the text box on the left, and remember to click **"Save"**.
6.  Use the various export buttons to manage your audio data and prepare it for further analysis.

### Troubleshooting: Tabs not refreshing together

If the Images or Videos tab shows stale content or doesn't update after changing folders:

- Use the new "Refresh Images" button (on the right side of the Images banner) to force a rebuild of the image grid.
- Make sure the folder name shown under the language selector matches the folder you selected; hover over it to see the full path tooltip.
- From the Tasks panel, you can run "Reset: App Settings" to clear saved state (last folder, language, etc.) if settings persist an old folder.
- Running the app in debug mode ("Run: App (Debug + Log)") will show lines like `refresh_all_media` and `Found N images / M videos` with the exact folder path being used, which helps confirm both tabs are loading from the same folder.

## 🚀 Call for Contributors: Windows Installer Development

Currently, the portable build is large and must be manually updated (and also looks slightly sketchy). We are looking for contributors to help us develop a professional, small-footprint Windows Installer.

This new installer will be a **Bootstrapper** (or **Network Installer**). It will be tiny (under 1MB) and will automatically perform all installation steps for the user:

1.  **Download and Install** the correct Python 3.11 interpreter into the application folder.
2.  **Download and Install** all Python dependencies (from PyPI) using `pip`.
3.  **Create** a Start Menu shortcut.

This is a high-priority task that will make the tool much easier for linguists to use! Please see **Issue #1** (or the top-pinned issue) for full details on how to contribute to this effort.

We welcome contributions from the community\! If you encounter a bug, have a feature request, or would like to contribute code, please follow our [CONTRIBUTING.md](https://github.com/rulingAnts/videoannotationtool?tab=contributing-ov-file) guidelines.


## 🚀 Call for Contributors: macOS Installer Optimization

For macOS, the goal is to create a small, efficient, and professional **drag-and-drop `.app` bundle** that is under GitHub's 25MB limit.

Standard macOS packaging tools like PyInstaller bundle the entire Python runtime and all large dependencies, which results in a file too large for GitHub releases.

**Goal:** Create a thin **PyInstaller/py2app**-based `.app` bundle (under 25MB) that runs a custom shell script on the first launch to download the bulk of the required dependencies (like pre-compiled libraries or the specific Python 3.11 environment) and place them into the application's resources folder.

This will involve:

1. **Selecting an App-Bundling Tool:** Using **PyInstaller** or **py2app** to create the initial `.app` structure.
2. ****Developing the Download Logic:** Writing a **Shell Script** or a small Python bootstrap script that, upon first run, uses `curl` or `wget` to download a single, large compressed file of pre-compiled dependencies from an external host (e.g., GitHub LFS, a CDN, or even a different GitHub Release asset).

1. **Self-Extraction:** The script must then un-zip and install these files into the correct location inside the `.app` package content, making the application fully functional.
  
2. **Creating the DMG:** Building a final, professional `.dmg` (Disk Image) for distribution.

## ⚖️ Licensing

Copyright © 2025 Seth Johnston

This software is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see https://www.gnu.org/licenses/.


## Third-Party Libraries

This project includes pre-built binaries of FFmpeg, distributed by **BtbN/FFmpeg-Builds**.

FFmpeg is a suite of libraries and programs for handling video, audio, and other multimedia files and streams, licensed primarily under the GNU Lesser General Public License (LGPL) version 2.1 or later, or the GNU General Public License (GPL) version 2 or later, depending on the enabled components.

### FFmpeg License and Source Code Distribution

In compliance with the (L)GPL license, we are providing the complete corresponding source code for the FFmpeg binaries included in this distribution.

* **FFmpeg Binary Source (BitBn Build):**
    * **Included Archive:** `BitBn_FFmpeg_Source_Code.zip`
    * **Original Source:** [Link to the specific BitBn/FFmpeg-Builds release page you used, e.g., `https://github.com/BtbN/FFmpeg-Builds/releases/tag/v6.1.1-latest-20231011`]

* **Attribution Notice:**
    > This software uses code of [FFmpeg](http://ffmpeg.org/) licensed under the **LGPLv2.1** and/or **GPLv2** (depending on the build variant) and its source code is available in the provided `BitBn_FFmpeg_Source_Code.zip` archive (with the [latest release](https://github.com/rulingAnts/videoannotationtool/releases/latest)).

* **License Text:**
    > A copy of the GNU Lesser General Public License, version 2.1, and the GNU General Public License, version 2, are included in the source code archive and should be read for full compliance details.

***Disclaimer:*** *This information is for license compliance purposes and does not constitute legal advice. Please consult a legal professional for complete licensing guidance.*


## 🌟 Acknowledgments

This project, and related tools, owe their existence to an **AI-first development methodology**, leveraging Large Language Models (LLMs) for the vast majority of coding and architecture.

* **AI Development Leads:** **Grok (xAI)**, with significant contributions from **ChatGPT (OpenAI)** and **Gemini (Google)**, all under the final direction and troubleshooting of the human developer.

* **Localization:** Interface translations (Bahasa Indonesia, 한국어, Nederlands, Português, Español, and Afrikaans) were also generated by **Gemini** to support a global audience.

* **Built With:** The application relies on the following essential open-source libraries and the foundational **Python Standard Library** (e.g., `os`, `json`, `threading`):
    * **UI Framework:** `PySide6` (Qt for Python)
    * **Multimedia & Processing:** `opencv-python`, `Pillow`, `pydub`, `pyaudio`, `numpy`

## Code Structure (modular)

The app has been reorganized into a small Python package for clarity and maintainability:

- `vat/main.py`: CLI and application bootstrap
- `vat/ui/app.py`: `VideoAnnotationApp` and interface labels (currently English)
- `vat/audio/recording.py`: background audio recording worker
- `vat/audio/playback.py`: background audio playback worker
- `vat/audio/joiner.py`: WAV concatenation worker with click markers
- `vat/utils/resources.py`: `resource_path` and FFmpeg environment configuration

### Run

Use Python 3.11 to run the modular entrypoint:

```bash
python3.11 -m vat.main
```

VS Code tasks include "Run: App (Modular)".
