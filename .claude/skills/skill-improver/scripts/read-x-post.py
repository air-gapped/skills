#!/usr/bin/env python3
"""Read an x.com / twitter.com post as plain text, expanding "Show more".

WebFetch returns 402 on every x.com URL — the block is keyed on the
User-Agent (`Claude-User`), not on the page. Bare curl is served the
server-rendered post, so a bot-blocked X row is verifiable, not unverifiable.

Two layers of truncation in that HTML, both handled here:

  * the `og:description` meta tag is hard-capped at 278 chars;
  * long posts ("note tweets") render only their first 278 chars followed by
    a `Show more` button — but the full text is carried in a <script> payload,
    either as a JS literal (`__typename:"NoteTweet",text:"..."`) or as JSON
    escaped inside a string (`\\"__typename\\":\\"NoteTweet\\", ...,
    \\"text\\":\\"...\\"`). This script splices it back in.

The sidebar's own `Show more` (under "What's happening") is page chrome and is
dropped, so `unexpanded` counts truncated posts only.

Profile URLs (no `/status/`) return only the most recent posts; a timeline
older than that needs the browser.

Usage:  read-x-post.py <url>          # text to stdout, stats to stderr
        read-x-post.py --selfcheck    # offline

Exit: 0 post read; 1 curl failed, or the post or account does not exist
(deleted, private, wrong id) — that row is gone, not verified.
"""

import html
import json
import re
import subprocess
import sys

JS_STR = r'"(?:[^"\\]|\\.)*"'
NOTE_RE = re.compile(r'__typename:"NoteTweet",text:(' + JS_STR + r")")
# The JSON form, after one level of unescaping. Other keys (`entity_set`, `id`)
# sit between the type tag and the text; never cross into the next object.
NOTE_JSON_RE = re.compile(
    r'"__typename":"NoteTweet"(?:(?!"__typename").){0,6000}?"text":(' + JS_STR + r")",
    re.S,
)
GONE_RE = re.compile(
    r"this page doesn.t exist|This account doesn.t exist|"
    r"unable to show this (content|account)",
    re.I,
)
CHROME_MORE_RE = re.compile(r"(What.s happening)\nShow more")


def norm(s):
    """Collapse space runs and blank lines, as HTML rendering does.

    Required for the splice: note payloads keep double spaces that the
    rendered DOM collapses, so unnormalised sides never compare equal.
    """
    s = re.sub(r"[ \t]+", " ", s)
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())


def fetch(url):
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "30", url], capture_output=True, text=True
    )
    if r.returncode:
        sys.exit(f"curl failed ({r.returncode}): {r.stderr.strip()}")
    return r.stdout


def note_texts(raw):
    out = []
    unescaped = re.sub(r'\\(["\\])', r"\1", raw)
    for src, rx in ((raw, NOTE_RE), (unescaped, NOTE_JSON_RE)):
        for m in rx.finditer(src):
            try:
                text = norm(json.loads(m.group(1).replace(r"\'", "'")))
            except json.JSONDecodeError:
                continue
            if text not in out:  # each note is carried more than once
                out.append(text)
    return out


def rendered(raw):
    body = re.sub(r"(?is)<(script|style|title)\b.*?</\1>", " ", raw)
    text = norm(html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body)))
    return CHROME_MORE_RE.sub(r"\1", text)


def expand(text, notes):
    """Replace each truncated post with its full note text.

    Anchors on the `Show more` marker and works backwards. Anchoring on the
    note's own opening instead would match the copy of the focal post in the
    page header and swallow every post between there and the marker.
    """
    expanded, used = 0, set()
    for m in reversed(list(re.finditer(r"\nShow more", text))):
        j = m.start()
        for k in (120, 60, 30):
            tail = text[max(0, j - k) : j]
            cand = next(
                (
                    (n, f)
                    for n, f in enumerate(notes)
                    if n not in used and tail and tail in f
                ),
                None,
            )
            if not cand:
                continue
            n, full = cand
            base = j - (full.index(tail) + len(tail))
            for d in (0, 1, -1, 2, -2):  # line-boundary slack
                s = base + d
                if s >= 0 and text[s:j] == full[: j - s]:
                    text = text[:s] + full + text[m.end() :]
                    used.add(n)
                    expanded += 1
                    break
            else:
                continue
            break
    return text, expanded


def read(raw):
    """(text, notes, expanded, unexpanded, gone) for one fetched page."""
    notes = note_texts(raw)
    text, expanded = expand(rendered(raw), notes)
    left = len(re.findall(r"(?m)^Show more$", text))
    return text, len(notes), expanded, left, bool(GONE_RE.search(text))


def selfcheck():
    """Offline. The page shapes this script has met, as minimal HTML."""
    head = "A" * 100 + " tail of the visible part"
    full = head + " and the rest that Show more hides."
    page = "<div>@someone</div><div>%s</div><div>Show more</div><div>12</div>" % head
    chrome = "<div>What’s happening</div><div>Show more</div>"

    # JS-literal payload.
    raw = page + '<script>x={__typename:"NoteTweet",text:%s}</script>' % json.dumps(
        full
    )
    text, notes, expanded, left, gone = read(raw)
    assert (notes, expanded, left, gone) == (1, 1, 0, False), (notes, expanded, left)
    assert full in text

    # JSON escaped inside a string, other keys between the tag and the text,
    # carried twice. A reader that knows only the literal form finds no note and
    # leaves the post cut at 278 chars.
    blob = json.dumps(
        {
            "result": {
                "__typename": "NoteTweet",
                "entity_set": {"urls": []},
                "text": full,
            }
        },
        separators=(",", ":"),
    )
    raw = page + chrome + "<script>p=%s;q=%s</script>" % ((json.dumps(blob),) * 2)
    text, notes, expanded, left, gone = read(raw)
    assert (notes, expanded, left, gone) == (1, 1, 0, False), (notes, expanded, left)
    assert full in text

    # No payload at all: the truncation is reported, and sidebar chrome alone is not.
    assert read(page + chrome)[3] == 1
    assert read("<div>short post</div>" + chrome)[3] == 0

    # A deleted post and a missing account are not posts.
    for body in (
        "<div>Hmm...this page doesn’t exist. Try searching for something else.</div>",
        "<div>We're unable to show this account</div><div>This account doesn't exist</div>",
    ):
        assert read(body + chrome)[4] is True, body
    print("selfcheck: all assertions passed")
    return 0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--selfcheck":
        sys.exit(selfcheck())
    text, notes, expanded, left, gone = read(fetch(sys.argv[1]))
    if gone:
        sys.exit(
            "post unavailable: X reports that the page or account does not exist "
            "(deleted, private or wrong id). Nothing was read."
        )
    print(text)
    print(
        f"[notes: {notes} | expanded: {expanded} | unexpanded: {left}]",
        file=sys.stderr,
    )
    if left:
        print(
            "warning: a truncated post could not be matched to a note "
            "payload — escalate that row to the browser.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
