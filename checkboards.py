import requests

NAMES = ["shopify", "entrust", "kinaxis", "solace", "rossvideo", "calian", "paloaltonetworks",
         "cisco", "blackberry", "ciena", "nokia", "thales", "cgi", "telesat", "ericsson",
         "cloudflare", "1password", "clio", "wealthsimple", "tailscale", "okta", "crowdstrike",
         "datadog", "mozilla", "gitlab", "ecobee", "faire", "hootsuite"]

def count(url, key):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return len(d.get(key, [])) if key else len(d)
    except Exception:
        pass
    return None

for n in NAMES:
    for label, url, key in [
        ("GREENHOUSE", f"https://boards-api.greenhouse.io/v1/boards/{n}/jobs", "jobs"),
        ("LEVER", f"https://api.lever.co/v0/postings/{n}?mode=json", None),
        ("ASHBY", f"https://api.ashbyhq.com/posting-api/job-board/{n}", "jobs"),
    ]:
        c = count(url, key)
        if c is not None:
            print(f"{label}: {n} ({c} jobs)")