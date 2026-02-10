Extracts sentences containing kanji from manga, screenshots, etc, and automatically creates Anki flashcards for later study.

---

## Installation

###### (.txt files only):
```
pip install japtoanki
```

###### OCR Support:
```
pip install japtoanki[ocr]
```

### Anki Cards:
*Examples*:

![Anki Card](./images/2026-02-10-145359_hyprshot.png) ![Anki Card2](./images/2026-02-10-153400_hyprshot.png)
## Usage

Requires Anki-connect plugin to be enabled in Anki to work.
[Anki-Connect](https://github.com/amikey/anki-connect)


```
japtoanki /path/to/manga --deck Kanji_Sentences --tag manga
```

#### Requirements:
- [python](https://www.python.org/downloads/)
- [Anki](https://apps.ankiweb.net/)
