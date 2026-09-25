"""All user-facing text of the bot, in Uzbek and English.

A chat's language is chosen with /lang, or guessed from Telegram's own language_code the first time
it links. Values are HTML (the bot sends parse_mode=HTML), so anything user-supplied — issue
titles, comments, usernames — must be passed through html.escape by the caller first.
"""

DEFAULT_LANG = "uz"
LANGS = ("uz", "en")

STRINGS = {
    "uz": {
        "linked": "✅ Telegram DevTrack'ga ulandi.",
        "linked_hint": "Buyruqlar ro'yxati: /help",
        "link_expired": "Havola muddati tugagan. DevTrack Sozlamalariga qaytib, qayta urinib ko'ring.",
        "not_linked": "Bu chat hali DevTrack akkauntiga ulanmagan. DevTrack → Sozlamalar → «Telegram'ni ulash» tugmasini bosing.",
        "welcome": "👋 Salom! Men DevTrack botiman: vazifalaringizni ko'rsataman, yangilarini yarataman va muhim yangiliklar haqida xabar beraman.",
        "help": (
            "<b>Buyruqlar</b>\n"
            "/tasks — mening ochiq vazifalarim\n"
            "/overdue — muddati o'tganlar\n"
            "/soon — muddati yaqinlar (3 kun)\n"
            "/projects — loyihalar va bajarilish\n"
            "/health <i>id</i> — loyiha salomatligi\n"
            "/new <i>[loyiha id]</i> <i>sarlavha</i> — yangi vazifa\n"
            "/done <i>id</i> — vazifani bajarilgan deb belgilash\n"
            "/status <i>id holat</i> — holatni o'zgartirish\n"
            "/comment <i>id matn</i> — izoh qoldirish\n"
            "/mute, /unmute — bildirishnomalarni o'chirish/yoqish\n"
            "/lang <i>uz|en</i> — til\n"
            "/me — men kimman\n"
            "/unlink — DevTrack'dan uzish"
        ),
        "me": "👤 <b>{username}</b>\nIsh maydonlari: {workspaces}",
        "tasks_title": "📋 <b>Ochiq vazifalarim</b> ({total})",
        "overdue_title": "⏰ <b>Muddati o'tgan vazifalar</b> ({total})",
        "soon_title": "🗓 <b>Muddati yaqin vazifalar</b> ({total})",
        "tasks_more": "…va yana {count} ta. Hammasini DevTrack'da ko'ring.",
        "tasks_empty": "🎉 Bu yerda hozircha hech narsa yo'q.",
        "overdue_tag": "muddati o'tgan · {date}",
        "due_tag": "muddat: {date}",
        "projects_title": "📁 <b>Loyihalar</b>",
        "projects_empty": "Hozircha loyiha yo'q.",
        "project_line": "{name} — {progress}% · {open} ta ochiq",
        "health_title": "🩺 <b>{name}</b> salomatligi: <b>{score}</b> — {status}",
        "health_capped": "⚠️ Baho pasaytirildi: {reasons}",
        "health_low_confidence": "ℹ️ Vazifalar kam — baho taxminiy.",
        "health_risks": "<b>Xavflar</b>",
        "health_usage": "Foydalanish: /health <i>loyiha id</i>. Loyiha id'larini /projects dan oling.",
        "new_usage": "Foydalanish: /new <i>[loyiha id]</i> <i>sarlavha</i>",
        "new_pick_project": "Qaysi loyihada? Loyiha id'sini ko'rsating:\n{projects}\n\nMasalan: /new {example} Sarlavha",
        "new_no_projects": "Vazifa yaratish uchun avval DevTrack'da loyiha yarating.",
        "created": "✅ Vazifa yaratildi: <b>#{id}</b> {title}",
        "done_usage": "Foydalanish: /done <i>vazifa id</i>",
        "status_usage": "Foydalanish: /status <i>vazifa id holat</i>\nHolatlar: {statuses}",
        "status_changed": "✅ <b>#{id}</b> {title} → {status}",
        "comment_usage": "Foydalanish: /comment <i>vazifa id matn</i>",
        "commented": "💬 Izoh <b>#{id}</b> vazifasiga qo'shildi.",
        "lang_usage": "Foydalanish: /lang uz yoki /lang en",
        "lang_set": "🇺🇿 Til: o'zbekcha.",
        "muted": "🔕 Bildirishnomalar o'chirildi. Yoqish: /unmute",
        "unmuted": "🔔 Bildirishnomalar yoqildi.",
        "unlinked": "Chat DevTrack'dan uzildi. Qayta ulash uchun DevTrack → Sozlamalar.",
        "unknown": "Tushunmadim. Buyruqlar ro'yxati: /help",
        "err_forbidden": "Sizda bu amal uchun ruxsat yo'q.",
        "err_not_creator": "Vazifani faqat uni yaratgan foydalanuvchi o'zgartira oladi.",
        "err_not_found": "Topilmadi.",
        "err_invalid": "Noto'g'ri qiymat.",
        "err_generic": "DevTrack bilan bog'lanib bo'lmadi. Birozdan keyin qayta urinib ko'ring.",
        "btn_open": "Ochish",
        "btn_done": "✅ Bajarildi",
        "btn_health": "🩺 {name}",
        "cb_done": "Bajarildi ✅",
        "cb_failed": "Bajarilmadi",
        "status.backlog": "Zaxira",
        "status.todo": "Qilinadigan",
        "status.in_progress": "Jarayonda",
        "status.in_review": "Ko'rib chiqilmoqda",
        "status.done": "Bajarildi",
        "priority.urgent": "shoshilinch",
        "priority.high": "yuqori",
        "priority.medium": "o'rta",
        "priority.low": "past",
        "priority.none": "",
        "health.healthy": "sog'lom",
        "health.needs_attention": "e'tibor talab",
        "health.at_risk": "xavf ostida",
        "factor.task_progress": "Reja bo'yicha bajarilish",
        "factor.deadline": "Muddatlar",
        "factor.bug_rate": "Xatolar bosimi",
        "factor.development_activity": "Faollik",
        "factor.flow": "Ish oqimi",
        "cap.critical_bug": "shoshilinch xato bir haftadan beri ochiq",
        "cap.mass_overdue": "muddatlarning aksariyati kechikkan",
        "cap.abandoned": "bir oydan beri faollik yo'q",
        "risk.stale_in_progress": "{count} ta vazifa {days} kundan ortiq jarayonda",
        "risk.stale_review": "{count} ta vazifa {days} kundan ortiq ko'rib chiqilishini kutmoqda",
        "risk.stale_pull_requests": "{count} ta pull request {days} kundan ortiq ochiq",
        "risk.overdue": "{count} ta vazifaning muddati o'tgan",
        "risk.urgent_bugs": "{count} ta yuqori/shoshilinch xato hal qilinmagan",
        "risk.no_recent_activity": "{days} kundan beri faollik yo'q",
        "n.issue_assigned": "📌 <b>{actor}</b> sizga vazifa tayinladi:\n{title}",
        "n.issue_assigned_anon": "📌 Sizga vazifa tayinlandi:\n{title}",
        "n.commented": "💬 <b>{actor}</b> izoh qoldirdi — {title}",
        "n.mentioned": "🔔 <b>{actor}</b> sizni eslatdi — {title}",
        "n.workspace_invited": "👋 Siz «{title}» ish maydoniga taklif qilindingiz.",
        "n.project_member_added": "📁 Siz «{title}» loyihasiga qo'shildingiz.",
        "n.digest_title": "☀️ <b>Bugungi xulosa</b>: {overdue} ta muddati o'tgan, {today} ta bugun tugaydi",
        "n.generic": "🔔 {title}",
    },
    "en": {
        "linked": "✅ Your Telegram is now linked to DevTrack.",
        "linked_hint": "See the commands: /help",
        "link_expired": "This link has expired. Go back to DevTrack Settings and try again.",
        "not_linked": "This chat is not linked to a DevTrack account yet. In DevTrack open Settings and press “Connect Telegram”.",
        "welcome": "👋 Hi! I'm the DevTrack bot: I show your tasks, create new ones and tell you about what matters.",
        "help": (
            "<b>Commands</b>\n"
            "/tasks — my open tasks\n"
            "/overdue — overdue ones\n"
            "/soon — due within 3 days\n"
            "/projects — projects and progress\n"
            "/health <i>id</i> — project health\n"
            "/new <i>[project id]</i> <i>title</i> — new task\n"
            "/done <i>id</i> — mark a task done\n"
            "/status <i>id status</i> — change status\n"
            "/comment <i>id text</i> — leave a comment\n"
            "/mute, /unmute — turn notifications off/on\n"
            "/lang <i>uz|en</i> — language\n"
            "/me — who am I\n"
            "/unlink — disconnect from DevTrack"
        ),
        "me": "👤 <b>{username}</b>\nWorkspaces: {workspaces}",
        "tasks_title": "📋 <b>My open tasks</b> ({total})",
        "overdue_title": "⏰ <b>Overdue tasks</b> ({total})",
        "soon_title": "🗓 <b>Tasks due soon</b> ({total})",
        "tasks_more": "…and {count} more. See them all in DevTrack.",
        "tasks_empty": "🎉 Nothing here right now.",
        "overdue_tag": "overdue · {date}",
        "due_tag": "due {date}",
        "projects_title": "📁 <b>Projects</b>",
        "projects_empty": "No projects yet.",
        "project_line": "{name} — {progress}% · {open} open",
        "health_title": "🩺 <b>{name}</b> health: <b>{score}</b> — {status}",
        "health_capped": "⚠️ Score held back: {reasons}",
        "health_low_confidence": "ℹ️ Only a few issues so far — a rough guide.",
        "health_risks": "<b>Risks</b>",
        "health_usage": "Usage: /health <i>project id</i>. Get project ids from /projects.",
        "new_usage": "Usage: /new <i>[project id]</i> <i>title</i>",
        "new_pick_project": "Which project? Give its id:\n{projects}\n\nFor example: /new {example} Title",
        "new_no_projects": "Create a project in DevTrack first, then you can add tasks here.",
        "created": "✅ Task created: <b>#{id}</b> {title}",
        "done_usage": "Usage: /done <i>task id</i>",
        "status_usage": "Usage: /status <i>task id status</i>\nStatuses: {statuses}",
        "status_changed": "✅ <b>#{id}</b> {title} → {status}",
        "comment_usage": "Usage: /comment <i>task id text</i>",
        "commented": "💬 Comment added to <b>#{id}</b>.",
        "lang_usage": "Usage: /lang uz or /lang en",
        "lang_set": "🇬🇧 Language: English.",
        "muted": "🔕 Notifications are off. Turn them back on with /unmute",
        "unmuted": "🔔 Notifications are on.",
        "unlinked": "This chat is disconnected from DevTrack. To link it again use DevTrack → Settings.",
        "unknown": "I didn't get that. See the commands: /help",
        "err_forbidden": "You are not allowed to do that.",
        "err_not_creator": "Only the person who created a task can change it.",
        "err_not_found": "Not found.",
        "err_invalid": "That value is not valid.",
        "err_generic": "Couldn't reach DevTrack. Please try again in a moment.",
        "btn_open": "Open",
        "btn_done": "✅ Done",
        "btn_health": "🩺 {name}",
        "cb_done": "Done ✅",
        "cb_failed": "Couldn't do that",
        "status.backlog": "Backlog",
        "status.todo": "Todo",
        "status.in_progress": "In progress",
        "status.in_review": "In review",
        "status.done": "Done",
        "priority.urgent": "urgent",
        "priority.high": "high",
        "priority.medium": "medium",
        "priority.low": "low",
        "priority.none": "",
        "health.healthy": "healthy",
        "health.needs_attention": "needs attention",
        "health.at_risk": "at risk",
        "factor.task_progress": "Progress vs plan",
        "factor.deadline": "Deadlines",
        "factor.bug_rate": "Bug pressure",
        "factor.development_activity": "Activity",
        "factor.flow": "Work flow",
        "cap.critical_bug": "an urgent bug has been open for over a week",
        "cap.mass_overdue": "most deadlines are blown",
        "cap.abandoned": "no activity for a month",
        "risk.stale_in_progress": "{count} task(s) in progress for over {days} days",
        "risk.stale_review": "{count} task(s) waiting for review for over {days} days",
        "risk.stale_pull_requests": "{count} pull request(s) open for over {days} days",
        "risk.overdue": "{count} issue(s) past their due date",
        "risk.urgent_bugs": "{count} unresolved high/urgent bug(s)",
        "risk.no_recent_activity": "no activity for {days} days",
        "n.issue_assigned": "📌 <b>{actor}</b> assigned you a task:\n{title}",
        "n.issue_assigned_anon": "📌 You were assigned a task:\n{title}",
        "n.commented": "💬 <b>{actor}</b> commented — {title}",
        "n.mentioned": "🔔 <b>{actor}</b> mentioned you — {title}",
        "n.workspace_invited": "👋 You were invited to the “{title}” workspace.",
        "n.project_member_added": "📁 You were added to the “{title}” project.",
        "n.digest_title": "☀️ <b>Today's digest</b>: {overdue} overdue, {today} due today",
        "n.generic": "🔔 {title}",
    },
}


def normalize_lang(value):
    """'en-GB' / 'EN' / None -> 'en' | 'uz' (Telegram's own code is only a first guess)."""
    code = (value or "").lower().split("-")[0]
    return code if code in LANGS else DEFAULT_LANG


def tr(lang, key, **params):
    template = STRINGS.get(lang, STRINGS[DEFAULT_LANG]).get(key) or STRINGS["en"].get(key, key)
    return template.format(**params) if params else template
