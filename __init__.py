from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

from anki.hooks import addHook
from aqt import mw, gui_hooks
from aqt.qt import QAction, QMenu, QInputDialog
from aqt.utils import showInfo, showWarning, qconnect
from aqt.browser import Browser
from aqt.editor import Editor, EditorWebView
from anki.notes import Note


# ------------------------------------------------------------
# Audio detection
# ------------------------------------------------------------

AUDIO_REGEX = re.compile(r"\[sound:([^\]]+\.wav)\]", re.IGNORECASE)


# ------------------------------------------------------------
# FFmpeg detection
# ------------------------------------------------------------

def get_ffmpeg_path() -> str:
    """Return system ffmpeg binary path if available."""
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]:
        try:
            subprocess.run([path, "-version"], capture_output=True, check=True)
            return path
        except Exception:
            continue
    return "ffmpeg"


# ------------------------------------------------------------
# Core conversion
# ------------------------------------------------------------

def convert_wav_to_mp3(media_dir: str, wav_filename: str, bitrate: str) -> Optional[str]:
    wav_path = os.path.join(media_dir, wav_filename)

    if not os.path.exists(wav_path):
        return None

    mp3_filename = os.path.splitext(wav_filename)[0] + ".mp3"
    mp3_path = os.path.join(media_dir, mp3_filename)

    ffmpeg = get_ffmpeg_path()

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        wav_path,
        "-b:a",
        bitrate,
        mp3_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        os.remove(wav_path)
        return mp3_filename
    except Exception:
        return None


# ------------------------------------------------------------
# Shared note processor
# ------------------------------------------------------------

def process_note(note: Note, media_dir: str, bitrate: str) -> int:
    """Convert all WAV audio references in a note."""
    converted = 0

    for field_name, field_value in note.items():
        matches = AUDIO_REGEX.findall(field_value)
        if not matches:
            continue

        updated = field_value

        for wav_file in matches:
            mp3 = convert_wav_to_mp3(media_dir, wav_file, bitrate)
            if mp3:
                updated = updated.replace(
                    f"[sound:{wav_file}]",
                    f"[sound:{mp3}]",
                )
                converted += 1

        note[field_name] = updated

    return converted


# ------------------------------------------------------------
# Browser selection conversion
# ------------------------------------------------------------

def process_browser_selected_cards(browser: Browser) -> None:
    selected_cids = browser.selected_cards()

    if not selected_cids:
        showWarning("No cards selected.")
        return

    config = mw.addonManager.getConfig(__name__) or {}
    bitrate: str = config.get("target_bitrate", "128k")
    media_dir = mw.col.media.dir()

    mw.progress.start(max=len(selected_cids), parent=browser, title="Converting Audio...")

    modified_notes = 0
    converted_files = 0

    try:
        for i, cid in enumerate(selected_cids):
            card = mw.col.get_card(cid)
            note = card.note()

            converted = process_note(note, media_dir, bitrate)

            if converted > 0:
                note.flush()
                modified_notes += 1
                converted_files += converted

            mw.progress.update(value=i)

    finally:
        mw.progress.finish()
        browser.model.reset()
        mw.reset()

    showInfo(
        f"Browser Conversion Complete!\n"
        f"Notes modified: {modified_notes}\n"
        f"Files converted: {converted_files}"
    )


# ------------------------------------------------------------
# Deck-wide conversion
# ------------------------------------------------------------

def process_deck_audio() -> None:
    config = mw.addonManager.getConfig(__name__) or {}
    bitrate: str = config.get("target_bitrate", "128k")
    media_dir = mw.col.media.dir()

    deck_names = [d.name for d in mw.col.decks.all_names_and_ids()]

    deck_name, ok = QInputDialog.getItem(
        mw,
        "Select Deck",
        "Choose deck to convert:",
        deck_names,
        0,
        False,
    )

    if not ok or not deck_name:
        return

    cids = mw.col.find_cards(f"deck:'{deck_name}'")

    if not cids:
        showInfo("No cards found.")
        return

    mw.progress.start(max=len(cids), parent=mw, title="Processing Deck...")

    modified_notes = 0
    converted_files = 0

    try:
        for i, cid in enumerate(cids):
            card = mw.col.get_card(cid)
            note = card.note()

            converted = process_note(note, media_dir, bitrate)

            if converted > 0:
                note.flush()
                modified_notes += 1
                converted_files += converted

            mw.progress.update(value=i)

    finally:
        mw.progress.finish()
        mw.reset()

    showInfo(
        f"Deck Conversion Complete!\n"
        f"Notes modified: {modified_notes}\n"
        f"Files converted: {converted_files}"
    )


# ------------------------------------------------------------
# Editor context menu (FIXED FEATURE)
# ------------------------------------------------------------

def on_editor_convert(editor: Editor) -> None:
    """Wrapper to cleanly convert, save, and reload fields in the UI view."""
    if not editor.note:
        return
        
    config = mw.addonManager.getConfig(__name__) or {}
    bitrate: str = config.get("target_bitrate", "128k")
    media_dir = mw.col.media.dir()
    
    converted = process_note(editor.note, media_dir, bitrate)
    
    if converted > 0:
        # Commit the modifications to Anki's database
        editor.note.flush()
        # Force the HTML/Svelte webview screen layout to repaint immediately
        editor.loadNoteKeepFocus()
        showInfo(f"Conversion Complete!\nOptimized {converted} audio references.")
    else:
        showInfo("No matching .wav files found on this card.")


def setup_editor_context_menu(webview: EditorWebView, menu: QMenu) -> None:
    action = menu.addAction("Anki Audio Converter: Convert Note")
    # webview.editor safely hands off the tracking instance coordinates
    qconnect(action.triggered, lambda: on_editor_convert(webview.editor))


# ------------------------------------------------------------
# Browser context menu
# ------------------------------------------------------------

def setup_browser_context_menu(browser: Browser, menu: QMenu) -> None:
    action = menu.addAction("Anki Audio Converter: Convert Selection")
    qconnect(action.triggered, lambda: process_browser_selected_cards(browser))


# ------------------------------------------------------------
# Setup main Tools menu
# ------------------------------------------------------------

def init_addon() -> None:
    action = QAction("Anki Audio Converter", mw)
    qconnect(action.triggered, process_deck_audio)
    mw.form.menuTools.addAction(action)


# ------------------------------------------------------------
# Hooks
# ------------------------------------------------------------

addHook("profileLoaded", init_addon)

gui_hooks.browser_will_show_context_menu.append(
    setup_browser_context_menu
)

gui_hooks.editor_will_show_context_menu.append(
    setup_editor_context_menu
)
