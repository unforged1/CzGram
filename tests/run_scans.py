"""Run `czgram --scan-file` on each image and print findings, wall time and peak RSS."""
import json
import os
import resource
import subprocess
import sys
import time

for path in sys.argv[1:]:
    t0 = time.monotonic()
    proc = subprocess.run([sys.executable, "-m", "czgram", "--scan-file", path],
                          capture_output=True, text=True, timeout=120)
    took = time.monotonic() - t0
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024
    print("== %s  %.2fs  (largest child so far: %d MB)" % (os.path.basename(path), took, peak))
    for line in proc.stdout.splitlines():
        msg = json.loads(line)
        if msg.get("event") == "result":
            if msg["notice"]:
                print("  notice:", msg["notice"])
            for item in msg["items"]:
                print("  %-8s %-34r %-15s %s" % (item["kind"], item["snippet"], item["topic"], item["hint"]))
    if proc.stderr.strip():
        print("  stderr:", proc.stderr.strip()[-300:])
