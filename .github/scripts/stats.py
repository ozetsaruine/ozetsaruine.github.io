"""Récupère l'export GoatCounter et l'agrège par jour dans stats/AAAA-MM.json
(visites, pages vues, clics par lien, sources). Aucune donnée individuelle n'est gardée."""
import csv, gzip, io, json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = "https://ozetsaruine.goatcounter.com/api/v0"
TOKEN = os.environ.get("GOATCOUNTER_TOKEN", "")
os.makedirs("stats", exist_ok=True)

def etat(ok, msg, **kw):
    json.dump({"ok": ok, "message": msg, "le": datetime.now(timezone.utc).isoformat(timespec="seconds"), **kw},
              open("stats/etat.json", "w"), ensure_ascii=False, indent=1)

def appel(methode, chemin):
    req = urllib.request.Request(BASE + chemin, method=methode,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
        data=b"{}" if methode == "POST" else None)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def source(ref):
    r = (ref or "").lower()
    if not r: return "Accès direct"
    for cle, nom in [("instagram","Instagram"),("tiktok","TikTok"),("youtu","YouTube"),("facebook","Facebook"),
                     ("fb.","Facebook"),("google","Google"),("linktr","Linktree")]:
        if cle in r: return nom
    m = re.match(r"(?:https?://)?(?:www\.)?([^/]+)", ref)
    return m.group(1) if m else ref[:40]

try:
    if not TOKEN: raise RuntimeError("Secret GOATCOUNTER_TOKEN absent")
    exp = json.loads(appel("POST", "/export"))
    for _ in range(60):
        st = json.loads(appel("GET", f"/export/{exp['id']}"))
        if st.get("finished_at"): break
        time.sleep(5)
    else:
        raise RuntimeError("L'export GoatCounter n'a pas fini à temps")
    brut = appel("GET", f"/export/{exp['id']}/download")
    try: brut = gzip.decompress(brut)
    except OSError: pass
    lignes = list(csv.reader(io.StringIO(brut.decode("utf-8"))))
    tete = [h.strip().lower().lstrip("0123456789,") for h in lignes[0]]
    ix = lambda n: tete.index(n) if n in tete else -1
    iP, iE, iD, iR, iS, iB = ix("path"), ix("event"), ix("date"), ix("referrer"), ix("session"), ix("bot")
    if iP < 0 or iD < 0: raise RuntimeError("Format d'export inattendu : " + ",".join(lignes[0]))
    jours, sessions = {}, {}
    for r in lignes[1:]:
        if len(r) <= max(iP, iD): continue
        if iB >= 0 and r[iB] not in ("", "0"): continue
        d = r[iD][:10]
        if not re.match(r"\d{4}-\d{2}-\d{2}$", d): continue
        j = jours.setdefault(d, {"v": 0, "p": 0, "c": {}, "s": {}})
        if iE >= 0 and r[iE].lower() in ("true", "1", "t"):
            nom = r[iP].lstrip("/"); j["c"][nom] = j["c"].get(nom, 0) + 1
        else:
            j["p"] += 1
            ses = r[iS] if iS >= 0 else ""
            vus = sessions.setdefault(d, set())
            if not ses or ses not in vus:
                if ses: vus.add(ses)
                j["v"] += 1
                s = source(r[iR] if iR >= 0 else ""); j["s"][s] = j["s"].get(s, 0) + 1
    mois = {}
    for d, j in jours.items(): mois.setdefault(d[:7], {})[d] = j
    for m, js in mois.items():
        json.dump({"jours": dict(sorted(js.items()))}, open(f"stats/{m}.json", "w"), ensure_ascii=False, indent=1)
    etat(True, "Stats à jour", jours=len(jours), dernierJour=max(jours) if jours else None)
except urllib.error.HTTPError as e:
    etat(False, f"GoatCounter a répondu {e.code} : {e.read()[:300].decode('utf-8','replace')}")
except Exception as e:
    etat(False, str(e)[:400])
