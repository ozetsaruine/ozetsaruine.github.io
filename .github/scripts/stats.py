"""Lit les stats de GoatCounter (API « Read statistics ») et les range par jour dans
stats/AAAA-MM.json : visites, clics par lien, sources. Recalcule les 35 derniers jours à chaque passage."""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import date, datetime, timedelta, timezone

BASE = "https://ozetsaruine.goatcounter.com/api/v0"
TOKEN = os.environ.get("GOATCOUNTER_TOKEN", "")
DEBUT_SITE = date(2026, 11, 1)
os.makedirs("stats", exist_ok=True)
ETAPE = ["début"]

def etat(ok, msg, **kw):
    json.dump({"ok": ok, "message": msg, "le": datetime.now(timezone.utc).isoformat(timespec="seconds"), **kw},
              open("stats/etat.json", "w"), ensure_ascii=False, indent=1)

def api(chemin, **params):
    url = BASE + chemin + ("?" + urllib.parse.urlencode(params) if params else "")
    ETAPE[0] = chemin + " " + json.dumps(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    for essai in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and essai < 3: time.sleep(5); continue
            raise

def source(nom):
    r = (nom or "").lower()
    if not r: return "Accès direct"
    for cle, lib in [("instagram","Instagram"),("tiktok","TikTok"),("youtu","YouTube"),("facebook","Facebook"),
                     ("fb.","Facebook"),("google","Google"),("linktr","Linktree")]:
        if cle in r: return lib
    return nom.replace("https://","").replace("http://","").replace("www.","").split("/")[0][:40]

try:
    if not TOKEN: raise RuntimeError("Secret GOATCOUNTER_TOKEN absent")
    fin = datetime.now(timezone.utc).date()
    deb = max(DEBUT_SITE, fin - timedelta(days=34))
    plage = dict(start=f"{deb}T00:00:00Z", end=f"{fin}T23:59:59Z")
    jours = {}
    d = deb
    while d <= fin:
        jours[str(d)] = {"v": 0, "p": 0, "c": {}, "s": {}}; d += timedelta(days=1)

    tot = api("/stats/total", **plage)
    for s in tot.get("stats") or []:
        j = jours.get(s["day"][:10])
        if j is not None: j["v"] = j["p"] = s.get("daily", 0)

    pages, exclus = [], []
    while True:
        p = dict(plage, daily="true", limit=100)
        if exclus: p["exclude_paths"] = ",".join(map(str, exclus))
        h = api("/stats/hits", **p)
        pages += h.get("hits") or []
        exclus += [x["path_id"] for x in h.get("hits") or []]
        if not h.get("more"): break
    for x in pages:
        if not x.get("event"): continue
        nom = x["path"].lstrip("/")
        for s in x.get("stats") or []:
            j = jours.get(s["day"][:10]); n = s.get("daily", 0)
            if j is not None and n: j["c"][nom] = j["c"].get(nom, 0) + n

    for jour, j in jours.items():
        if not j["v"]: continue
        refs = api("/stats/toprefs", start=f"{jour}T00:00:00Z", end=f"{jour}T23:59:59Z", limit=20)
        for r in refs.get("stats") or []:
            lib = source(r.get("name", "")); j["s"][lib] = j["s"].get(lib, 0) + r.get("count", 0)
        time.sleep(0.3)

    mois = {}
    for jour, j in jours.items(): mois.setdefault(jour[:7], {})[jour] = j
    for m, js in mois.items():
        f = f"stats/{m}.json"
        ancien = json.load(open(f))["jours"] if os.path.exists(f) else {}
        ancien.update(js)
        json.dump({"jours": dict(sorted(ancien.items()))}, open(f, "w"), ensure_ascii=False, indent=1)
    etat(True, "Stats à jour", du=str(deb), au=str(fin), visites=sum(j["v"] for j in jours.values()),
         clics=sum(sum(j["c"].values()) for j in jours.values()))
except urllib.error.HTTPError as e:
    etat(False, f"GoatCounter a répondu {e.code} à {ETAPE[0]} : {e.read()[:300].decode('utf-8','replace')}")
except Exception as e:
    etat(False, f"{ETAPE[0]} : {type(e).__name__} {str(e)[:400]}")
