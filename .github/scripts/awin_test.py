import os, json, urllib.request
TOK = os.environ.get("AWIN_TOKEN", "").strip()
PID = os.environ.get("AWIN_PUBLISHER_ID", "").strip()
def get(url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK, "User-Agent": "ozetsaruine"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)
print("Clé présente :", bool(TOK), "| ID éditeur présent :", bool(PID), "| ID =", PID)
try:
    acc = get("https://api.awin.com/accounts")
    comptes = [(a.get("accountId"), a.get("accountType"), a.get("accountName")) for a in acc.get("accounts", acc if isinstance(acc, list) else [])]
    print("Comptes rattachés à la clé :", comptes)
    print("L'ID éditeur correspond :", any(str(c[0]) == PID for c in comptes))
except Exception as e:
    print("Erreur /accounts :", e)
try:
    progs = get(f"https://api.awin.com/publishers/{PID}/programmes?relationship=joined&countryCode=FR")
    print("Programmes rejoints (FR) :", len(progs))
    for p in progs: print(" -", p.get("id"), p.get("name"))
except Exception as e:
    print("Erreur /programmes :", e)
try:
    progs = get(f"https://api.awin.com/publishers/{PID}/programmes?relationship=pending")
    print("Candidatures en attente :", [p.get("name") for p in progs])
except Exception as e:
    print("Erreur /programmes pending :", e)
