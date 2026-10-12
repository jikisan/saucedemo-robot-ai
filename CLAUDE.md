# saucedemo-robot-ai

SDET technical exercise. Robot Framework + Python + Selenium UI automation for https://www.saucedemo.com, plus a custom **AI Test Assistant** library that HELPS testers at runtime (failure triage, self-healing locators, visual checks). The AI does not generate tests.

Evaluation criteria: code quality, modularity, maintainability, creativity (AI + custom tools), structure and design, clear README.

Work proceeds in phases given by the user. Do not start a phase until instructed.

## Tech

- Python 3.11+, robotframework, robotframework-seleniumlibrary (Selenium Manager, NO webdriver_manager), robotframework-pabot, robotframework-datadriver, python-dotenv, pyyaml, pytest
- AI SDKs: `anthropic`, `openai`, both optional (lazy imports inside providers)
- `requirements.txt` uses compatible ranges (`>=x,<y`), not exact pins

## Structure

```
tests/                      login.robot, inventory.robot, cart.robot, checkout.robot
resources/common.resource   suite/test setup & teardown, browser open/close from config
resources/pages/            LoginPage, InventoryPage, CartPage, CheckoutPage (.resource)
locators/locators.yaml      every locator: {primary, description}
libraries/utils/            config.py (reads .env), data_loader.py
libraries/ai_assist/        providers.py, failure_analyzer.py, self_healing.py, visual_validator.py, __init__.py
listeners/AIReportListener.py
data/users.yaml, data/checkout.csv
unit_tests/                 pytest for Python libraries, FakeProvider, no network
.github/workflows/tests.yml
.env.example, requirements.txt, README.md, .gitignore
```

## Rules

- **AI is optional.** `AI_PROVIDER=none` or a missing key → everything runs on heuristic fallbacks. Never fail a test because an AI call failed: catch, log WARN, continue.
- **Provider abstraction:** base class with `complete(prompt)` and `complete_with_image(prompt, image_path)`. Implementations: `AnthropicProvider`, `OpenAIProvider`, `NullProvider`. Model name comes from `AI_MODEL` env, never hardcoded in logic.
- **Config via .env:** `BASE_URL, BROWSER, HEADLESS, TIMEOUT, AI_PROVIDER (anthropic|openai|none), AI_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY, AI_MAX_CALLS`.
- **No sleeps.** Explicit waits only.
- **Tags:** `smoke, regression, negative, edge, known-bug, ai` (+ runtime tag `healed`).
- **Known bugs:** tests for buggy SauceDemo users assert CORRECT behavior and are tagged `known-bug`. Run with `--skiponfailure known-bug` so CI stays green and the report still shows the defects.
- Every Python keyword library has module + keyword docstrings (libdoc compatible). Type hints throughout.
- Small, single-responsibility modules. Consistent names.

## Design decisions (settled)

1. **Repo** at `~/Developer/saucedemo-robot-ai`, git on `main`.
2. **Page Object Model.** Page resources expose actions AND named verification keywords (`Cart Badge Should Show    2`). Tests call page keywords only: no raw SeleniumLibrary calls, no locators in tests.
3. **Self-healing.** Wrapper keywords (e.g. `Click Element Healed    login.submit`) resolve the key from `locators.yaml`. If `primary` fails: heuristic DOM scoring against `description` (text, id, name, data-test, aria-label, tag/type), then AI ranks candidates if the heuristic isn't confident and AI is on. Healed locator logged + written to `results/healing_report.json` (key, old, new, confidence, source). `locators.yaml` is NEVER auto-rewritten; a human accepts the fix.
4. **Visual validator.** With AI: vision model checks the screenshot against a natural-language expectation. Without AI: deterministic DOM/JS heuristics (broken `<img>` via `naturalWidth==0`, duplicate image `src`, misalignment/overlap via bounding rects). No pixel diff, no Pillow.
5. **Failure triage.** `AIReportListener` on failed `end_test` collects error, URL, screenshot, trimmed page source. Categories: `locator | timeout | assertion | app-defect | environment`. Heuristic = regex rules; AI adds root-cause hypothesis + suggested fix. Output: message in log.html for that test + run summary `results/ai_triage.md`.
6. **Data-driven checkout** via `robotframework-datadriver` reading `data/checkout.csv` (one test case per row).
7. **Users covered:** `standard_user` (smoke/regression), `locked_out_user` (negative), `problem_user` / `error_user` / `visual_user` (known-bug), `performance_glitch_user` (edge, login succeeds within raised timeout). `secret_sauce` is public; committing it in `data/users.yaml` is fine.
8. **CI:** Chrome headless only, pabot, AI enabled only if `ANTHROPIC_API_KEY` secret is set (else `none`), separate pytest job, upload `results/` artifacts. Browser stays configurable via `BROWSER`; README notes Firefox.
9. **Dependencies:** compatible version ranges.
10. **AI verdicts are advisory.** Only heuristic checks can fail a test. AI opinions are logged as WARN + included in `ai_triage.md`. CI outcome is identical with or without an API key.
11. **Healed tests pass**, with WARN, a `healing_report.json` entry, and a runtime `healed` tag.
12. **Cost guard:** `AI_MAX_CALLS` (default 20) per run, shared across all AI features. After the cap → heuristics only. Known-bug failures still get AI triage until the cap.
