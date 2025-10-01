# Video Annotation Tool for Linguistic Fieldwork

A simple and robust video annotation tool designed to streamline data collection and analysis for linguistic fieldwork.

Download the latest portable build for Windows (x64) [here](https://drive.google.com/file/d/1Cos0r0hxpJkkUguE0EgueQcGlUY7-u3b/view?usp=sharing).

## About the Project

This application provides a user-friendly graphical interface for linguists and researchers to manage video and audio data. It is built to assist in the tedious but critical task of transcribing and annotating oral data.

The tool allows users to select a folder of video files, play them back, and record synchronized audio annotations. It includes features for organizing, managing, and exporting audio files, with native support for workflows common in linguistic research.

## Key Features

  * **Synchronous Video Playback & Audio Recording:** Record audio annotations while watching video playback.
  * **Intuitive User Interface:** A simple, easy-to-use interface built with `tkinter`.
  * **Multi-language Support:** The application's interface is available in multiple languages, including English, Bahasa Indonesia, 한국어 (Korean), Nederlands, Português (Brasil), Español (Latinoamérica), and Afrikaans.
  * **Linguistic Software Integration:** Seamlessly export all audio annotations into a single file (with generated clicks marking the end of each annotation for clarity) for use in software like [**SayMore**](https://software.sil.org/saymore/) or [**ELAN**](https://archive.mpi.nl/tla/elan/download), or open them directly in [**Ocenaudio**](https://www.ocenaudio.com/) for advanced editing.
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
  
  - **Link:** [https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_00_0000_0000_0021_DC42_E](https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_becc2150_e760_4270_aa0b_481511f88f1b)

- **The Pear Story:** A famous, silent 6-minute video designed to elicit narrative discourse, often used to study grammar, narrative structure, and reference tracking. The video file can be downloaded and used directly.
  
  - **Link:** [https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_becc2150_e760_4270_aa0b_481511f88f1b](https://archive.mpi.nl/mpi/islandora/object/lat%3A1839_becc2150_e760_4270_aa0b_481511f88f1b)

### Kits for Participant Reference & Case Alignment

For researchers focusing on grammar, case systems, and how participants are introduced and tracked in discourse (e.g., switch reference, zero anaphora, ergativity, pronouns), these resources include ready-to-use video clips:

- **Cut and Break Clips:** A stimulus set of short video clips designed to elicit descriptions of cutting, breaking, and related events, which often prompt the use of different case/alignment patterns and argument structure.
  
  - **Resource Link (Includes video files):** [MPI Field Manual Entry for Cut and Break Clips](https://www.google.com/search?q=http://fieldmanuals.mpi.nl/volumes/2001/cut-and-break-clips/)
- **Caused Positions:** A set of video stimuli for eliciting descriptions of caused motion and placement events, useful for investigating transitivity and argument roles.
  
  - **Resource Link (Includes video files):** [MPI Field Manual Entry for Caused Positions](https://www.google.com/search?q=http://fieldmanuals.mpi.nl/volumes/2001/caused-positions/)
- **The CEGS Stimulus Kit for Case Elicitation:** An elicitation toolkit focused on case marking and its acquisition. While primarily picture-based, it can be a valuable guide for designing comparable video stimuli.
  
  - **Resource Link:** [CEGS Elicitation Toolkit](https://www.google.com/search?q=http://academia.edu/794129/CEGS_An_elicitation_took_kit_for_studies_on_case_marking_and_its_acquisition)

---

## Getting Started

### Prerequisites

  * **Python 3.11**: This script is specifically built and tested for Python 3.11. **It will not work with Python 3.12 or higher** due to compatibility issues with some dependencies.
  * **FFmpeg**: You must have FFmpeg installed and in your system's PATH. You can download it from the official [FFmpeg website](https://ffmpeg.org/download.html).

### Installation

For most users, we highly recommend using the **portable build for Windows (x64)** linked at the top of this page.

**For Developers & Contributors (Installing from Source):**

1.  **Clone this repository to your local machine:**
    ```bash
    git clone [https://github.com/rulingAnts/videoannotationtool.git](https://github.com/rulingAnts/videoannotationtool.git)
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

## 🚀 Call for Contributors: Windows Installer Development

Currently, the portable build is large and must be manually updated. We are looking for contributors to help us develop a professional, small-footprint Windows Installer.

This new installer will be a **Bootstrapper** (or **Network Installer**). It will be tiny (under 1MB) and will automatically perform all installation steps for the user:

1.  **Download and Install** the correct Python 3.11 interpreter into the application folder.
2.  **Download and Install** all Python dependencies (from PyPI) using `pip`.
3.  **Create** a Start Menu shortcut.

This is a high-priority task that will make the tool much easier for linguists to use! Please see **Issue #1** (or the top-pinned issue) for full details on how to contribute to this effort.

We welcome contributions from the community\! If you encounter a bug, have a feature request, or would like to contribute code, please follow our [CONTRIBUTING.md](https://www.google.com/search?q=CONTRIBUTING.md) guidelines.


## 🚀 Call for Contributors: macOS Installer Optimization

For macOS, the goal is to create a small, efficient, and professional **drag-and-drop `.app` bundle** that is under GitHub's 25MB limit.

Standard macOS packaging tools like PyInstaller bundle the entire Python runtime and all large dependencies, which results in a file too large for GitHub releases.

**Goal:** Create a thin **PyInstaller/py2app**-based `.app` bundle (under 25MB) that runs a custom shell script on the first launch to download the bulk of the required dependencies (like pre-compiled libraries or the specific Python 3.11 environment) and place them into the application's resources folder.

This will involve:

1. **Selecting an App-Bundling Tool:** Using **PyInstaller** or **py2app** to create the initial `.app` structure.
2. ****Developing the Download Logic:** Writing a **Shell Script** or a small Python bootstrap script that, upon first run, uses `curl` or `wget` to download a single, large compressed file of pre-compiled dependencies from an external host (e.g., GitHub LFS, a CDN, or even a different GitHub Release asset).

1. **Self-Extraction:** The script must then un-zip and install these files into the correct location inside the `.app` package content, making the application fully functional.
  
2. **Creating the DMG:** Building a final, professional `.dmg` (Disk Image) for distribution.


## License

This software is released under the **GNU Affero General Public License, Version 3 (AGPL-3.0)**. The AGPL is a strong copyleft license that ensures the freedom of the software for all users. Any modifications or derivative works must also be licensed under the same terms, guaranteeing that this project will always remain free and open for the benefit of the linguistic community.

A copy of the full license text can be found in the [LICENSE](https://www.google.com/search?q=LICENSE) file.

## Acknowledgments

  * Built using the following fantastic open-source libraries: `opencv-python`, `Pillow`, `pyaudio`, `pydub`, and `numpy`.
  * The project benefits from a global perspective, thanks to contributions of the following language translations: Bahasa Indonesia, 한국어, Nederlands, Português, Español, and Afrikaans.
