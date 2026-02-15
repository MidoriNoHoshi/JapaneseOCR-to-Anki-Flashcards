import os
import re
import shutil
from deep_translator import GoogleTranslator
import requests
import time
import tempfile
import csv
import questionary #type: ignore
from fugashi import Tagger #type: ignore # Supposedly could really use MeCab as the filter for bad sentences. . .
import jaconv #type: ignore
# import json
# from pykakasi import kakasi # pykakasi to be replaced by something else. Makes mistakes.
from tqdm import tqdm
# from deep_translator import GoogleTranslator #LibreTranslator # GoogleTranslator giving me issues all day. Too much of a pain in the ass. Wasted so many hours. #type: ignore
from japtoanki.mokuroRunner import kanjiFilter, noiseFilter, splitParagraphs, mokuroRun, extractSentences

tagger = None

url = "http://localhost:8765" # Connect to Anki Connect port
# jouzuList = "kanji.txt"
knownSet = set()
kanjiList = os.path.expanduser("~/.mastered_kanji_list(japtoanki).txt")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_EXTS = {".txt", ".md", ".html", ".json", ".csv"} # can it take .json, .apkg, colpkg, csv files?

def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS

def is_text(path):
    return os.path.splitext(path)[1].lower() in TEXT_EXTS

def dir_contains_images(path):
    if not os.path.isdir(path):
        return False
    return any(is_image(f) for f in os.listdir(path))

def dir_contains_json(path):
    if not os.path.isdir(path):
        return False
    return any(f.lower().endswith(".json") for f in os.listdir(path))

def containsKanji(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text)) # Doesn't cover all kanji, but it's not as heavy as using regex \p {Han}
    # return bool(regex.search(r'\p{Han}', text)) # regex han is heavy

def storeKanji(file):
    if not os.path.exists(file):
        return set()
    try:
        with open(file, 'r', encoding="utf-8") as f:
            return set(re.findall(r'[\u4e00-\u9fff]', f.read()))
    except Exception as e:
        print(f"Could not extract kanji from {file}: {e}")
        return set()

def loadknownSet():
    global knownSet
    if not os.path.exists(kanjiList):
        with open(kanjiList, 'w', encoding="utf-8") as f: #type: ignore
            f.write("一")
    knownSet = storeKanji(kanjiList)
    return knownSet

def updateKanjiList(file):
    global knownSet
    initialList = storeKanji(kanjiList)
    newList = storeKanji(file)
    newKanji = [k for k in newList if k not in initialList]

    if not newKanji:
        print("Nothing to add to mastered list")
        return

    mastered_ordered = []
    if os.path.exists(kanjiList):
        with open(kanjiList, 'r', encoding="utf-8") as f: #type: ignore
            mastered_ordered = [line.strip() for line in f if line.strip()]

    updated_ordered = newKanji + mastered_ordered

    # mergedList = initialList.union(newList)

    with open(kanjiList, 'w', encoding="utf-8") as f:
        f.write("\n".join(updated_ordered)) 

    knownSet = initialList.union(newList)
    print(f"Mastered Kanji List Updated: {len(newKanji)}. Total mastered kanji: {len(knownSet)}")

# def kanjiToHiragana(text):
#     result = kks.convert(text)
#     return "".join([item['hira'] for item in result])

def useTagger(): # Also lazy-loading fugashi? Or I guess MeCab. Splits sentence into individual "tokens" / words.
    global tagger
    if tagger is None:
        # tagger = Tagger('-Owakati') # Idk what owakati really does honestly
        tagger = Tagger()
    return tagger

def MeCabFilter(tokens, max_symbol_ratio=0.25, min_tokens=3, min_content_pos=1): # Let the Ai do the magic. Don't bother wasting time.
    if not tokens or len(tokens) < min_tokens:
        return False

    symbol_count = 0
    content_count = 0  # Nouns, Verbs, Adjectives
    kanji_found = False
    
    # Track POS (Part of Speech) categories
    for t in tokens:
        surface = t.surface
        # UniDic/Fugashi usually uses pos1 for the main category
        pos = t.feature.pos1 # UniDic => t.feature.pos1, pos2, pos3, pos4. IPADIC => t.feature.pos
        
        if containsKanji(surface):
            kanji_found = True

        # Identify Content Words
        # We include '形状詞' (Adjectival Nouns/たる-adjectives) for better coverage
        if pos in {"名詞", "動詞", "形容詞", "形状詞"}:
            # Exclude single-character generic nouns like 'ん', 'の', 'こと' 
            # if they are marked as '非自立' (dependent)
            if hasattr(t.feature, 'pos2') and t.feature.pos2 == "非自立":
                continue
            content_count += 1
            
        # Identify Noise/Symbols
        elif pos in {"補助記号", "記号", "空白"}:
            # Allow common prolonging marks, but count others as noise
            if surface not in {"・", "ー", "～", "!" , "？", "!", "?"}:
                symbol_count += 1

    # Logic Gates
    # 1. Must contain at least one Kanji (since this is for Kanji study)
    if not kanji_found:
        return False

    # 2. Density Check: Too many symbols relative to words is usually OCR gore
    if (symbol_count / len(tokens)) > max_symbol_ratio:
        return False

    # 3. Substance Check: Must have enough "meaningful" words to be a sentence
    if content_count < min_content_pos:
        return False

    # 4. Length Check: Very long strings without symbols are often OCR merging errors
    if len(tokens) > 50 and symbol_count == 0:
        return False

    return True

def hiraganaFurigana(tokens):
    hiraganaRes = []
    furiganaRes = []

    for word in tokens:
        surface = word.surface
        if containsKanji(surface):
            if word.feature.kana:
                reading = jaconv.kata2hira(word.feature.kana)
            else:
                reading = surface
        else:
            reading = surface
        hiraganaRes.append(reading)
        if containsKanji(surface):
            furiganaRes.append(f" {surface}[{reading}]")
        else:
            furiganaRes.append(surface)

    sentenceHirgana = "".join(hiraganaRes)
    sentenceFurigana = "".join(furiganaRes).strip()

    return sentenceHirgana, sentenceFurigana

def isthochanhkanji(text, ignoreMastered=False):
    kanjiSet = set(re.findall(r'[\u4e00-\u9fff]', text))
    if ignoreMastered: # For the all-sentences flag
        notJouzu = kanjiSet
    else:
        notJouzu = [shit for shit in kanjiSet if shit not in knownSet] # Self explanitory XD
    ### This is a special line, my favourite line XDDDDDDDDDDDD FUCKKKK im retarded
    links = []
    for a in sorted(notJouzu):
        link = f'<a href="https://hochanh.github.io/rtk/{a}/index.html">{a}</a>'
        links.append(link)
    # Return each used kanji as a list
    return " ".join(links)

def translateChunks(sentences, lang, chunkGirth=10):
    if not isinstance(lang, str) or not lang.strip():
        return [""] * len(sentences)
    if not sentences:
        return []
    translator = GoogleTranslator(source="ja", target=lang)
    translated_list = [] # The ouput of the chunk

    for i in range(0, len(sentences), chunkGirth):
        batch = sentences[i : i + chunkGirth]

        enNumberate = "\n".join([f"{index+1}. {text}" for index, text in enumerate(batch)])
        try:
            ouputChunk = translator.translate(enNumberate)
            lines = [line.strip() for line in ouputChunk.split("\n") if line.strip()]
            unNumberedLines = [re.sub(r"^\d+\.\s*", "", line) for line in lines]
        
            if len(unNumberedLines) != len(batch):
                print(f"Batch {i//chunkGirth} mismatch! Expected {len(batch)}, got {len(unNumberedLines)}")
                while len(unNumberedLines) < len(batch):
                    unNumberedLines.append("")
            
            translated_list.extend(unNumberedLines)
            time.sleep(2)
        except Exception as e:
            print(f"Error in batch starting at {i}: {e}")
            translated_list.extend([""] * len(batch))
    return translated_list


# def translateSentence(text, lang): # Can't fucking figure out this shit. I give up for now.
#     if not isinstance(lang, str) or not lang.strip():
#         return ""
#     if not text or not text.strip():
#         return ""
#
#     try: 
#         from deep_translator import GoogleTranslator # Lazy import instead?
#         time.sleep(2)  # Prevent Rate Limiting
#         result = GoogleTranslator(source="ja", target=lang).translate(text)
#         return result if result is not None else ""
#
#     except AttributeError as e:
#         print(f"Translation failed - translator object issue: {str(e)}")
#         return ""
#     except Exception as e:
#         print(f"Translation Error: {str(e)}")
#         return ""

def extract_from_single_image(image_path): # mokuro only runs on directories. So many temporary directory for single images
    with tempfile.TemporaryDirectory() as tmp:
        tmp_image = os.path.join(tmp, os.path.basename(image_path))
        shutil.copy2(image_path, tmp_image)

        mokuroRun(tmp)
        ocr_dir = os.path.join(tmp, "_ocr")
        return extractSentences(ocr_dir)

def extract_sentences_from_input(path):
    if os.path.isfile(path):
        ocr_dir = os.path.join(path, "_ocr")
        if os.path.exists(ocr_dir):
            shutil.rmtree(ocr_dir)
        
        if is_image(path):
            return extract_from_single_image(path)
        
        if path.lower().endswith(".json"):
            return extractSentences(os.path.dirname(path))
        
        if is_text(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                sentences = []
                for chunk in splitParagraphs(content):
                    sentences.append(chunk)
                return sentences
        
        raise ValueError(f"Unsupported file type: {path}")
    if os.path.isdir(path):

        if dir_contains_json(path):
            return extractSentences(path)
        
        if dir_contains_images(path):
            mokuroRun(path)

            parent_dir = os.path.dirname(os.path.abspath(path))
            directory_name = os.path.basename(os.path.abspath(path))
            mokuro_ocr_path = os.path.join(parent_dir, "_ocr", directory_name)
            if os.path.exists(mokuro_ocr_path):
                return extractSentences(mokuro_ocr_path)
            internal_ocr = os.path.join(path, "_ocr")
            if os.path.exists(internal_ocr):
                return extractSentences(internal_ocr)
        
        # Fallback: collect all text from text files
        sentences = []
        
        for root, _, files in os.walk(path):
            for f in files:
                if is_text(f):
                    file_path = os.path.join(root, f)
                    with open(file_path, encoding="utf-8") as fh:
                        # rawlines = re.split(r"[。！？\n]+", fh.read())
                        text = fh.read()

                        for chunk in splitParagraphs(text):
                            if len(chunk) < 4:
                                continue
                            if not kanjiFilter(chunk):
                                continue

                            tokens = list(useTagger()(chunk))
                            if not noiseFilter(chunk) and MeCabFilter(tokens):
                                sentences.append(chunk)

                        # rawlines = re.split(r"[。！？\n]+", fh.read())
                        # for line in rawlines:
                        #     line = line.strip()
                        #     if line and kanjiFilter(line):
                        #         tokens = list(useTagger()(line))
                        #         if not noiseFilter(line) and MeCabFilter(tokens):
                        #             sentences.append(line)
                        # sentences += re.split(r"[。！？\n]+", fh.read())
        return sentences

    raise ValueError(f"Invalid path: {path}")

def ankiPackage(action, **params):
    payload = {"action": action, "version": 6, "params": params}
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        return {"Error": str(e)}

def getDecks():
    try: 
        return ankiPackage("deckNames").get("result", [])
    except:
        print("\n ❌ Cannot connect to Anki")
        print("Make sure:")
        print("1. Anki is running")
        print("2. AnkiConnect add-on is installed and enabled (code: 2055492159)")
        return []

def setupAnki(deckName):
    if deckName not in getDecks():
        ankiPackage("createDeck", deck=deckName)
    models = ankiPackage("modelNames").get("result", [])
    if "Kanji-Hochanh" not in models:
        create_custom_model()

def create_custom_model():
    # Defines the Kanji-Hochanh note type with a Furigana field.
    model_data = {
        "modelName": "Kanji-Hochanh",
        "inOrderFields": ["Front", "Back", "HochanhLinks", "translation"],
        "cardTemplates": [
            {
                "Name": "Japanese sentence",
                "Front": '<div class="jp">{{Front}}</div>',
                "Back": (
                    '<div class="jp">{{furigana:Back}}</div>'
                    '<hr>'
                    '<div class="translation">{{translation}}</div>'
                    '<br><div class="kanji">{{HochanhLinks}}</div>'
                )
            }
        ],
        "css": ".card { text-align: center; font-family: 'Meiryo', sans-serif; } "
               ".jp { font-size: 30px; } "
               ".translation { font-style: italic; color: gray; } "
               ".kanji a { font-size: 40px; margin: 5px; text-decoration: none; }"
    }
    ankiPackage("createModel", **model_data)

def create_anki_card(front, back, hochanhLinks, translation, deck, tags):
    # hochanhkanji = f'<a href="https://hochanh.github.io/rtk/{Kanji}/index.html">{Keyword}</a>'
    params = {
        "note": {
            "deckName": deck,
            "modelName": "Kanji-Hochanh",
            "fields": {
                "Front": front,
                "Back": back,
                "HochanhLinks": hochanhLinks,
                "translation": translation
            },
            "tags":tags.split(", "),
            "options": {"allowDuplicate": False}
        }
    }
    return ankiPackage("addNote", **params)

# def walk(root_dir, deck, tags, translateLang):
#     totalFiles = []
#     for root, _, files in os.walk(root_dir):
#         for file in files:
#             if file.lower().endswith((".json", ".txt")):
#                 totalFiles.append(os.path.join(root, file))
#
#     print(f"\n Found {len(totalFiles)} files.")
#     for a in tqdm(totalFiles, desc="Creating Anki flashcards", unit="file"):
#         processFile(a, deck, tags, translateLang)
#             # a = os.path.join(root, file)
#             # processFile(a)

# def navigation(start="."):
#     current = os.path.abspath(start)
#     while True:
#         print(f"\n{'='*60}")
#         print(f"\nCurrent Directory: {current}")
#         print(f"\n{'='*60}")
#
#         entries = sorted(os.listdir(current))
#
#         for i, entry in enumerate(entries):
#             full_path = os.path.join(current, entry)
#             if os.path.isdir(full_path):
#                 print(f"{i}: 📁 {entry}")
#             else:
#                 print(f"{i}: 📄 {entry}")
#
#         print(f"\n{'='*60}")
#         print("\n[ENTER] : Scan current directory + all subdirectories")
#         print("\n.. : go up")
#         print("q : quit")
#         print(f"\n{'='*60}")
#
#         choice = input("Select Directory (ENTER to select):").strip()
#
#         if choice == "":
#             return current
#
#         if choice == "q": 
#             return None
#
#         if choice == "..":
#             current = os.path.dirname(current)
#             continue
#
#         if choice.isdigit():
#             index = int(choice)
#             if 0 <= index < len(entries):
#                 selected = os.path.join(current, entries[index])
#                 if os.path.isdir(selected):
#                     current = selected
#                 else:
#                     return selected
#                 continue
#
#         print("Invalid choice")

def navigation(start="."):
    current = os.path.abspath(start)
    
    while True:
        try:
            entries = sorted(os.listdir(current))
        except PermissionError:
            print(f"❌ Permission denied: {current}")
            current = os.path.dirname(current)
            continue

        choices = []
        choices.append(questionary.Choice(
            title=f" [SELECT CURRENT DIRECTORY: {os.path.basename(current) or current}]",
            value="SELECT_CURRENT"
        ))
        choices.append(questionary.Choice(title="  .. (Back)", value="GO_BACK"))
        choices.append(questionary.Separator())

        for entry in entries:
            full_path = os.path.join(current, entry)
            if os.path.isdir(full_path):
                choices.append(questionary.Choice(title=f"📁 {entry}", value=full_path))
            else:
                choices.append(questionary.Choice(title=f"📄 {entry}", value=full_path))

        choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="❌ Quit", value="QUIT"))

        useShortcuts = len(choices) <= 36

        answer = questionary.select(
            f"Navigate to files/folders (Current: {current})",
            choices=choices,
            use_shortcuts=useShortcuts # Disable shortcuts if more than 36 options
        ).ask()

        if answer == "QUIT" or answer is None:
            return None
        
        if answer == "SELECT_CURRENT":
            return current
        
        if answer == "GO_BACK":
            current = os.path.dirname(current)
            continue
            
        # If user selected a directory, drill down. If a file, return it.
        if os.path.isdir(answer):
            current = answer
        else:
            return answer


def startProcessing(target_path, deck, tags, showFurigana=True, masteredKanji=None, translateLang=None, allSentences=False):
    if len(knownSet) > 1:
        loadknownSet()
        print(f"Loaded {len(knownSet)} known set.")

    if masteredKanji:
        updateKanjiList(masteredKanji)
        print(f"Merged {masteredKanji} with known set.")

    setupAnki(deck)

    ankiConnectEnabled = True
    if not getDecks():
        print("\n Anki-Connect Disabled or not installed. Switching to CSV export mode.")
        ankiConnectEnabled = False
    else:
        setupAnki(deck)

    sentences = extract_sentences_from_input(target_path)
    kanjiContainingSentences = [n for n in sentences if n.strip() and containsKanji(n.strip())]
    if len(kanjiContainingSentences) == 0:
        print(f"No sentences containing kanji found.")
        return
    else:
        print(f"Found {len(kanjiContainingSentences)} sentences containing kanji.\n")

    csv_rows = []
    eligibleSentences = [] # Sentences approved by filters.

    for txt in tqdm(sentences, desc="Filtering sentences"):
        clean = txt.strip()
        if not clean:
            continue
        if len(clean) < 5:
            continue
        tokens = list(useTagger()(clean))
        if not MeCabFilter(tokens):
            continue

        hiragana, furigana = hiraganaFurigana(tokens)
        links = isthochanhkanji(clean, ignoreMastered=allSentences)
        if not links: continue # Filter if sentence only has mastered kanji

        eligibleSentences.append({
            'clean': clean,
            'hiragana': hiragana,
            'furigana': furigana,
            'links': links
        })
    if not eligibleSentences:
        print("No valid sentences")
        return

    # trans = ""
    toTranslate = []

    if translateLang:
        # trans = translateSentence(clean, translateLang)
        translateExpress = [hoo['clean'] for hoo in eligibleSentences]
        toTranslate = translateChunks(translateExpress, translateLang)
    else:
        toTranslate = [""] * len(eligibleSentences)

    for index, data in enumerate(tqdm(eligibleSentences, desc="Generating deck")):
        returnedTranslations = toTranslate[index] if index < len(toTranslate) else ""
        isFurigana = data['furigana'] if showFurigana else data['clean']

    # trans = translate(clean, translateLang)
        if ankiConnectEnabled:
            create_anki_card(data['hiragana'], isFurigana, data['links'], returnedTranslations, deck, tags)
        else:
            csv_rows.append([data['hiragana'], isFurigana, data['links'], returnedTranslations, deck, tags])

    if not ankiConnectEnabled:
        base_name = os.path.basename(target_path.strip("/").strip("\\"))
        outputFile = f"japtoanki_export_{base_name or 'deck'}.csv"
        with open(outputFile, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(csv_rows)
        print(f"\n Exported {len(csv_rows)} cards to {outputFile}.")
        print(f"Import manually into Anki (File > Import).")
    else: 
        print(f"\n  Generated deck with {len(eligibleSentences)} cards.")

