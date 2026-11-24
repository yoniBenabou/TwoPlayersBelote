"""Télécharge les parties enregistrées par le site (table Supabase game_logs) dans un fichier .jsonl,
le même format que web/logs/games.jsonl, pour scripts.coinche_human_results.

    SUPABASE_URL=... SUPABASE_SECRET_KEY=... python -m scripts.supabase_export --out web/logs/site.jsonl
    python -m scripts.coinche_human_results --log web/logs/site.jsonl --model grand
    ... python -m scripts.supabase_export --table game_logs_petit --out web/logs/petit.jsonl   # table du petit réseau

Les clés sont celles du site sur Render (Environment). Chaque enregistrement porte model_name
(« petit » ou « grand ») depuis le 15/11/2026 ; avant, c'était toujours le petit réseau.
"""
import argparse
import json
import os
import sys
import urllib.request

PAGE = 1000


def main():
    parser = argparse.ArgumentParser(description="Parties du site (Supabase) vers un fichier .jsonl.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--table", default="game_logs", help="table Supabase (game_logs_petit pour le petit réseau)")
    args = parser.parse_args()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        sys.exit("Il faut SUPABASE_URL et SUPABASE_SECRET_KEY (les mêmes que sur Render).")
    seen, rows, start = set(), [], 0
    while True:
        request = urllib.request.Request(f"{url}/rest/v1/{args.table}?select=payload",
                                         headers={"apikey": key, "Authorization": f"Bearer {key}",
                                                  "Range-Unit": "items", "Range": f"{start}-{start + PAGE - 1}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            page = json.load(response)
        for row in page:
            text = json.dumps(row["payload"], ensure_ascii=False, sort_keys=True)
            if text not in seen:
                seen.add(text)
                rows.append(row["payload"])
        if len(page) < PAGE:
            break
        start += PAGE
    rows.sort(key=lambda r: r.get("time") or 0)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    names = {}
    for r in rows:
        if r.get("type") == "game" and (r.get("opponents") or "").startswith("ai"):
            name = r.get("model_name") or "petit"
            names[name] = names.get(name, 0) + 1
    print(f"{len(rows)} enregistrements écrits dans {args.out} ; parties contre l'IA : {names or 'aucune'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
