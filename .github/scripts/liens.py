"""Vérifie tous les liens produits du site (PROJETS dans index.html, OUTILS dans outils.html).
Pour chaque lien : suit les redirections (lien raccourci, plateforme d'affiliation) jusqu'au
site marchand et classe le résultat :
  ok          : la page produit répond (200)
  hs          : 404/410, erreur DNS ou connexion, ou redirection vers l'accueil / une recherche
                (produit retiré)
  ok_non_verifie : le lien d'affiliation redirige bien vers la page produit du marchand, mais le
                   marchand bloque les robots (403, 429...) : la page elle-même n'est pas vérifiable
Résultat dans liens/etat.json."""
import json, re, urllib.request, urllib.error
from datetime import datetime, timezone
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

def refs():
    out = []
    for f, nom in (("index.html", "PROJETS"), ("outils.html", "OUTILS")):
        s = open(f, encoding="utf-8").read()
        m = re.search(rf"const {nom}=(\[.*?\]);", s, re.S)
        data = json.loads(m.group(1))
        groupes = data if nom == "OUTILS" else [g for p in data for g in p.get("groupes", [])]
        for g in groupes:
            for r in g.get("refs", []):
                if r.get("url") and r["url"] != "#":
                    out.append({"id": r["id"], "nom": r["nom"], "url": r["url"], "page": f})
    return out

def produit_retire(depart, final):
    p = urlparse(final)
    chemin = p.path.rstrip("/")
    if chemin in ("", "/fr", "/fr-fr"): return True
    if re.search(r"/(recherche|search|s)(/|$)", p.path) or "q=" in p.query and "/p/" not in p.path:
        return True
    return False

def verifie(r):
    req = urllib.request.Request(r["url"], headers={"User-Agent": UA, "Accept": "text/html",
                                                   "Accept-Language": "fr-FR,fr;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=40) as rep:
            final, code = rep.geturl(), rep.status
    except urllib.error.HTTPError as e:
        final, code = e.geturl() or r["url"], e.code
    except Exception as e:
        return {"etat": "hs", "detail": f"erreur : {type(e).__name__} {e}"[:200], "final": r["url"]}
    if code in (404, 410):
        return {"etat": "hs", "code": code, "final": final, "detail": "page introuvable"}
    if code in (401, 403, 429, 503):
        if produit_retire(r["url"], final):
            return {"etat": "hs", "code": code, "final": final, "detail": "redirige vers l'accueil ou une recherche (produit retiré ?)"}
        return {"etat": "ok_non_verifie", "code": code, "final": final,
                "detail": "redirection d'affiliation OK, page produit non vérifiable (le marchand bloque les robots)"}
    if code >= 400:
        return {"etat": "hs", "code": code, "final": final, "detail": f"erreur {code}"}
    if produit_retire(r["url"], final):
        return {"etat": "hs", "code": code, "final": final, "detail": "redirige vers l'accueil ou une recherche (produit retiré ?)"}
    return {"etat": "ok", "code": code, "final": final}

res = []
for r in refs():
    v = verifie(r); v.update(r); res.append(v)
    print(v["etat"], r["id"], v.get("code", ""), v.get("detail", ""))
nb = {e: sum(1 for x in res if x["etat"] == e) for e in ("ok", "ok_non_verifie", "hs")}
json.dump({"le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "total": len(res), **nb,
           "liens": res}, open("liens/etat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
