import os
import json
import subprocess
import shutil
import re

KANJI_RE = re.compile(r'[\u4e00-\u9fff]') # Kanji characters
JP_RE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]') # Jp characters
EN_RE = re.compile(r'[A-Za-z]') # English alphabet
AGGRESSIVE_SPLIT_RE = re.compile(r'[、,。．\.！？!?・：:；;「」『』【】（\(\)]|…+|\n+')

def splitParagraphs(text: str) -> list[str]:
    if not text:
        return []
    parts = AGGRESSIVE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p and p.strip()]

# def splitParagraphs(paragraph):
#     sentences = []
#     buf = ""
#
#     for line in paragraph:
#         buf += line
#         if re.search(r"[。！？!?…]$", line):
#             sentences.append(buf)
#             buf = ""
#         else:
#             # soft break → treat as pause, not sentence end
#             buf += " "
#
#     if buf:
#         sentences.append(buf)
#
#     return sentences


def valid(text, ratio=0.7): # Discard sentence if it's mostly English
    jp = len(JP_RE.findall(text))
    en = len(EN_RE.findall(text))

    if en / max(jp, 1) > 0.5:
        return False

    if jp / max(len(text), 1) < ratio:
        return False
    return True

def kanjiFilter(text: str) -> bool: 
    return bool(KANJI_RE.search(text))

def noiseFilter(text, threshold=0.3):
    if not text:
        return True

    noise = re.findall(r'[0-9\d\s\-\=\+\_\!\@\#\$\%\^\&\*\(\)\[\]\{\}\,\?\/\>\<\:\;\"\'\|\ッーァィゥェォヵヶ]', text)
    noise_count = len(noise)
    noise_ratio = noise_count / len(text)
    return noise_ratio > threshold

def mokuroRun(input_dir: str):
    """Run mokuro OCR on manga directory"""
    if shutil.which("mokuro") is None:
        raise RuntimeError("mokuro is not installed or not in PATH\n" "Install it with: pip install mokuro")
    # mokuro will create output in the parent of input by default
    # We need to handle this differently
    
    cmd = ["mokuro", input_dir, "--disable_confirmation"]
    print(f"   Running OCR: {' '.join(cmd)}")
    try:
        # subprocess.run(cmd, check=True, capture_output=True, text=True)
        subprocess.run(cmd, check=True) #Show mokuro loading bars.
    except subprocess.CalledProcessError as e:
        print(f"   Mokuro failed!")
        print(f"   stderr: {e.stderr}")
        raise RuntimeError(f"Mokuro OCR failed. Check input directory.")

def extractSentences(ocr_dir: str) -> list:

    sentences = []
    seen = set()

    for root, _, files in os.walk(ocr_dir):
        for file in sorted(files):
            if not file.endswith(".json"):
                continue
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                data = json.load(f)

            for block in data.get("blocks", []): # block contains the n'th dict in the list (n = loop iteration)

                block_text = "".join(block.get("lines", [])).strip()

                for chunk in splitParagraphs(block_text):
                    if len(chunk) >= 4 and valid(chunk) and kanjiFilter(chunk):
                        if not noiseFilter(chunk) and chunk not in seen:
                            seen.add(chunk)
                            sentences.append(chunk)

    return sentences

def listSentences(sentences, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in sentences:
            f.write(s + "\n")

