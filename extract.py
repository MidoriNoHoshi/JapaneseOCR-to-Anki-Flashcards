#!/home/nemi/Raven/JapanesetoAnki/manga-venv/bin/python3
#!/usr/bin/python3

import os
import re
import requests
from manga_ocr import MangaOcr
from fugashi import Tagger
import jaconv
# from pykakasi import kakasi # pykakasi to be replaced by something else. Makes mistakes.
from tqdm import tqdm

mocr = MangaOcr()
# kks = kakasi()
tagger = Tagger('-Owakati')

def containsKanji(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text)) # Doesn't cover all kanji, but it's not as heavy as using regex \p {Han}
    # return bool(regex.search(r'\p{Han}', text))

# def kanjiToHiragana(text):
#     result = kks.convert(text)
#     return "".join([item['hira'] for item in result])

def kanjiToHiragana(text):
    result = []
    for m in tagger(text):
        try:
            kana = m.feature.kana
            if kana:
                result.append(jaconv.kata2hira(kana))
            else:
                result.append(m.surface)
        except (AttributeError, IndexError):
                result.append(m.surface)
    return "".join(result)

def create_anki_card(front, back):
    url = "http://localhost:8765"
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": "Japanese",
                "modelName": "Basic",
                "fields": {
                    "Front": front,
                    "Back": back
                },
                "tags": [
                    "Irl"
                ],
                "options": {
                    "allowDuplicate": False
                }
            }
        }
    }
    try:
        return requests.post(url, json=payload).json()
    except:
        return {"Error": "Connection to anki localhost failed"}

def processFile(file_path):
    ext = file_path.lower()

    if ext.endswith((".png", ".jpg", ".jpeg", ".webp")):
        original = mocr(file_path)
        if original.strip():
            if containsKanji(original):
                hiragana = kanjiToHiragana(original)
                create_anki_card(hiragana, original)
            else:
                pass
    elif ext.endswith(".txt"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                sentences = re.split(r'[。！？\n]+', content)
                for s in sentences:
                    clean = s.strip()
                    if containsKanji(clean):
                        hiragana = kanjiToHiragana(clean)
                        create_anki_card(hiragana, clean)
                    else:
                        pass
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

def walk(root_dir):
    totalFiles = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".txt")):
                totalFiles.append(os.path.join(root, file))

    print(f"\n Found {len(totalFiles)} files.")
    for a in tqdm(totalFiles, desc="Creating Anki flashcards", unit="file"):
        processFile(a)
            # a = os.path.join(root, file)
            # processFile(a)

def navigation(start="."):
    current = os.path.abspath(start)
    while True:
        print(f"\nCurrent Directory: {current}")
        entries = [
            d for d in os.listdir(current)
            # if os.path.isdir(os.path.join(current, d))
        ]
        entries.sort()

        for i, d in enumerate(entries):
            print(f"{i}: {d}")

        print("\n[ENTER] : Scan current directory + all subdirectories")
        print("\n.. : go up")
        print("q : quit")

        choice = input("Select Directory (ENTER to select):").strip()

        if choice == "":
            return current

        if choice == "q": 
            return None

        if choice == "..":
            current = os.path.dirname(current)
            continue

        if choice.isdigit():
            index = int(choice)
            if 0 <= index < len(entries):
                current = os.path.join(current, entries[index])
                continue

        print("Invalid choice")

def start_processing(target_path):
    if os.path.isfile(target_path):
        processFile(target_path)
    else:
        walk(target_path)

if __name__ == "__main__":
    mangaDir = navigation()
    if not mangaDir:
        print("Exiting")
        exit(1)
    start_processing(mangaDir)
