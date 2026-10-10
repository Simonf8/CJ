import json
import urllib.error
import urllib.request

import pytest

from simon.events import EventBus
from simon.server import HudServer


@pytest.fixture
def server():
    received = []
    srv = HudServer(EventBus(), api={"command": lambda b: received.append(b) or True}, port=47950)
    srv.start()
    srv.received = received
    yield srv
    srv.stop()


def post(srv, path, body, token=None, host=None):
    req = urllib.request.Request(srv.url + path, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Simon-Token", token)
    if host:
        req.add_header("Host", host)
    return urllib.request.urlopen(req, timeout=3)


def test_index_embeds_token(server):
    html = urllib.request.urlopen(server.url, timeout=3).read().decode()
    assert server.token in html


def test_command_requires_token(server):
    with pytest.raises(urllib.error.HTTPError) as err:
        post(server, "api/command", {"text": "shut down"})
    assert err.value.code == 403
    assert server.received == []


def test_command_with_token(server):
    assert post(server, "api/command", {"text": "hi"}, token=server.token).status == 200
    assert server.received == [{"text": "hi"}]


def test_rejects_foreign_host_header(server):
    with pytest.raises(urllib.error.HTTPError) as err:
        post(server, "api/command", {"text": "hi"}, token=server.token, host="evil.example")
    assert err.value.code == 403


def test_static_files_cannot_escape_hud_dir(server):
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(server.url + "..%2f..%2fmain.py", timeout=3)
    assert err.value.code == 404


def test_sticky_status_is_merged():
    bus = EventBus()
    bus.publish("status", llm="online", model="llama3.2")
    bus.publish("status", mic="offline")
    assert bus.last("status")["llm"] == "online"
    assert bus.last("status")["mic"] == "offline"
