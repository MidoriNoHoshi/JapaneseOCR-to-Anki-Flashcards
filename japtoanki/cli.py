# PYTHON_ARGCOMPLETE_OK
import argparse
import argcomplete #To be able to have [TAB} to show options #type: ignore
import sys
from japtoanki.core import navigation, startProcessing

def main():
    parser = argparse.ArgumentParser(
        description="OCR Japanese text and use for Anki flashcards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process a directory of images:
    japtoanki /path/to/directory --deck "Japanese manga" --tags "manga, gundam"

    # Text file with translation:
    japtoanki chat.txt --deck "Japanese Chat" --translate en

    # Interactive navigator (no path argument)
    japtoanki
        """
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory to process"
    )

    parser.add_argument(
        "--deck",
        default="Kanji-Sentences",
        help="Anki deck name (default: Kanji-Sentences)"
    )

    parser.add_argument(
        "--tags",
        default="japtoanki",
        help="Comma separated Anki tags"
    )

    parser.add_argument(
        "--translate",
        nargs="?",
        default=None,
        const="en",
        help="Translate Sentences into desired language using google translate (Default is en (english))"
    )

    parser.add_argument(
        "--no-furigana",
        action="store_true", # Furigana on default
        help="Generate furigana (helper hiragana) for the kanji?"
    )

    parser.add_argument(
        "--mastered-kanji",
        help="Input document containing already mastered kanji. Database of mastered kanji is [japtoankikanji.txt]"
    )

    parser.add_argument(
        "--all-sentences",
        action="store_true",
        help="Runs japtoanki as if 0 mastered-kanji."
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.path:
        target = args.path
    else:
        print("\n🗂️  Interactive Directory Navigator")
        print("="*60)
        target = navigation()
    if target is None:
        sys.exit(0)

    try:
        startProcessing(target_path=target, deck=args.deck, tags=args.tags, showFurigana=not args.no_furigana, masteredKanji=args.mastered_kanji, translateLang=args.translate, allSentences=args.all_sentences)
        print("\n✅ Complete")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() # AI explanation:
    # If you try to import cli from another file, the code inside that block won't run. This prevents your program from starting the CLI navigation menu automatically just because you wanted to import a function from it.
