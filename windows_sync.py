"""Windows manual collector. Requires Python 3.11+, GitHub CLI and gh auth login."""
import base64
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

REPO = "zzunny218/phjunivcompetitionrate"
TASK = "PHUniversityRates"
ROOT = Path(__file__).resolve().parent
GH = os.environ.get("PH_GH_EXE") or shutil.which("gh")

def gh(*args, payload=None):
    if not GH:
        raise RuntimeError("Install GitHub CLI, reopen the terminal, then run gh auth login.")
    p = subprocess.run([GH, *args], input=json.dumps(payload) if payload else None,
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        # Avoid printing credential-bearing command output.
        raise RuntimeError("GitHub command failed: " + " ".join(args[:3]) + ". Check gh auth status and repository access.")
    return p.stdout

def get_file(name):
    return json.loads(gh("api", f"repos/{REPO}/contents/{name}"))

def collect_and_publish(require_all=False):
    import collect
    old = get_file("data.json")
    targets = get_file("targets.json")
    with tempfile.TemporaryDirectory(prefix="ph-rates-") as directory:
        path = Path(directory)
        (path / "data.json").write_bytes(base64.b64decode(old["content"]))
        (path / "targets.json").write_bytes(base64.b64decode(targets["content"]))
        collect.ROOT = path
        collect.main()
        raw = (path / "data.json").read_bytes()
        data = json.loads(raw)
        good = sum(row["status"] == "ok" for row in data["rows"])
        print(f"Successful sources: {good}/17", flush=True)
        if require_all and good != 17:
            raise RuntimeError("PC collection did not pass all 17 rows. No schedule was installed. See windows-sync.log.")
        if good == 0:
            raise RuntimeError("All sources failed; nothing published.")
        gh("api", "--method", "PUT", f"repos/{REPO}/contents/data.json", "--input", "-",
           payload={"message": "Update rates from Windows PC", "sha": old["sha"],
                    "content": base64.b64encode(raw).decode(), "branch": "main"})
        print("Data saved to GitHub. Pages publication may take a few minutes.", flush=True)

def stop_old_schedule():
    import xml.etree.ElementTree as ET
    result = subprocess.run(["schtasks", "/Query", "/TN", TASK, "/XML"],
                            capture_output=True)
    if result.returncode:
        # Absence is verified against the full task listing; other errors stop.
        listing = subprocess.run(["schtasks", "/Query", "/FO", "CSV", "/NH"],
                                 capture_output=True)
        if listing.returncode or TASK.encode() in listing.stdout:
            raise RuntimeError("Could not inspect the previous Windows task. Check Task Scheduler.")
        return
    root = ET.fromstring(result.stdout)
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    actions = root.findall(".//t:Exec", ns)
    if len(actions) != 1:
        raise RuntimeError("Unexpected existing task. Inspect PHUniversityRates in Task Scheduler.")
    text = " ".join(element.text or "" for element in actions[0])
    if "windows_sync.py" not in text or "python" not in text.lower():
        raise RuntimeError("Existing task does not match this collector; no task was changed.")
    subprocess.run(["schtasks", "/Change", "/TN", TASK, "/DISABLE"], check=True)
    print("Previous Windows schedule disabled.", flush=True)


def main():
    if os.name != "nt":
        raise RuntimeError("This installer is for Windows only.")
    import msvcrt
    with (ROOT / "windows-sync.lock").open("a+b") as lock:
        lock.seek(0)
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            print("Another collection is already running.")
            return 2
        with (ROOT / "windows-sync.log").open("a", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                print("\nRUN", datetime.now().isoformat(), flush=True)
                try:
                    stop_old_schedule()
                    collect_and_publish()
                except Exception as exc:
                    print("FAILED:", str(exc), flush=True)
                    return 1
        return 0

if __name__ == "__main__":
    code = main()
    print("See windows-sync.log for collection counts and publication status.")
    sys.exit(code or 0)
