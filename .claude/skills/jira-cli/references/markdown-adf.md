# Markdown → ADF: writing descriptions & comments

> **ADF conversion is Jira Cloud only.** On **Jira Cloud** (REST v3), text passed as a description (`-b/--body`, `--template`) or comment is converted to **Atlassian Document Format (ADF)** — Jira's structured JSON document model — before storage. On **Server/Data Center** (REST v2) there is no ADF: the field stores **Jira wiki markup**, and GFM is **not** reliably converted — on Server it is passed through largely untranslated (#935). The sections below describe Cloud/ADF behavior; for Server/DC use the **Jira wiki markup (Server/DC)** section below and write wiki markup directly.

**Which to use:**
- **Cloud →** GitHub-flavored markdown (GFM). More predictable; auto-converts to ADF.
- **Server/Data Center →** **Jira wiki markup** (`h2.`, `*bold*`, `{code}…{code}`, `||header||`). GFM may render literally. If GFM is the only available input, convert it to wiki markup first and pipe the result in.

jira-cli accepts **both** GFM and Jira wiki markup as input regardless of backend — the difference is what survives conversion.

## Use GitHub-flavored markdown (recommended)

| Element | Syntax |
|---|---|
| Headers | `# H1`, `## H2`, `### H3` |
| Bold / italic | `**bold**` / `*italic*` (or `__`/`_`) |
| Strikethrough | `~~text~~` → renders as `-text-` in Jira |
| Inline / block code | `` `inline` `` / ```` ```lang … ``` ```` |
| Lists | `- item` / `1. item` |
| Task lists | `- [ ]` / `- [x]` (checkboxes are **not** interactive in Jira) |
| Link | `[text](url)` |
| Table | standard GFM pipe table |
| Blockquote | `> quote` |
| Rule | `---` |

## Conversion gotchas (what does NOT round-trip)

- **Prefer GFM ```` ``` ```` fences over Jira `{code}` blocks.** `{code}` blocks can leak escape characters through the converter. Fenced code is reliable.
- **Strikethrough** `~~text~~` becomes `-text-`.
- **Mentions** need Jira's account form `[~accountid:xxxx]` — a literal `@user` does not become a mention. Get the accountId from `jira issue view KEY --raw | jq '.fields.assignee'`.
- **Emoji shortcodes** (`:rocket:`) are not converted.
- **Raw HTML** tags are stripped.
- **Some Jira panels** (`{panel}`, `{note}`, `{warning}`) have no GFM equivalent — if you need them, use Jira markup deliberately.
- **Triple underscores** `___word___` can be mis-parsed as emphasis and mangle the text (#941). Avoid `___` in identifiers/link text; escape or reword.
- **Code blocks containing a URL with query parameters** may not survive the conversion intact (#974). Verify on one issue if a fenced block holds parameterized URLs.
- Atlassian notes that not all ADF nodes translate perfectly; complex documents may shift formatting. Test on one throwaway issue before a bulk run.

## Jira wiki markup (Server/DC)

On Server/Data Center, write **Jira wiki markup** directly — it is stored as-is (no ADF). Core syntax:

| Element | Wiki markup |
|---|---|
| Headers | `h1.` `h2.` `h3.` |
| Bold / italic | `*bold*` / `_italic_` |
| Underline / strike | `+underline+` / `-strike-` |
| Monospace / code block | `{{inline}}` / `{code:lang}…{code}` |
| Quote | `bq. line` or `{quote}…{quote}` |
| Bullet / numbered list | `* item` / `# item` |
| Link | `[text|https://url]` or `[https://url]` |
| Table | `||H1||H2||` header row, then `|a|b|` rows |
| Panels | `{panel}`, `{note}`, `{warning}`, `{info}`, `{tip}` |
| Color / rule | `{color:red}text{color}` / `----` |

```bash
# Server/DC issue with wiki markup
jira issue create -tBug -s"Title" \
  -b$'h2. Steps\n\n# do x\n# do y\n\n{code:bash}\nmake test\n{code}' --no-input
```

GFM passed to a Server/DC instance tends to render literally (`## H2` shows the hashes) — convert to wiki markup first, or author in wiki markup from the start.

## Getting multi-line text in safely

Shell quoting is the usual source of mangled descriptions. Three reliable patterns:

```bash
# 1) $'...' for inline newlines (bash)
jira issue create -tTask -s"Title" \
  -b$'## Summary\n\nDetails here\n\n```python\nprint("x")\n```' --no-input

# 2) Template file — best for anything structured
jira issue create -tTask -s"Title" --template ./issue.md --no-input

# 3) Pipe from stdin (template -)
cat issue.md | jira issue create -tTask -s"Title" --template -
echo "One-liner body" | jira issue comment add PROJ-1
```

Heredoc for a comment:

```bash
jira issue comment add PROJ-1 --template - <<'EOF'
## Update
- Fixed the root cause
- Added a regression test

```bash
make test
```
EOF
```

## Precedence: body/positional beats template

If you pass **both** a direct body and a template, the direct one wins and the template is **silently ignored**:

- `issue create`/`edit`: `-b/--body` overrides `--template`.
- `comment add`: the positional `BODY` overrides `--template`.

Pick one source per call.

## Template file example

```markdown
## Description
What and why.

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Technical notes
```ts
const example = "test";
```

## References
- [Docs](https://example.com)
```

```bash
jira issue create -tStory -s"New feature" --template ./template.md --no-input
```
