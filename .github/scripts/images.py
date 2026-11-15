"""Pour chaque produit de images/produits/demandes.json ({id, url}) sans photo :
suit le lien (affilié), lit la page produit, récupère la photo principale, la compresse
(800 px max, JPEG qualité 72) en images/produits/<id>.jpg et note titre, description et prix
dans images/produits/infos/<id>.json. Résultat global dans images/produits/rapport.json."""
import html, io, json, os, re, urllib.request
from datetime import datetime, timezone
from PIL import Image

D = "images/produits"
os.makedirs(f"{D}/infos", exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
def get(url, accept="text/html"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "fr-FR,fr;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.geturl(), r.read()
def meta(page, *noms):
    for n in noms:
        for pat in (rf'<meta[^>]+(?:property|name)=["\']{n}["\'][^>]+content=["\']([^"\']+)',
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{n}["\']'):
            m = re.search(pat, page, re.I)
            if m: return html.unescape(m.group(1)).strip()
    return ""
def jsonld(page):
    out = {}
    for bloc in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try: data = json.loads(bloc)
        except Exception: continue
        for d in (data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []):
            if isinstance(d, dict) and "Product" in str(d.get("@type", "")):
                img = d.get("image"); img = img[0] if isinstance(img, list) and img else img
                if isinstance(img, dict): img = img.get("url")
                offres = d.get("offers") or {}; offres = offres[0] if isinstance(offres, list) and offres else offres
                out = {"nom": d.get("name", ""), "description": d.get("description", ""), "image": img or "",
                       "prix": str(offres.get("price", "")) if isinstance(offres, dict) else "",
                       "marque": (d.get("brand") or {}).get("name", "") if isinstance(d.get("brand"), dict) else str(d.get("brand") or "")}
    return out

demandes = json.load(open(f"{D}/demandes.json")) if os.path.exists(f"{D}/demandes.json") else []
rapport = json.load(open(f"{D}/rapport.json")) if os.path.exists(f"{D}/rapport.json") else {}
for d in demandes:
    pid, lien = d["id"], d["url"]
    if os.path.exists(f"{D}/{pid}.jpg") and not d.get("refaire"): continue
    try:
        try:
            finale, brut = get(lien)
            page = brut.decode("utf-8", "replace")
        except Exception:
            # Site qui bloque les robots (ex. Leroy Merlin) : on se contente de la photo fournie
            if not d.get("image"): raise
            finale, page = d.get("page", lien), ""
        ld = jsonld(page)
        img = d.get("image") or meta(page, "og:image", "og:image:secure_url", "twitter:image") or ld.get("image", "")
        infos = {"page": finale.split("?")[0], "titre": meta(page, "og:title") or ld.get("nom", ""),
                 "description": meta(page, "og:description", "description") or ld.get("description", ""),
                 "prix": ld.get("prix", "") or meta(page, "product:price:amount"), "marque": ld.get("marque", ""), "image": img}
        json.dump(infos, open(f"{D}/infos/{pid}.json", "w"), ensure_ascii=False, indent=1)
        if not img: raise RuntimeError("aucune photo trouvée sur la page")
        if img.startswith("//"): img = "https:" + img
        _, octets = get(img, "image/avif,image/webp,image/*")
        im = Image.open(io.BytesIO(octets)).convert("RGB")
        im.thumbnail((800, 800))
        im.save(f"{D}/{pid}.jpg", "JPEG", quality=72, optimize=True, progressive=True)
        rapport[pid] = {"ok": True, "taille_ko": round(os.path.getsize(f"{D}/{pid}.jpg") / 1024), "page": infos["page"]}
    except Exception as e:
        rapport[pid] = {"ok": False, "erreur": f"{type(e).__name__}: {str(e)[:200]}"}
rapport["_le"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
json.dump(rapport, open(f"{D}/rapport.json", "w"), ensure_ascii=False, indent=1)
