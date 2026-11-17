"""Régénère go/liens.js : la table id -> lien affilié utilisée par les liens courts
https://ozetsaruine.github.io/go/?p=<id>. Prend tous les liens affiliés du site
(PROJETS dans index.html, OUTILS dans outils.html) + go/extra.json (liens hors site)."""
import json, re, os
L = {}
for f, nom in (("index.html", "PROJETS"), ("outils.html", "OUTILS")):
    s = open(f, encoding="utf-8").read()
    data = json.loads(re.search(rf"const {nom}=(\[.*?\]);", s, re.S).group(1))
    groupes = data if nom == "OUTILS" else [g for p in data for g in p.get("groupes", [])]
    for g in groupes:
        for r in g.get("refs", []):
            if r.get("a") and r.get("url"):
                L[r["id"]] = {"u": r["url"], "n": r["nom"]}
if os.path.exists("go/extra.json"):
    L.update(json.load(open("go/extra.json", encoding="utf-8")))
open("go/liens.js", "w", encoding="utf-8").write("window.LIENS=" + json.dumps(L, ensure_ascii=False, indent=0) + ";\n")
print(len(L), "liens")
