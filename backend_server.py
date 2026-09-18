from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, sqlite3, webbrowser, threading, time, os, csv

ROOT=Path(__file__).resolve().parent
DB=ROOT/"data"/"responses.sqlite3"
SEED=ROOT/"data"/"synthetic_demo_responses_n45.json"

def init_db():
    con=sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS live_responses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id TEXT, condition_code TEXT, payload_json TEXT, submitted_at TEXT
    )""")
    con.commit(); con.close()

def counts():
    seeded=len(json.loads(SEED.read_text(encoding="utf-8")))
    con=sqlite3.connect(DB); live=con.execute("SELECT COUNT(*) FROM live_responses").fetchone()[0]; con.close()
    return seeded,live

class H(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        path=path.split("?",1)[0].split("#",1)[0]
        rel=path.lstrip("/") or "index.html"
        return str(ROOT/rel)
    def send_json(self,obj,status=200):
        b=json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith("/api/status"):
            s,l=counts(); return self.send_json({"status":"ok","mode":"local-research-backend","seeded_n":s,"live_n":l})
        if self.path.startswith("/api/responses"):
            seed=json.loads(SEED.read_text(encoding="utf-8"))
            con=sqlite3.connect(DB); live=[json.loads(r[0]) for r in con.execute("SELECT payload_json FROM live_responses ORDER BY id").fetchall()]; con.close()
            return self.send_json({"seeded":seed,"live":live})
        return super().do_GET()
    def do_POST(self):
        if self.path.startswith("/api/submit"):
            try:
                n=int(self.headers.get("Content-Length","0")); d=json.loads(self.rfile.read(n))
                pid=str(d.get("participant_id","")); c=str(d.get("condition","")); ts=str(d.get("submitted_at",""))
                con=sqlite3.connect(DB); con.execute("INSERT INTO live_responses(participant_id,condition_code,payload_json,submitted_at) VALUES(?,?,?,?)",(pid,c,json.dumps(d),ts)); con.commit(); con.close()
                return self.send_json({"saved":True},201)
            except Exception as e:
                return self.send_json({"saved":False,"error":str(e)},400)
        return self.send_json({"error":"not found"},404)

if __name__=="__main__":
    init_db()
    port=8000
    url=f"http://127.0.0.1:{port}/index.html"
    threading.Thread(target=lambda:(time.sleep(.8),webbrowser.open(url)),daemon=True).start()
    print(f"Research prototype running at {url}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1",port),H).serve_forever()
