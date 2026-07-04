import os
import re
import subprocess
from anki.hooks import addHook
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, showWarning, qconnect

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
    
    # Run conversion via subprocess to decouple execution environments
    cmd = [ffmpeg_bin, "-y", "-i", wav_path, "-b:a", bitrate, mp3_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # If success, remove legacy file footprint
        if os.path.exists(wav_path):
            os.remove(wav_path)
        return mp3_filename
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def process_deck_audio():
    """Iterates completely through active collection spaces searching for targets."""
    config = mw.addonManager.getConfig(__name__) or {"target_bitrate": "128k"}
    bitrate = config.get("target_bitrate", "128k")

    # Pick target collection setup
    deck_names = [d["name"] for d in mw.col.decks.all_names_and_ids()]
    deck_name, ok = QInputDialog.getItem(mw, "Select Deck", "Choose deck to compress:", deck_names, 0, False)
    
    if not ok or not deck_name:
        return

    media_dir = mw.col.media.dir()
    deck_id = mw.col.decks.id(deck_name)
    card_ids = mw.col.find_cards(f"deck:'{deck_name}'")

    if not card_ids:
        showInfo("No cards found in selected target deck.")
        return

    mw.progress.start(max=len(card_ids), parent=mw, title="Compressing Audio Assets...")
    
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
                        # Swap the string context cleanly
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

    showInfo(f"Operation complete!\nProcessed {modified_notes_count} notes.\nSuccessfully compressed {converted_files_count} audio tracks.")

def init_addon():
    """Binds operational components inside standard drop-downs."""
    action = QAction("Batch Compress WAV -> MP3", mw)
    qconnect(action.triggered, process_deck_audio)
    mw.form.menuTools.addAction(action)

addHook("profileLoaded", init_addon)
