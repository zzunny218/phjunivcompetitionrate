"""Windows hourly collector. Requires Python 3.11+, GitHub CLI and gh auth login."""
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
GH = shutil.which("gh")

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

def setup():
    # Prove access and collection before changing the active scheduler.
    collect_and_publish(require_all=True)
    command = subprocess.list2cmdline([sys.executable, "-X", "utf8", str(Path(__file__).resolve())])
    if len(command) > 260:
        raise RuntimeError("Move the project to a shorter path, such as C:\\UniversityRates.")
    exists = subprocess.run(["schtasks", "/Query", "/TN", TASK], capture_output=True)
    if exists.returncode == 0:
        raise RuntimeError("PHUniversityRates already exists. Inspect it in Task Scheduler before reinstalling.")
    subprocess.run(["schtasks", "/Create", "/TN", TASK, "/SC", "HOURLY", "/MO", "1",
                    "/ST", "00:05", "/TR", command, "/IT", "/RL", "LIMITED"], check=True)
    try:
        gh("workflow", "disable", "refresh.yml", "--repo", REPO)
    except Exception:
        # Roll back only the exact task created by this setup.
        subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], check=True)
        raise
    print("SETUP COMPLETE: every hour at :05 while logged in. Keep this folder and the PC awake.", flush=True)

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
            return
        with (ROOT / "windows-sync.log").open("a", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                print("\nRUN", datetime.now().isoformat(), flush=True)
                try:
                    if "--setup" in sys.argv:
                        setup()
                    else:
                        collect_and_publish()
                except Exception as exc:
                    print("FAILED:", str(exc), flush=True)
                    return 1
        return 0

if __name__ == "__main__":
    code = main()
    if "--setup" in sys.argv:
        print("See windows-sync.log for the result. SETUP COMPLETE means installation succeeded.")
    sys.exit(code or 0)
