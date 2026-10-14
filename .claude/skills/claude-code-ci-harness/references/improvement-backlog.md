# Improvement Backlog

Open items only. Read before changing the skill.

## Open

- **Subscription-mode live run not done**: blocked on a `claude setup-token`
  token in the secrets file. Once present: smoke + parallel scenarios with
  `--model sonnet`, then re-check `--bare` (expect OAuth refusal) and
  `--restricted` (`system/init` tools must still list `Read`, `Glob`); adopt
  `--restricted` if it holds.
- **Negative-transfer eval not measured**: needs an evals set run with and
  without the skill; blocked on the same live-run credential.
