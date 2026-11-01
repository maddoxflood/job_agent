# Job Search Agent

Python agent that checks company job boards daily, filters for co-op/internship postings,
scores each against my profile with Gemini, and sends the best matches to Telegram.
Runs free on GitHub Actions.

## How it works
1. Pulls postings from the public Greenhouse, Lever, and Ashby APIs for a list of target companies.
2. Filters by title, location, and a scam-pattern regex, and skips anything already in `seen.json`.
3. Scores each new posting 0-100 with Gemini, using a Pydantic schema so output is always valid JSON (`fit`, `why`, `dealbreaker`).
4. Sends the top matches to Telegram. Rate limiting, retries, and a per-run cap keep it inside free-tier quotas.

## Setup
Python 3.12. Install `google-genai`, `requests`, and `pydantic`. Set `GEMINI_API_KEY` (and optionally
`TG_TOKEN` / `TG_CHAT`), and put your goals, skills, and dealbreakers in `private/profile.md`.
In GitHub Actions, add those as repo secrets, with the profile text as `PROFILE_MD`.

## Privacy
The profile and keys never live in the repo: they're git-ignored locally and stored as Actions secrets in CI.