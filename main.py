import argparse
import logging
import os
import sys

from simon import CODENAME, __version__
from simon.app import Simon
from simon.config import DATA_DIR, Settings

BANNER = r"""
   ███████╗██╗███╗   ███╗ ██████╗ ███╗   ██╗
   ██╔════╝██║████╗ ████║██╔═══██╗████╗  ██║
   ███████╗██║██╔████╔██║██║   ██║██╔██╗ ██║
   ╚════██║██║██║╚██╔╝██║██║   ██║██║╚██╗██║
   ███████║██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
   ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="simon", description=f"{CODENAME} — cinematic desktop voice assistant")
    p.add_argument("model", nargs="?", help="Ollama model to use (overrides settings.json)")
    p.add_argument("--browser", action="store_true", help="open the HUD in a browser window instead of a native one")
    p.add_argument("--headless", action="store_true", help="serve the HUD without opening any window")
    p.add_argument("--no-mic", action="store_true", help="disable microphone, wake word and hotkey")
    p.add_argument("--mute", action="store_true", help="animate speech without playing audio")
    p.add_argument("--port", type=int, help="HUD server port")
    p.add_argument("--fullscreen", action="store_true", help="launch the HUD fullscreen")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return p.parse_args()


def setup_logging(verbose: bool) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    handlers = [logging.FileHandler(os.path.join(DATA_DIR, "simon.log"), encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)-18s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    for noisy in ("urllib3", "httpx", "httpcore", "PIL", "comtypes", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger("phonemizer").setLevel(logging.ERROR)


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    settings = Settings.load()
    if args.model:
        settings.set("llm.model", args.model)
    if args.port:
        settings.set("hud.port", args.port)
    if args.fullscreen:
        settings.set("hud.fullscreen", True)
    if args.headless or args.browser:
        settings.set("hud.auto_hide", False)

    if sys.stdout is not None:
        print(f"\033[96m{BANNER}\033[0m   v{__version__}  ·  say \"Hey {settings.get('assistant.name')}\" or press "
              f"{settings.get('listening.hotkey')}\n")

    mode = "none" if args.headless else "browser" if args.browser else "native"
    Simon(settings, window_mode=mode, use_mic=not args.no_mic, muted=args.mute).run()


if __name__ == "__main__":
    main()
