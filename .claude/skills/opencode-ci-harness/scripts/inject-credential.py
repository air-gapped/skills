#!/usr/bin/env python3
"""Emit ONE provider credential from the operator's opencode v2 store as an
`opencode auth export` array, for piping into `opencode auth import --standalone`
inside the isolated home. The secret travels only through the pipe.

Usage: inject-credential.py SRC_DB INTEGRATION MIN_VALID_SECONDS | opencode auth import --standalone

- key   credentials are copied as-is.
- oauth credentials are copied with an EMPTY refresh token: v2 refreshes only
  when the access token is within 5 min of expiry, so a token valid for longer
  than the run never refreshes, and the operator's refresh token (which the
  provider may rotate) never leaves the operator store. Refused when the access
  token expires sooner than MIN_VALID_SECONDS from now.
- external credentials are refused (secrets live outside the store).

Reads SRC_DB read-only. Refuses to write to a terminal. Exit 3 = refused.
"""

import json
import sqlite3
import sys
import time

if len(sys.argv) != 4:
    sys.exit(__doc__)
if sys.stdout.isatty():
    sys.exit(
        "inject-credential: stdout is a terminal; pipe it into `opencode auth import --standalone`"
    )
src, integration, min_valid = sys.argv[1], sys.argv[2], int(sys.argv[3])

db = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
row = db.execute(
    "SELECT label, value FROM credential WHERE integration_id = ? "
    "ORDER BY active DESC, time_created DESC, id DESC LIMIT 1",
    (integration,),
).fetchone()
db.close()
if row is None:
    sys.exit(
        f"inject-credential: no credential for integration '{integration}' in {src}"
    )
label, raw = row
value = json.loads(raw if isinstance(raw, str) else raw.decode())

kind = value.get("type")
if kind == "key":
    note = "key"
elif kind == "oauth":
    left = value["expires"] / 1000 - time.time()
    if left < min_valid:
        print(
            f"inject-credential: REFUSED {integration}: oauth access token expires in {int(left)}s "
            f"(< {min_valid}s); a copy would have to refresh. Refresh it in your own opencode first.",
            file=sys.stderr,
        )
        sys.exit(3)
    value = {**value, "refresh": ""}
    note = f"oauth, access valid {left / 3600:.1f}h, refresh token withheld"
else:
    print(
        f"inject-credential: REFUSED {integration}: credential type '{kind}' is not copyable",
        file=sys.stderr,
    )
    sys.exit(3)

json.dump(
    [
        {
            "id": "cred_ci",
            "integrationID": integration,
            "label": label,
            "active": True,
            "value": value,
        }
    ],
    sys.stdout,
)
print(f"inject-credential: {integration} ({note})", file=sys.stderr)
