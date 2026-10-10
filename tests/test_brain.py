import pytest

from simon.brain import parse_llm_reply


def names(plan):
    return [(a.name, a.target) for a in plan.actions]


@pytest.mark.parametrize("text, expected", [
    ("open chrome", [("open_app", "chrome")]),
    ("could you please launch spotify", [("open_app", "spotify")]),
    ("open youtube dot com", [("open_url", "youtube.com")]),
    ("open my downloads folder", [("open_file", "downloads")]),
    ("search for python decorators", [("search_google", "python decorators")]),
    ("play lofi beats on youtube", [("search_youtube", "lofi beats")]),
    ("turn the volume up", [("volume_up", None)]),
    ("set volume to 140", [("volume_set", "100")]),
    ("next track", [("media_next", None)]),
    ("pause", [("media_play_pause", None)]),
    ("lock my computer", [("lock_screen", None)]),
    ("take a screenshot", [("screenshot", None)]),
    ("that's all", [("hud_hide", None)]),
    ("abort shutdown", [("cancel_shutdown", None)]),
])
def test_local_intents(brain, text, expected):
    plan = brain.think(text)
    assert names(plan) == expected
    assert plan.source == "intent"


@pytest.mark.parametrize("text, skill", [
    ("run diagnostics", "skill:system"),
    ("run a system check", "skill:system"),
    ("start a timer for 5 minutes", "skill:timer"),
])
def test_launch_verbs_defer_to_skills(brain, text, skill):
    plan = brain.think(text)
    assert plan.source == skill and not plan.actions
    brain.think("cancel all timers")


def test_time_answers_without_llm(brain):
    plan = brain.think("what time is it")
    assert plan.response.startswith("It's") and not plan.actions


def test_greeting_keeps_conversation_open(brain):
    assert brain.think("hello simon").expect_reply


def test_power_actions_require_confirmation(brain):
    ask = brain.think("shut down")
    assert ask.actions == [] and ask.expect_reply
    go = brain.think("yes")
    assert names(go) == [("shutdown", "10")]


def test_power_confirmation_can_be_declined(brain):
    brain.think("restart the computer")
    plan = brain.think("no")
    assert plan.actions == [] and "Cancelled" in plan.response


def test_unrelated_reply_drops_pending_confirmation(brain):
    brain.think("shut down")
    plan = brain.think("what time is it")
    assert plan.actions == []
    assert brain.think("yes").actions == []


def test_long_open_requests_go_to_llm(brain):
    plan = brain.think("open the pod bay doors please hal i insist")
    assert plan.source == "fallback"


def test_custom_command_uses_word_boundaries(brain, tmp_path):
    path = tmp_path / "commands.json"
    path.write_text('{"break": [{"action": "open_url", "target": "youtube.com"}]}')
    brain.commands.path = str(path)
    brain.commands._mtime = 0
    brain.commands.reload()
    assert brain.commands.match("time for a break")["name"] == "break"
    assert brain.commands.match("what's for breakfast") is None


def test_parse_llm_reply_structured():
    plan = parse_llm_reply('{"response": "Opening it.", "actions": [{"action": "open_app", "target": "vlc"}]}')
    assert plan.response == "Opening it."
    assert names(plan) == [("open_app", "vlc")]


def test_parse_llm_reply_legacy_and_noise():
    plan = parse_llm_reply('Sure! ```json\n{"action": "volume_up", "target": null, "response": "Louder."}\n``` {"x": 1}')
    assert names(plan) == [("volume_up", None)]
    assert plan.response == "Louder."


def test_parse_llm_reply_rejects_unknown_actions():
    plan = parse_llm_reply('{"response": "Done.", "actions": [{"action": "format_c_drive"}]}')
    assert plan.actions == []


def test_parse_llm_reply_plain_text():
    assert parse_llm_reply("Just chatting.").response == "Just chatting."


def test_parse_llm_reply_braces_inside_strings():
    plan = parse_llm_reply('{"response": "Use {curly} braces?", "actions": []}')
    assert plan.response == "Use {curly} braces?"
    assert plan.expect_reply
