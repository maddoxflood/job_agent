try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
import os, re, json, time, pathlib, requests
from google import genai
from google.genai import types
from pydantic import BaseModel

MODEL = "gemini-3.5-flash-lite"
MIN_FIT = 70        # raise to 80 if too many results, lower to 60 if too few
MAX_SCORED = 30    # max Gemini calls per run (free-tier safety)


GREENHOUSE = ["cloudflare", "tailscale", "okta", "datadog", "mozilla", "gitlab", "hootsuite"]
LEVER = ["telesat"]
ASHBY = ["solace", "1password", "wealthsimple"]

def load(env_name, path):
    return os.environ.get(env_name) or pathlib.Path(path).read_text()

PROFILE = load("PROFILE_MD", "private/profile.md")

KEYWORDS = re.compile(r"\bco-?op\b|\bintern(ship)?\b|\bstudent\b", re.I)
LOC = re.compile(r"ottawa|kanata|ontario|canada|remote", re.I)
RED_FLAGS = re.compile(r"western union|wire transfer|whatsapp|upfront|gift card|@gmail\.com", re.I)

SEEN = pathlib.Path("seen.json")
try:
    seen = json.loads(SEEN.read_text())
except (FileNotFoundError, json.JSONDecodeError):
    seen = []

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

class Match(BaseModel):
    fit: int            # 0-100
    why: str            # under 20 words
    dealbreaker: bool

def greenhouse(t):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs?content=true", timeout=20).json()
    for j in r.get("jobs", []):
        yield dict(id=f"gh-{j['id']}", company=t, title=j["title"], url=j["absolute_url"],
                   loc=j["location"]["name"], desc=re.sub("<[^>]+>", " ", j.get("content", ""))[:3000])

def lever(t):
    for j in requests.get(f"https://api.lever.co/v0/postings/{t}?mode=json", timeout=20).json():
        yield dict(id=f"lv-{j['id']}", company=t, title=j["text"], url=j["hostedUrl"],
                   loc=j["categories"].get("location") or "", desc=(j.get("descriptionPlain") or "")[:3000])

def ashby(t):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{t}", timeout=20).json()
    for j in r.get("jobs", []):
        yield dict(id=f"ab-{j['id']}", company=t, title=j["title"], url=j["jobUrl"],
                   loc=j.get("location") or "", desc=(j.get("descriptionPlain") or "")[:3000])

def safe(fn, name):
    try:
        return list(fn(name))
    except Exception as e:
        print(f"source failed: {fn.__name__} {name}: {e}")
        return []

def score(job):
    prompt = f"Job: {job['title']} at {job['company']} ({job['loc']})\n\n{job['desc']}"
    for attempt in range(2):
        try:
            r = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=("You screen job postings for the candidate below. Score fit 0-100 against "
                                        "their goals, skills and fit signals. Set dealbreaker=true if any "
                                        "dealbreaker applies.\n\n" + PROFILE),
                    response_mime_type="application/json",
                    response_schema=Match, temperature=0.2))
            return r.parsed
        except Exception as e:
            print(f"score failed: {str(e)[:100]}")
            time.sleep(20)
    return None

jobs = []
for t in GREENHOUSE: jobs += safe(greenhouse, t)
for t in LEVER:      jobs += safe(lever, t)
for t in ASHBY:      jobs += safe(ashby, t)

new = [j for j in jobs if j["id"] not in seen and KEYWORDS.search(j["title"])
       and LOC.search(j["loc"]) and not RED_FLAGS.search(j["desc"])]
print(f"fetched {len(jobs)} postings, {len(new)} new matching co-op/intern + location")

hits = []
for j in new[:MAX_SCORED]:
    s = score(j)
    if s is None:
        continue                       # not marked seen, retry next run
    seen.append(j["id"])
    print(f"  {s.fit}/100 {j['title']} @ {j['company']}")
    if not s.dealbreaker and s.fit >= MIN_FIT:
        hits.append((s.fit, f"{s.fit}/100 {j['title']} @ {j['company']} ({j['loc']})\n{s.why}\n{j['url']}"))
    time.sleep(6)                      # stay under rate limits

hits.sort(reverse=True)
if hits:
    msg = "\n\n".join(h[1] for h in hits[:8])
elif not jobs:
    msg = "Job agent: no postings fetched. Check company lists and logs."
else:
    msg = f"No strong matches today ({len(new)} new postings checked)."
print(msg)

if os.environ.get("TG_TOKEN") and os.environ.get("TG_CHAT"):
    requests.post(f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
                  json=dict(chat_id=os.environ["TG_CHAT"], text=msg[:4000], disable_web_page_preview=True))
SEEN.write_text(json.dumps(seen[-1000:]))