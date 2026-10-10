from __future__ import annotations

import random
import re
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from .plan import Plan

KNOWN_FOLDERS = {"downloads", "documents", "desktop", "pictures", "music", "videos", "home"}
_URL_RE = re.compile(r"^(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?$")
_POLITE = r"(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
_TAIL = r"(?:\s+(?:please|for me|now|thanks))*[.!?]*$"


def _clean(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[,]", " ", text)
    return re.sub(r"\s+", " ", text)


def _part_of_day(now: datetime) -> str:
    if now.hour < 5:
        return "night"
    if now.hour < 12:
        return "morning"
    if now.hour < 18:
        return "afternoon"
    return "evening"


def _spoken_time(now: datetime) -> str:
    return now.strftime("%I:%M %p").lstrip("0")


class IntentMatcher:
    def __init__(self, name: str = "Simon", honorific: str = "sir"):
        self.name = name
        self.honorific = honorific
        self._rules: List[Tuple[re.Pattern, Callable[[re.Match], Optional[Plan]]]] = []
        self._build()

    def _rule(self, pattern: str, handler: Callable[[re.Match], Optional[Plan]]) -> None:
        self._rules.append((re.compile(pattern), handler))

    def match(self, text: str) -> Optional[Plan]:
        cleaned = _clean(text)
        for pattern, handler in self._rules:
            m = pattern.search(cleaned)
            if m:
                plan = handler(m)
                if plan is not None:
                    return plan
        return None

    def _build(self) -> None:
        s = self.honorific
        P, T = _POLITE, _TAIL

        self._rule(rf"^(?:what(?:'s| is) the time|what time is it|(?:tell me )?the time|time){T}",
                   lambda m: Plan.say(f"It's {_spoken_time(datetime.now())}, {s}."))
        self._rule(rf"^(?:what(?:'s| is) (?:the |today's )?date|what day is (?:it|today)|today's date){T}",
                   lambda m: Plan.say(f"Today is {datetime.now().strftime('%A, %B %d').replace(' 0', ' ')}, {s}."))

        name = re.escape(self.name.lower())
        self._rule(rf"^(?:(?:hey|hi|hello|yo|good (?:morning|afternoon|evening))(?: there)?(?: {name})?|{name}|are you (?:there|up)|you there|wake up|daddy's home){T}",
                   lambda m: Plan.say(self._greeting(), expect_reply=True))
        self._rule(rf"^(?:thanks|thank you|cheers|nice work|good job|well done)(?: {name})?{T}",
                   lambda m: Plan.say(random.choice([
                       f"Always a pleasure, {s}.", f"At your service, {s}.", "My pleasure.",
                       f"Happy to help, {s}."])))
        self._rule(rf"^(?:who are you|what(?:'s| is) your name|identify yourself){T}",
                   lambda m: Plan.say(
                       f"I'm {self.name}, your personal assistant. I run your desktop, keep an eye on "
                       f"the system, and occasionally make clever remarks."))
        self._rule(rf"^(?:what can you do|help|what are your (?:capabilities|abilities)){T}",
                   lambda m: Plan.say(
                       "I can launch apps and websites, search the web, control volume and media, take "
                       "screenshots, set timers, check the weather, run diagnostics, remember things "
                       f"about you, and lock or power down the machine. Or just talk to me, {s}."))

        self._rule(rf"^(?:that(?:'s| is| will be) all|dismissed|standby|stand by|go to standby|never ?mind|nothing|cancel|stop|shut up|be quiet|hide|close the hud|go away|goodbye|bye){T}",
                   lambda m: Plan.do(random.choice([f"Standing by, {s}.", f"Very good, {s}.", "As you wish."]),
                                     "hud_hide"))

        self._rule(rf"^(?:clear|reset|wipe) (?:your |the )?(?:memory|conversation|context){T}",
                   lambda m: Plan.say("Conversation memory cleared. Fresh start.", meta={"clear_memory": True}))

        self._rule(rf"^{P}(?:abort|cancel|stop) (?:the )?(?:shutdown|restart|reboot|power ?down)(?: sequence)?{T}",
                   lambda m: Plan.do(f"Shutdown aborted, {s}.", "cancel_shutdown"))
        self._rule(rf"^{P}(?:shut ?down|power (?:down|off)|turn off)(?: the| my)?(?: computer| pc| system| machine| everything)?{T}",
                   lambda m: Plan.do("Initiating shutdown sequence.", "shutdown"))
        self._rule(rf"^{P}(?:restart|reboot)(?: the| my)?(?: computer| pc| system| machine)?{T}",
                   lambda m: Plan.do("Rebooting.", "restart"))
        self._rule(rf"^{P}(?:put )?(?:the |my )?(?:computer|pc|system|machine) to sleep{T}|^{P}(?:sleep|hibernate)(?: the| my)? (?:computer|pc|system|machine){T}",
                   lambda m: Plan.do("Putting the system to sleep.", "sleep"))
        self._rule(rf"^{P}lock(?: the| my)?(?: computer| pc| screen| system| workstation| it)?(?: up)?{T}",
                   lambda m: Plan.do(f"Locking the workstation, {s}.", "lock_screen"))
        self._rule(rf"^{P}(?:take a |grab a |capture (?:the |a )?)?screen ?(?:shot|grab|capture)(?: of (?:the|my) screen)?{T}|^{P}capture (?:the|my) screen{T}",
                   lambda m: Plan.do("Screen captured.", "screenshot"))

        self._rule(rf"^{P}(?:turn|crank|bump) (?:the )?(?:volume|sound|it) up{T}|^{P}(?:turn |crank )?up the (?:volume|sound){T}|^{P}(?:louder|volume up|increase (?:the )?volume|raise (?:the )?volume){T}",
                   lambda m: Plan.do("Volume up.", "volume_up"))
        self._rule(rf"^{P}turn (?:the )?(?:volume|sound|it) down{T}|^{P}turn down the (?:volume|sound){T}|^{P}(?:quieter|softer|volume down|decrease (?:the )?volume|lower (?:the )?volume){T}",
                   lambda m: Plan.do("Volume down.", "volume_down"))
        self._rule(rf"^{P}(?:un)?mute(?: the)?(?: volume| sound| audio| it)?{T}",
                   lambda m: Plan.do("Done.", "volume_mute"))
        self._rule(rf"^{P}(?:set |change |put )?(?:the )?volume (?:to |at )?(\d{{1,3}})(?: ?%| percent)?{T}",
                   lambda m: self._volume_set(m.group(1)))

        self._rule(rf"^{P}(?:next|skip)(?: (?:track|song|this|it))?{T}",
                   lambda m: Plan.do("Skipping.", "media_next"))
        self._rule(rf"^{P}(?:previous|last|go back)(?: (?:track|song))?{T}",
                   lambda m: Plan.do("Going back.", "media_prev"))
        self._rule(rf"^{P}(?:pause|resume|play|unpause)(?: (?:the )?(?:music|song|track|media|video|it))?{T}",
                   lambda m: Plan.do("Done.", "media_play_pause"))

        self._rule(rf"^{P}(?:search |look up |find )?(?:on )?youtube (?:for )?(.+?){T}|^{P}(?:search|look up|find) (.+?) on youtube{T}|^{P}play (.+?) on youtube{T}",
                   lambda m: self._search("youtube", next(g for g in m.groups() if g)))
        self._rule(rf"^{P}(?:google|search (?:google |the web |online )?for|search|look up) (.+?){T}",
                   lambda m: self._search("google", m.group(1)))

        self._rule(rf"^{P}(?:open|launch|start|run|fire up|boot up|load up|bring up|pull up|go to|navigate to) (?:up )?(?:the |my )?(.+?){T}",
                   lambda m: self._open(m.group(1)))

    def _greeting(self) -> str:
        part = _part_of_day(datetime.now())
        return random.choice([
            f"Good {part}, {self.honorific}. What can I do for you?",
            f"At your service, {self.honorific}.",
            f"Online and ready, {self.honorific}.",
            f"Good {part}. All systems nominal.",
        ])

    def _volume_set(self, raw: str) -> Plan:
        level = max(0, min(100, int(raw)))
        return Plan.do(f"Volume set to {level} percent.", "volume_set", str(level))

    def _search(self, engine: str, query: str) -> Optional[Plan]:
        query = query.strip()
        if not query:
            return None
        if engine == "youtube":
            return Plan.do(f"Searching YouTube for {query}.", "search_youtube", query)
        return Plan.do(f"Searching for {query}.", "search_google", query)

    def _open(self, target: str) -> Optional[Plan]:
        target = target.strip()
        if not target or len(target.split()) > 4:
            return None
        bare = re.sub(r"^(?:my |the )", "", target).replace(" folder", "").strip()
        if bare in KNOWN_FOLDERS:
            return Plan.do(f"Opening {bare}.", "open_file", bare)
        spoken_url = re.sub(r"\s+dot\s+", ".", target).replace(" ", "")
        if _URL_RE.match(spoken_url) and "." in spoken_url:
            return Plan.do(f"Opening {spoken_url}.", "open_url", spoken_url)
        return Plan.do(f"Opening {target}.", "open_app", target)
