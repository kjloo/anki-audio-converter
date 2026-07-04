import os
import re
import subprocess
from anki.hooks import addHook
from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import showInfo, showWarning, qconnect
from aqt.editor import Editor

# Regex matching standard Anki audio hooks: [sound:example.wav]
AUDIO_REGEX = re.compile(r"\[sound:([^\]]+\.wav)\]", re.IGNORECASE)

def get_ffmpeg_path() -> str:
    """Fallback search routing for system installations of ffmpeg."""
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]:
        if subprocess.run(["which", path], capture_output=True).returncode == 0:
            return path
    return "ffmpeg"

def convert_wav_to_mp3(media_dir: str, wav_filename: str, bitrate: str) -> str | None:
    """Invokes ffmpeg to safely transcode targets to mp3 files."""
    wav_path = os.path.join(media_dir, wav_filename)
    if not os.path.exists(wav_path):
        return None

    mp3_filename = os.path.splitext(wav_filename)[0] + ".mp3"
    mp3_path = os.path.join(media_dir, mp3_filename)

    ffmpeg_bin = get_ffmpeg_path()
    
    cmd = [ffmpeg_bin, "-y", "-i", wav_path, "-b:a", bitrate, mp3_path]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        if os.path.exists(wav_path):
            os.remove(wav_path)
        return mp3_filename
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def process_editor_card(editor: Editor):
    """Converts audio files for the note currently open in the card editor."""
    note = editor.note
    if not note:
        showWarning("No active note found in the editor.")
        return

    config = mw.addonManager.getConfig(__name__) or {"target_bitrate": "128k"}
    bitrate = config.get("target_bitrate", "128k")
    media_dir = mw.col.media.dir()
    
    note_changed = False
    converted_files_count = 0

    # Read current editor field values before processing
    for i, field_value in enumerate(note.fields):
        matches = AUDIO_REGEX.findall(field_value)
        if not matches:
            continue

        for wav_file in matches:
            new_mp3 = convert_wav_to_mp3(media_dir, wav_file, bitrate)
            if new_mp3:
                field_value = field_value.replace(f"[sound:{wav_file}]", f"[sound:{new_mp3}]")
                note.fields[i] = field_value
                note_changed = True
                converted_files_count += 1

    if note_changed:
        # Update the editor UI fields visually right away
        editor.loadNoteKeepFocus()
        showInfo(f"Conversion Complete!\nSuccessfully optimized {converted_files_count} audio files on this card.")
    else:
        showInfo("No matching .wav files found in this editor note to convert.")

def process_deck_audio():
    """Iterates completely through active collection spaces searching for targets."""
    config = mw.addonManager.getConfig(__name__) or {"target_bitrate": "128k"}
    bitrate = config.get("target_bitrate", "128k")

    deck_names = [d["name"] for d in mw.col.decks.all_names_and_ids()]
    deck_name, ok = QInputDialog.getItem(mw, "Select Deck", "Choose deck to convert:", deck_names, 0, False)
    
    if not ok or not deck_name:
        return

    media_dir = mw.col.media.dir()
    card_ids = mw.col.find_cards(f"deck:'{deck_name}'")

    if not card_ids:
        showInfo("No cards found in selected target deck.")
        return

    mw.progress.start(max=len(card_ids), parent=mw, title="Anki Audio Converter: Processing...")
    
    modified_notes_count = 0
    converted_files_count = 0

    try:
        for idx, cid in enumerate(card_ids):
            card = mw.col.get_card(cid)
            note = card.note()
            note_changed = False

            for field_name, field_value in note.items():
                matches = AUDIO_REGEX.findall(field_value)
                if not matches:
                    continue

                for wav_file in matches:
                    new_mp3 = convert_wav_to_mp3(media_dir, wav_file, bitrate)
                    if new_mp3:
                        field_value = field_value.replace(f"[sound:{wav_file}]", f"[sound:{new_mp3}]")
                        note[field_name] = field_value
                        note_changed = True
                        converted_files_count += 1

            if note_changed:
                note.flush()
                modified_notes_count += 1
            
            mw.progress.update(value=idx)
    finally:
        mw.progress.finish()
        mw.reset()

    showInfo(f"Conversion complete!\nProcessed {modified_notes_count} notes.\nSuccessfully optimized {converted_files_count} audio tracks.")

def add_editor_button(buttons: list[QWidget], editor: Editor) -> list[QWidget]:
    """Injects an on-demand audio conversion button into the editor toolbar."""
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    
    button = QPushButton()
    button.setToolTip("Convert Audio")
    
    if os.path.exists(icon_path):
        button.setIcon(QIcon(icon_path))
    else:
        button.setText("🎵 Convert")
        
    qconnect(button.clicked, lambda: process_editor_card(editor))
    buttons.append(button)
    return buttons

def init_addon():
    """Binds public operational components inside standard Tools menu dropdown."""
    action = QAction("Anki Audio Converter", mw)
    qconnect(action.triggered, process_deck_audio)
    mw.form.menuTools.addAction(action)

# Hooks setup
addHook("profileLoaded", init_addon)
gui_hooks.editor_did_init_buttons.append(add_editor_button)
