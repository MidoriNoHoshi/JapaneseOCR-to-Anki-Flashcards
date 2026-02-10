import argparse
from japtoanki.core import navigation, start_processing

def main():
    parser = argparse.ArgumentParser(
        description="OCR Japanese text and send it to Anki"
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory to process"
    )

    parser.add_argument(
        "--deck",
        default="IRLJapanese-Sentences",
        help="Anki deck name (default: IRLJapanese-Sentences)"
    )

    parser.add_argument(
        "--tags",
        default="Irl",
        help="Comma-separated Anki tags"
    )

    args = parser.parse_args()

    if args.path:
        start_processing(args.path, deck=args.deck, tags=args.tags)
    else:
        manga_dir = navigation()
        if manga_dir:
            start_processing(manga_dir, deck=args.deck, tags=args.tags)

# def main():
#     if len(sys.argv) > 1:
#         start_processing(sys.argv[1])
#     else:
#         mangaDir = navigation()
#         if not mangaDir:
#             print("Exiting")
#             return 
#         start_processing(mangaDir)
