PYTHON = python
PIP = pip
ADDON_DIR = anki_audio_converter

.PHONY: setup clean zip

setup:
	@echo "Checking system dependencies..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "Installing ffmpeg via Homebrew..."; \
		brew install ffmpeg; \
	else \
		echo "⚠️ Homebrew not found. Please ensure 'ffmpeg' is installed manually."; \
	fi
	@echo "Installing Python packages..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✨ Setup complete!"

zip:
	@echo "Packing Add-on package for AnkiWeb..."
	@rm -f anki_audio_converter.ankiaddon
	@zip -r anki_audio_converter.ankiaddon __init__.py manifest.json config.json config.md
	@echo "📦 Generated anki_audio_converter.ankiaddon"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f *.ankiaddon
	@echo "Caches and builds cleared."
