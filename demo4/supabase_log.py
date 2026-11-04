
import json
import os
import urllib.request

from demo.game import GameLog


class SupabaseGameLog(GameLog):
    def __init__(self, path):
        super().__init__(path)
        self.url = os.environ["SUPABASE_URL"].rstrip("/")
        self.key = os.environ["SUPABASE_SECRET_KEY"]

    def write(self, record):
        super().write(record)

        request = urllib.request.Request(
            f"{self.url}/rest/v1/game_logs",
            data=json.dumps(
                {"payload": record},
                ensure_ascii=False
            ).encode("utf-8"),
            headers={
                "apikey": self.key,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except Exception as error:
            print(f"Supabase logging error: {error}", flush=True)
