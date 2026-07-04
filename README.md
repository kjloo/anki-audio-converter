# 📦 WAV to MP3 Audio Compressor for Anki

A streamlined Anki add-on written in modern Python that scans your decks, converts bloated, space-consuming `.wav` audio card fields into efficient, high-quality `.mp3` files using `ffmpeg`, and automatically rewrites your card field references.

## 🚀 Features

- **Space Saver:** Convert raw audio fields dynamically to optimized `.mp3` tracks.
- **Automatic Reference Relinking:** Rewrites standard `[sound:file.wav]` syntax to `[sound:file.mp3]` safely across notes.
- **Deck-Specific Processing:** Choose target decks through an easy-to-use dropdown menu directly in Anki.
- **Configurable Quality:** Choose your target bitrate parameters inside Anki's native Configuration window.
- **Clean Tooling:** Complete development isolation using `pyenv`, `direnv`, and `Makefile`.

---

## 🛠️ Requirements & Workspace Setup

The project is built around Python 3.13 and relies on a system-level installation of `ffmpeg` to process audio files.

### 1. Prerequisites

Ensure you have Homebrew (on macOS/Linux) or your native system package manager installed.

### 2. Automatic Virtual Environment Setup

This project uses `direnv` to completely automate environment loading through the `.envrc` file.

Install `direnv` (if you haven't already):

```bash
brew install direnv
```

Allow `direnv` access in your cloned project root folder:

```bash
direnv allow
```

> 💡 **What this does:** The `.envrc` file automatically discovers or installs Python 3.13.x via `pyenv`, initializes a dedicated virtual environment, installs system `ffmpeg` dependencies, configures your VS Code interpreter paths, and updates the environment whenever `requirements.txt` changes.

### 3. Quickstart Makefile Commands

For manual orchestration or initial build initialization, run the following commands.

#### Complete Dependencies Provisioning

```bash
make setup
```

Installs system-level `ffmpeg` via Homebrew and updates core Python packages.

#### Package Add-on for Distribution

```bash
make zip
```

Compresses the workspace into a standalone `.ankiaddon` bundle ready to install into Anki.

#### Clear Caches & Temporary Artifacts

```bash
make clean
```

---

## 📖 How to Use

### Installation

1. Run:

   ```bash
   make zip
   ```

2. This generates:

   ```text
   wav_to_mp3_converter.ankiaddon
   ```

3. Open Anki.

4. Navigate to **Tools → Add-ons**.

5. Click **Install from file...** in the upper-right corner.

6. Select the generated `.ankiaddon` file.

7. Restart Anki.

### Running Conversions

1. Inside Anki, open **Tools** from the top menu bar.
2. Select **Batch Compress WAV → MP3**.
3. Choose your desired target deck from the popup selection menu.
4. Let the compressor run. A progress dialog displays the current status, and a completion notification summarizes:
   - Total notes modified
   - Storage space saved

### Adjusting Bitrates

1. Open **Tools → Add-ons**.
2. Select **WAV to MP3 Audio Compressor**.
3. Click **Config**.
4. Modify your desired bitrate, for example:

```json
{
  "target_bitrate": "128k"
}
```

or

```json
{
  "target_bitrate": "192k"
}
```

The default output bitrate is **128k**.
