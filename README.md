# Japtoanki ⚡📖

Extracts sentences containing kanji from manga, screenshots, etc, and automatically creates Anki flashcards for later study.

---

## Installation

```bash
pip install japtoanki
```

**Note:** japtoanki includes OCR support by default (will download AI model weights (~400MB) on the first run)

### Anki Cards:
*Examples*:

![Anki Card](./images/2026-02-10-145359_hyprshot.png) ![Anki Card2](./images/2026-02-10-153400_hyprshot.png)
## Usage

#### Requirements:

- [Python](https://www.python.org/)
- [Anki](https://apps.ankiweb.net/)
- [Anki-connect](https://github.com/amikey/anki-connect)

Requires [Anki-connect](https://github.com/amikey/anki-connect) plugin to be enabled in Anki to work. Anki needs to be open as japtoanki runs.

```bash
japtoanki /path/to/manga --deck Kanji_Sentences --tag manga
```

Running japtoanki with no flags will open a basic cli file-navigator.
If the deck given with the `--deck` flag doesn't exist, japtoanki will create a new deck with the given name.

#### Requirements:
- [python](https://www.python.org/downloads/)
- [Anki](https://apps.ankiweb.net/)
