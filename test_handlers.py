import pytest

import backend_client
import handlers
import storage
import telegram_client
from backend_client import BackendError
from signing import sign_user_id

CHAT = 500
USER = 42


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()


@pytest.fixture
def sent(monkeypatch):
    """Every message the bot sends: (chat_id, text, reply_markup)."""
    messages = []
    monkeypatch.setattr(telegram_client, "send_message", lambda chat_id, text, reply_markup=None: messages.append((chat_id, text, reply_markup)))
    return messages


@pytest.fixture
def answers(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_client, "answer_callback_query", lambda cid, text="": calls.append((cid, text)))
    return calls


@pytest.fixture
def linked():
    storage.upsert_link(USER, CHAT, "alice", "en")


def say(text, chat=CHAT, language_code=None, username="alice"):
    message = {"chat": {"id": chat}, "from": {"username": username, **({"language_code": language_code} if language_code else {})}, "text": text}
    handlers.handle_update({"message": message})


def issue(id=1, title="Fix it", **overrides):
    return {"id": id, "title": title, "status": "todo", "priority": "high", "due_date": None, "overdue": False,
            "can_edit": True, "path": f"/issues/{id}", "project": {"id": 1, "name": "P"}, **overrides}


def stub(monkeypatch, **functions):
    for name, fn in functions.items():
        monkeypatch.setattr(backend_client, name, fn)


def last(sent):
    return sent[-1][1]


# --- linking and language -----------------------------------------------------------------------


def test_start_with_a_valid_token_links_the_chat_and_greets_in_both_languages(sent):
    say(f"/start {sign_user_id(USER, 'test-link-secret')}", language_code="en-US")
    assert storage.get_link(USER)["chat_id"] == CHAT
    text = last(sent)
    assert "ulandi" in text and "linked" in text
    assert storage.get_link(USER)["lang"] == "en"  # guessed from Telegram's language_code


def test_a_chat_without_a_language_hint_defaults_to_uzbek(sent):
    say(f"/start {sign_user_id(USER, 'test-link-secret')}")
    assert storage.get_link(USER)["lang"] == "uz"


def test_start_with_a_bad_token_explains_in_both_languages_and_links_nothing(sent):
    say("/start garbage")
    assert storage.get_link_by_chat(CHAT) is None
    assert "muddati tugagan" in last(sent) and "expired" in last(sent)


def test_start_without_a_token_greets_a_linked_chat_and_guides_an_unlinked_one(sent, linked):
    say("/start")
    assert "DevTrack bot" in last(sent) and "/help" in last(sent)
    say("/start", chat=999, language_code="en")
    assert "Connect Telegram" in last(sent)


def test_help_works_before_linking_in_the_users_language(sent):
    say("/help", chat=777, language_code="en")
    assert "Commands" in last(sent)
    say("/help", chat=777, language_code="uz")
    assert "Buyruqlar" in last(sent)


def test_every_other_command_asks_an_unlinked_chat_to_link_first(sent):
    say("/tasks", chat=888, language_code="en")
    assert "not linked" in last(sent)


def test_lang_switches_and_persists(sent, linked):
    say("/lang uz")
    assert storage.get_link_by_chat(CHAT)["lang"] == "uz"
    say("/help")
    assert "Buyruqlar" in last(sent)
    say("/lang xx")
    assert "/lang uz" in last(sent)


def test_mute_unmute_and_unlink(sent, linked):
    say("/mute")
    assert storage.get_link_by_chat(CHAT)["muted"] == 1
    say("/unmute")
    assert storage.get_link_by_chat(CHAT)["muted"] == 0
    say("/unlink")
    assert storage.get_link_by_chat(CHAT) is None
    assert "disconnected" in last(sent)


def test_unknown_input_gets_a_hint(sent, linked):
    say("/frobnicate")
    assert "/help" in last(sent)
    say("just chatting")
    assert "/help" in last(sent)


def test_parse_command_handles_bot_suffix_and_arguments():
    assert handlers.parse_command("/tasks@DevTrackBot overdue") == ("tasks", "overdue")
    assert handlers.parse_command("/NEW  hello") == ("new", " hello")
    assert handlers.parse_command("hello") is None


# --- tasks ----------------------------------------------------------------------------------------


def test_tasks_lists_issues_with_overdue_marks_and_only_offers_done_where_it_works(sent, linked, monkeypatch):
    data = {"total": 3, "issues": [
        issue(1, "Late one", overdue=True, due_date="2026-09-20"),
        issue(2, "Mine <b>", can_edit=True),
        issue(3, "Not mine", can_edit=False),
    ]}
    stub(monkeypatch, issues=lambda user_id, scope="mine": data)
    say("/tasks")
    _, text, markup = sent[-1]
    assert "My open tasks" in text and "(3)" in text
    assert "🔴" in text and "overdue · 20.09" in text
    assert "Mine &lt;b&gt;" in text  # user text is escaped, never interpreted as markup
    buttons = [b for row in markup["inline_keyboard"] for b in row]
    assert {b["callback_data"] for b in buttons} == {"done:1", "done:2"}  # no Done for #3


def test_task_buttons_link_into_the_app_only_when_it_is_publicly_reachable(sent, linked, monkeypatch):
    stub(monkeypatch, issues=lambda user_id, scope="mine": {"total": 1, "issues": [issue(1, can_edit=False)]})
    say("/tasks")
    assert sent[-1][2] is None  # localhost is not a valid Telegram button URL
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")
    say("/tasks")
    assert sent[-1][2]["inline_keyboard"][0][0]["url"] == "https://app.example.com/issues/1"


def test_scopes_and_the_more_line(sent, linked, monkeypatch):
    seen = []
    def fake(user_id, scope="mine"):
        seen.append(scope)
        return {"total": 14, "issues": [issue(i) for i in range(10)]}
    stub(monkeypatch, issues=fake)
    say("/overdue")
    say("/soon")
    say("/my")
    assert seen == ["overdue", "soon", "mine"]
    assert "4 more" in last(sent)


def test_an_empty_list_is_celebrated(sent, linked, monkeypatch):
    stub(monkeypatch, issues=lambda user_id, scope="mine": {"total": 0, "issues": []})
    say("/tasks")
    assert "Nothing here" in last(sent)


# --- projects and health ---------------------------------------------------------------------------


def test_projects_list_with_health_buttons(sent, linked, monkeypatch):
    stub(monkeypatch, projects=lambda user_id: {"projects": [{"id": 7, "name": "Payments", "status": "active", "open": 3, "done": 1, "progress": 25}]})
    say("/projects")
    _, text, markup = sent[-1]
    assert "Payments — 25% · 3 open" in text
    assert markup["inline_keyboard"][0][0]["callback_data"] == "health:7"


HEALTH = {"project": {"id": 7, "name": "Payments"}, "score": 61, "status": "needs_attention", "confidence": "low",
          "factors": {"task_progress": 40, "deadline": None, "bug_rate": 90, "development_activity": 100, "flow": 55},
          "capped_by": ["critical_bug"], "risk_details": [{"code": "overdue", "count": 2}, {"code": "stale_pull_requests", "count": 1, "days": 7}]}


def test_health_shows_factors_caps_and_risks_but_skips_unjudged_factors(sent, linked, monkeypatch):
    stub(monkeypatch, project_health=lambda user_id, project_id: HEALTH)
    say("/health 7")
    text = last(sent)
    assert "Payments" in text and "61" in text and "needs attention" in text
    assert "Progress vs plan: <b>40</b>" in text
    assert "Deadlines" not in text  # null factor: nothing to show
    assert "urgent bug has been open for over a week" in text
    assert "2 issue(s) past their due date" in text and "1 pull request(s) open for over 7 days" in text
    assert "rough guide" in text


def test_health_needs_a_project_id(sent, linked):
    say("/health")
    assert "Usage: /health" in last(sent)


# --- creating and changing issues ------------------------------------------------------------------


def test_new_with_an_explicit_project(sent, linked, monkeypatch):
    calls = []
    stub(monkeypatch, create_issue=lambda user_id, project_id, title: calls.append((user_id, project_id, title)) or issue(9, title))
    say("/new 3 Write the docs")
    assert calls == [(USER, 3, "Write the docs")]
    assert "#9" in last(sent) and "Write the docs" in last(sent)


def test_new_uses_the_only_project_and_asks_when_there_are_several(sent, linked, monkeypatch):
    calls = []
    stub(monkeypatch, create_issue=lambda user_id, project_id, title: calls.append((project_id, title)) or issue(9, title))
    stub(monkeypatch, projects=lambda user_id: {"projects": [{"id": 5, "name": "Only"}]})
    say("/new Just a title")
    assert calls == [(5, "Just a title")]

    stub(monkeypatch, projects=lambda user_id: {"projects": [{"id": 5, "name": "A"}, {"id": 6, "name": "B"}]})
    say("/new Ambiguous")
    assert "Which project" in last(sent) and "/new 5 Title" in last(sent)
    assert calls == [(5, "Just a title")]  # nothing created


def test_new_edge_cases(sent, linked, monkeypatch):
    say("/new")
    assert "Usage: /new" in last(sent)
    stub(monkeypatch, projects=lambda user_id: {"projects": []})
    say("/new Something")
    assert "Create a project" in last(sent)


def test_done_marks_the_issue_and_reports(sent, linked, monkeypatch):
    stub(monkeypatch, set_status=lambda user_id, issue_id, status: issue(issue_id, "Ship", status=status))
    say("/done 12")
    assert "#12" in last(sent) and "Done" in last(sent)


def test_only_the_creator_may_change_status_and_the_bot_says_so(sent, linked, monkeypatch):
    def refuse(user_id, issue_id, status):
        raise BackendError(403, "Only the person who created this issue can edit it.")
    stub(monkeypatch, set_status=refuse)
    say("/done 12")
    assert "Only the person who created a task" in last(sent)


def test_status_validates_its_arguments(sent, linked, monkeypatch):
    stub(monkeypatch, set_status=lambda user_id, issue_id, status: issue(issue_id, "T", status=status))
    say("/status 3 in_review")
    assert "In review" in last(sent)
    say("/status 3 nonsense")
    assert "Usage: /status" in last(sent)
    say("/done abc")
    assert "Usage: /done" in last(sent)


def test_comment(sent, linked, monkeypatch):
    calls = []
    stub(monkeypatch, comment=lambda user_id, issue_id, body: calls.append((issue_id, body)) or {})
    say("/comment 4 Looks good to me")
    assert calls == [(4, "Looks good to me")]
    assert "#4" in last(sent)
    say("/comment 4")
    assert "Usage: /comment" in last(sent)


def test_me(sent, linked, monkeypatch):
    stub(monkeypatch, me=lambda user_id: {"id": USER, "username": "jane.dev", "workspaces": [{"id": 1, "name": "Nova Labs"}]})
    say("/me")
    assert "jane.dev" in last(sent) and "Nova Labs" in last(sent)


def test_backend_problems_become_friendly_messages(sent, linked, monkeypatch):
    for status, expected in ((None, "Couldn't reach DevTrack"), (500, "Couldn't reach DevTrack"), (404, "Not found"), (403, "not allowed")):
        def boom(user_id, scope="mine", status=status):
            raise BackendError(status, "x")
        stub(monkeypatch, issues=boom)
        say("/tasks")
        assert expected in last(sent)


def test_handle_update_never_raises(sent, linked, monkeypatch):
    def explode(user_id, scope="mine"):
        raise RuntimeError("bug")
    stub(monkeypatch, issues=explode)
    handlers.handle_update({"message": {"chat": {"id": CHAT}, "from": {}, "text": "/tasks"}})  # must not raise
    handlers.handle_update({})
    handlers.handle_update({"message": {"text": "no chat"}})


# --- callbacks -------------------------------------------------------------------------------------


def callback(data, chat=CHAT):
    handlers.handle_update({"callback_query": {"id": "cb1", "data": data, "from": {}, "message": {"chat": {"id": chat}}}})


def test_the_done_button_completes_the_task_and_answers_the_tap(sent, answers, linked, monkeypatch):
    calls = []
    stub(monkeypatch, set_status=lambda user_id, issue_id, status: calls.append((issue_id, status)) or issue(issue_id))
    callback("done:5")
    assert calls == [(5, "done")]
    assert answers == [("cb1", "Done ✅")]


def test_the_done_button_explains_a_refusal(sent, answers, linked, monkeypatch):
    def refuse(user_id, issue_id, status):
        raise BackendError(403, "nope")
    stub(monkeypatch, set_status=refuse)
    callback("done:5")
    assert "Only the person who created a task" in answers[-1][1]


def test_the_health_button_sends_the_report(sent, answers, linked, monkeypatch):
    stub(monkeypatch, project_health=lambda user_id, project_id: HEALTH)
    callback("health:7")
    assert "Payments" in last(sent)


def test_callbacks_from_unlinked_chats_or_with_junk_data_are_declined(sent, answers, linked):
    callback("done:5", chat=12345)
    callback("done:abc")
    callback("whatever:1")
    # The unlinked chat has no language yet, so it gets the default (Uzbek); the linked one speaks English.
    assert [text for _, text in answers] == ["Bajarilmadi", "Couldn't do that", "Couldn't do that"]
