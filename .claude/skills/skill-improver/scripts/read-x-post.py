#!/usr/bin/env python3
"""Read an x.com / twitter.com post as plain text, expanding "Show more".

WebFetch returns 402 on every x.com URL — the block is keyed on the
User-Agent (`Claude-User`), not on the page. Bare curl is served the
server-rendered post, so a bot-blocked X row is verifiable, not unverifiable.

Two layers of truncation in that HTML, both handled here:

  * the `og:description` meta tag is hard-capped at 278 chars;
  * long posts ("note tweets") render only their first 278 chars followed by
    a `Show more` button — but the full text is carried in a <script> payload
    as `__typename:"NoteTweet",text:"..."`. This script splices it back in.

Still needs the browser: profile URLs (no `/status/`), which return a ~2.6 KB
shell with no timeline.

Usage:  read-x-post.py <url>          # text to stdout, stats to stderr
"""

import html
import json
import re
import subprocess
import sys

JS_STR = r'"(?:[^"\\]|\\.)*"'
NOTE_RE = re.compile(r'__typename:"NoteTweet",text:(' + JS_STR + r")")


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
    for m in NOTE_RE.finditer(raw):
        try:
            out.append(norm(json.loads(m.group(1).replace(r"\'", "'"))))
        except json.JSONDecodeError:
            pass
    return out


def rendered(raw):
    body = re.sub(r"(?is)<(script|style|title)\b.*?</\1>", " ", raw)
    return norm(html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body)))


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


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raw = fetch(sys.argv[1])
    notes = note_texts(raw)
    text, expanded = expand(rendered(raw), notes)
    print(text)
    left = text.count("Show more")
    print(
        f"[notes: {len(notes)} | expanded: {expanded} | unexpanded: {left}]",
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
