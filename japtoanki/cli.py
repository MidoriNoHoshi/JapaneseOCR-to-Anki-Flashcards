import argparse
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
        help="Translate Sentences into desired language using google translate (Default is english (en))"

    )

    parser.add_argument(
        "--mastered-kanji",
        help="Input media containing already mastered kanji. Database of mastered kanji is [japtoankikanji.txt]"

    )

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
        startProcessing(target_path=target, deck=args.deck, tags=args.tags, masteredKanji=args.mastered_kanji, translateLang=args.translate)
        print("\n✅ Complete")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() # AI explanation:
    # If you try to import cli from another file, the code inside that block won't run. This prevents your program from starting the CLI navigation menu automatically just because you wanted to import a function from it.
