"""English for the pages and reports ([ui] language = "en" in studio.toml; "zh" keeps the Chinese they were written in).

The review page, the editing page and the reports (intake, recording diff, QA) carry their wording in Chinese in the
code. With [ui] language = "en" each known phrase is replaced by its English, longest phrase first; variables sit
between the phrases, so they pass through. To add a language, add a table like EN and pick it in `_table()`.
    page(html) / loc(text)   whole page or report        t(phrase)   one phrase
"""
import gs_env

EN = {
    # ---- review page
    "棚拍审片": "Review", "棚拍剪辑": "Edit",
    "一支一行，点名字看最新的那一版。": "One row per piece. Click a name to open its newest build.",
    "人声初剪": "voice cut", "动画 + 配乐 480p": "animation + music 480p",
    "换到 ${ep.startsWith('s')?'':isS(x)?'短片 · ':'正片 · '}": "switch to ${ep.startsWith('s')?'':isS(x)?'short · ':'long video · '}",
    "' · 短片'": "' · short'", "' · 正片'": "' · long video'",
    ">剪辑</a>": ">edit</a>",
    "← 全部影片": "← all pieces", "剪辑页（这一支，用耳朵修）": "editing page (this piece: fix it by ear)",
    "<b>键盘：</b>空格＝播放 / 暂停 · ← →＝退 / 进 2 秒（按住 Shift 是 0.5 秒）· ↑ ↓＝上一个 / 下一个镜头 · 1–9＝点第几个意见 · E＝去剪辑页 · 在打字格里按 Esc 离开格子":
        "<b>Keys:</b> Space = play / pause · ← → = back / forward 2 s (with Shift: 0.5 s) · ↑ ↓ = previous / next shot · 1–9 = that note · E = editing page · Esc leaves the text box",
    "要补充的话（可以不写；先写字再点意见）": "Anything to add (optional; type first, then tap a note)",
    "意见会记下时间、镜头和当时的字幕。": "Each note keeps the time, the shot and the subtitle on screen.",
    " · 镜头 ${s.id}": " · shot ${s.id}", "（没有字幕）": "(no subtitle)",
    "停顿太长": "pause too long", "停顿太短": "pause too short", "重念没剪掉": "retake left in", "这句被切到": "line clipped",
    "字幕有错": "subtitle wrong", "这句想重录": "re-record this", "事实要查": "check this fact", "画面 / 镜头": "picture / shot", "其他": "other",
    # ---- editing page
    "保存 (Ctrl+S)": "Save (Ctrl+S)", "保存并重做人声初剪": "Save and rebuild the voice cut", "撤销 (Ctrl+Z)": "Undo (Ctrl+Z)",
    ">全部影片</a>": ">all pieces</a>", "审片页（这一支）": "review page (this piece)",
    "点左边一个镜头。亮的地方是影片里留着的声音，暗的地方是剪掉的。": "Pick a shot on the left. Bright = sound kept in the video, dark = cut away.",
    "▶ 听这个镜头（照现在剪的）": "▶ Play this shot (as it is cut now)", "▶ 听选起来的": "▶ Play the selection", "■ 停": "■ Stop",
    "✂ 剪掉选起来的 (X)": "✂ Cut the selection (X)", "↩ 把选起来的放回去 (R)": "↩ Put the selection back (R)", "还原这个镜头": "Reset this shot",
    "<b>键盘：</b>空格＝播放 / 停（有选起来就只播那一段）· X＝剪掉 · R＝放回去 · ↑ ↓＝上一个 / 下一个镜头 · Ctrl+Z＝撤销 · Ctrl+S＝保存 · Esc＝取消选取（在字幕格子里按 Esc 是离开格子）":
        "<b>Keys:</b> Space = play / stop (only the selection when there is one) · X = cut · R = put back · ↑ ↓ = previous / next shot · Ctrl+Z = undo · Ctrl+S = save · Esc = clear the selection (in a subtitle box: leave the box)",
    "在波形上按住拖一段就是选起来。选到镜头开头或结尾外面再按「放回去」，镜头就会往外延长；从开头或结尾往里选再「剪掉」，就是把头尾收短。字幕直接在左边改字；一句太长，在要断开的地方打一个 <b>/</b>（例如「前半句/后半句」），保存后就会变成前后两句字幕，各自跟着你讲到的时候出现。":
        "Drag on the waveform to select. Select past the start or end of the shot and press Put back to make the shot longer; select inwards from the start or end and press Cut to trim it. Correct subtitles in the boxes on the left; to split a long one, type a <b>/</b> where it should break (first half/second half): after saving it becomes two subtitles, each shown when you say it.",
    "换到正片": "switch to the long video", "换到短片": "switch to the short",
    "s.kind==='cam'?'出镜':'旁白'": "s.kind==='cam'?'on camera':'narration'",
    "} 秒</span>": "} s</span>", " · 改过": " · changed",
    "msg('还没保存')": "msg('not saved yet')", "dirty?'还没保存':''": "dirty?'not saved yet':''", "dirty?'还没保存':undefined": "dirty?'not saved yet':undefined",
    "msg('读声音…')": "msg('loading sound…')",
    " · 录音 ${s.src} · 从 ${fmt(s.in)} 到 ${fmt(s.out)} 秒 · 中间剪掉 ${s.cut.length} 处": " · recording ${s.src} · from ${fmt(s.in)} to ${fmt(s.out)} s · ${s.cut.length} cut(s) inside",
    " · 选起来 ${fmt(range[0])}–${fmt(range[1])}（${fmt(range[1]-range[0])} 秒）": " · selected ${fmt(range[0])}–${fmt(range[1])} (${fmt(range[1]-range[0])} s)",
    "没有可以撤销的": "nothing to undo",
    "`保存了（${r.shots} 个镜头、${r.text} 句字幕改过）`": "`saved (${r.shots} shot(s), ${r.text} subtitle(s) changed)`", "'保存失败：'": "'not saved: '",
    "重做人声初剪，要一两分钟…": "rebuilding the voice cut, a minute or two…", "做好了，可以去审片页看": "done: open the review page", "'没做成：'": "'failed: '",
    "网址要带 ?id=<编号>": "the address needs ?id=<piece id>", 'lang="zh"': 'lang="en"',
    # ---- intake report
    "# 录音整理 · ": "# Intake · ", "intake.py 自动生成，来源：": "Made by intake.py from ",
    "。⚠ 的那几行要导演确认；确认后改 intake-plan.json 的 dest / status，再跑 `intake.py ": ". Rows marked ⚠ need the director; after that, set dest / status in intake-plan.json and run `intake.py ",
    "| 文件 | 听到的编号 | 归到 | 涵盖段落 | 吻合 | 同步延迟 | 状态 |": "| File | Slate heard | Filed as | Sections covered | Match | Sync lag | Status |",
    " 补录": " pickup", "念的编号是 ": "the slate says ", "，可是内容不像这一段（": ", but the content does not sound like that section (",
    "没听到编号，按内容判断": "no slate heard: filed by content", "编号“": "slate “", "”不在这一批": "” is not in this batch",
    "听不出编号，内容也对不上": "no slate heard and the content matches nothing",
    "没听到编号，而且录音里有 ": "no slate heard, and ", " 对不上这几段": " of the recording does not match these sections",
    " 有两个录音，默认用较晚的 ": " has two recordings: the later one is used, ", "；这个移到 unused/": "; this one goes to unused/",
    " 读不到声音轨": " no audio track could be read", " 用相机外接麦的声音": " sound from the camera's own microphone",
    # ---- recording-diff report
    "# 录音对照 · ": "# Recording vs script · ",
    "> 自动生成（recording_diff.py）。用的是不带台本提示的转写，时间是录音档里的位置。": "> Made by recording_diff.py from the transcript without a script prompt; times are positions in the recording.",
    "> 字幕和剪辑照导演实际说的；只有**事实**说错、或重念 / 口误不清楚时才问导演。": "> Subtitles and cuts follow what was actually said; ask the director only when a **fact** changed or a retake / slip is unclear.",
    "这个录音没有对上台本的任何段落（补录、测试片，或段落已经在别的录音里）。": "This recording matches no section of the script (a pickup, a test clip, or its section is in another recording).",
    "⚠ 还没有转写（先跑 transcribe.py）": "⚠ no transcript yet (run intake / transcribe.py first)",
    "没有不带提示的转写：重念可能被吞掉，要人工看": "no unprompted transcript: retakes may be swallowed, check by hand",
    "Whisper 在静音处编了“": "Whisper invented “", "…”，这一段已略过": "…” in a silence; that segment is ignored",
    "不带提示的转写太不可靠，改用带提示的：重念可能被吞掉，要人工看": "the unprompted transcript is too unreliable, the prompted one is used: retakes may be swallowed, check by hand",
    "（台本里找不到这一段）": "(not found in the script)", " · 吻合 ": " · match ",
    "没念到": "not said", "多出来": "extra", "说法不同": "said differently", " · 有数字，核对事实": " · has a number: check the fact",
    "**可能的重念 / 口误**（同一句说了不止一次）：": "**Possible retakes / slips** (the same phrase said more than once):",
    "| 时间 | 段落 | 类型 | 台本 | 实际说的 |": "| Time | Section | Kind | Script | Actually said |",
    "停顿 > 1.5 秒：": "Pauses > 1.5 s: ", "Whisper 不确定的词（别据此改字幕，先看音量）：": "Words Whisper was unsure of (do not change subtitles from these; check the loudness first): ",
    "跟台本一致。": "Matches the script.", "## 没有录音的段落": "## Sections with no recording",
    # ---- QA report
    "## 台本 check_script": "## Script (check_script)", "## 剪点 ": "## Cuts ", "## 画面自查页": "## Review sheets",
    "看每一页：字幕带没有文字、没有方块字、标签在旁边、没有重复旁白的卡片、出现时间对字。":
        "Look at every page: no text in the subtitle band, no missing glyphs, labels beside their subject, no card that repeats the narration, things appear on their word.",
    "（节奏检查没跑完：": "(the rhythm check did not finish: ", "## 节奏": "## Rhythm (what directors ask to fix most)",
    "停顿、接点、重念都没发现问题。": "No problem found with pauses, joins or retakes.",
    "## 没有来源标注的镜头": "## Shots with no source note",
    "（逐个确认：有事实就要来源，纯示意要写“示意图”）": " (check each: a fact needs its source, a pure illustration says it is a diagram)",
    "全部都有来源或“示意图”。": "Every shot has a source or a diagram note.",
    " 停顿 ": " pause of ", " 秒（原档 ": " s (in the recording at ", "s 起）": " s)",
    " 剪接点只留 ": " join leaves only ", " 秒空气（原档 ": " s of air (recording ", "s），听起来会像被切": " s): it will sound clipped",
    " 接上一个镜头只留 ": " joins the previous shot with only ", " 秒空气": " s of air",
    "”说了两次，台本只有一次：重念没剪掉？": "” is said twice, the script has it once: a retake left in?",
    "、": ", ", "，": ", ", "（": " (", "）": ")", "：": ": ", "“": "\"", "”": "\"",
}


def _table():
    return EN if gs_env.UI != "zh" else {}


def loc(text):
    for zh in sorted(_table(), key=len, reverse=True):
        if zh in text:
            text = text.replace(zh, _table()[zh])
    return text


def page(html):
    """A page in the studio's language. The last rows of the table (single punctuation marks) are for reports only."""
    T = _table()
    for zh in sorted((k for k in T if len(k) > 1), key=len, reverse=True):
        if zh in html:
            html = html.replace(zh, T[zh])
    return html


def t(phrase):
    return _table().get(phrase, phrase)
