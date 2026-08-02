# Normalize a Keycloak realm export (partial-export or kc.sh export) for
# cross-version / cross-instance comparison.
#
# Strips instance-specific and volatile fields, and sorts every array of
# named objects, so that UUID regeneration and ordering differences never
# show up as diffs — while every real setting change still does.
#
# Usage (compare an old-version realm against its migrated counterpart):
#   jq -S -f kc-normalize.jq old-export.json  > old.norm.json
#   jq -S -f kc-normalize.jq new-export.json  > new.norm.json
#   diff old.norm.json new.norm.json
#
# Interpret remaining diffs against the per-version expected-changes tables
# in references/legacy-and-migration.md before calling anything a bug.
def volatile: ["id", "containerId", "authenticationFlowBindingOverrides"];
walk(
  if type == "object" then
    with_entries(select(.key as $k | volatile | index($k) | not))
    | if has("attributes") and (.attributes | type == "object") then
        .attributes |= with_entries(select(.key | test("secret.creation.time|client.secret") | not))
      else . end
  elif type == "array" then
    if length > 0 and (.[0] | type == "object") then
      sort_by(.clientId // .name // .alias // .username // (. | tostring))
    else sort end
  else . end
)
