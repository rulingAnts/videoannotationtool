# Contributing to the Visual Stimulus Kit Tool

We welcome and appreciate all contributions to the Visual Stimulus Kit Tool\! Your help is vital to making this project better for everyone. By contributing, you agree to abide by the project's [Code of Conduct](https://www.google.com/search?q=CODE_OF_CONDUCT.md) and license.

## How Can I Contribute?

There are many ways to contribute, not just by writing code.

### Reporting Bugs

Encountered an issue? The best way to help is to file a detailed bug report.

1.  Check the [issue tracker](https://www.google.com/search?q=https://github.com/rulingAnts/videoannotationtool/issues) to see if the bug has already been reported.
2.  If not, open a new issue.
3.  In your report, please include:
      * A clear, descriptive title.
      * The steps to reproduce the bug.
      * Your operating system (e.g., macOS, Windows).
      * Your Python version (e.g., `python3.11 --version`).
      * The expected behavior vs. the actual behavior.

### Suggesting Enhancements

Have an idea for a new feature or an improvement to an existing one? We'd love to hear it\! Open an issue to discuss your ideas. Please explain why the enhancement would be useful and, if you have any thoughts on how it could be implemented, include them.

### Code Contributions

Ready to make a code change? Here is the standard workflow to get your changes into the project.

#### 1\. Fork the Repository

Start by creating a copy of the project on your GitHub account.

#### 2\. Clone Your Fork

Clone your forked repository to your local machine using the command line.

```bash
git clone https://github.com/your-username/videoannotationtool.git
```

#### 3\. Create a New Branch

Create a new branch for your work. Use a descriptive name that indicates whether it's a new feature or a bug fix.

```bash
git checkout -b feature/my-new-feature
# OR
git checkout -b bugfix/fix-that-bug
```

#### 4\. Make Your Changes

Make the necessary changes to the code. Before submitting, please ensure your code adheres to a standard Python style (e.g., [PEP 8](https://peps.python.org/pep-0008/)).

#### 5\. Commit Your Changes

Commit your changes with a clear and concise message. A good commit message summarizes the change in a single line.

```bash
git commit -m "feat: Add new language support for Bahasa Indonesia"
# OR
git commit -m "fix: Correct bug that prevented video playback on Windows"
```

#### 6\. Push to Your Fork

Push your new branch to your forked repository on GitHub.

```bash
git push origin <your-branch-name>
```

#### 7\. Submit a Pull Request (PR)

Go to your fork's page on GitHub and open a pull request. Provide a detailed description of your changes, explaining what you did and why. Your PR will be reviewed, and we will work with you to merge it into the main project.

-----

## Proposing a Major New Feature: Android App for Informants

The current version of this tool is designed for linguists on a computer. We have a vision for a major new feature that would empower native speakers to directly contribute to a research project with minimal technical overhead.

This new project would be a **standalone Android app** designed for a native-speaking informant. The goal is to make it as simple as possible for a user with limited tech savvy to record and submit video descriptions.

**Key Requirements for the Android App:**

  * **Zero-Configuration for the Informant:** The user should not have to manually configure cloud services, set folder locations, or manage files. All settings should be pre-configured by the researcher.
  * **Researcher-Bundled Content:** The researcher should be able to bundle a set of videos and configuration settings (e.g., Google Drive/Dropbox API keys, destination folders) with the app itself. The ideal end product would be a Windows or macOS wizard that creates this pre-configured package.
  * **Easy Interface:** The app should have a large, intuitive interface with clear buttons for watching a video and recording an audio description.
  * **Automated Uploads:** The app should automatically handle the upload of recordings to the designated cloud service without the user needing to manually log in or transfer files.
  * **Privacy and Non-Overwriting:** The app should use a user ID or device ID to ensure recordings are not overwritten by another user with the same app, providing a simple form of data protection and organization.

We are looking for a collaborator or a team to help us bring this vision to life. If you have experience with **Android development (Java/Kotlin)**, **cloud storage APIs (Google Drive, Dropbox)**, or **desktop GUI wizards (Python/Qt)**, please reach out by opening a new issue to discuss this proposal.

## Adding New Languages

If you want to add a new language, please create a new dictionary entry in the `LABELS_ALL` variable, formatted just like the existing ones. The key should be the language name in English, and the `language_name` value should be in the native language.

Thank you for your valuable contribution\!