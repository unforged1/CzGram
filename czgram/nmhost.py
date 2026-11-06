#!/usr/bin/python3
"""Native-messaging host: started by the browser, one per browser process.

Connects the CzGram extension to the app. It listens on a private Unix socket;
on each request it asks the extension for a snapshot and relays the reply.
Standalone on purpose, with no imports from the package, since browsers run it directly.
"""
import json
import os
import select
import signal
import socket
import stat
import struct
import sys
import tempfile


def runtime_dir():
    base = os.environ.get("XDG_RUNTIME_DIR")
    path = os.path.join(base, "czgram") if base else os.path.join(
        tempfile.gettempdir(), "czgram-%d" % os.getuid())
    os.makedirs(path, mode=0o700, exist_ok=True)
    st = os.lstat(path)
    if st.st_uid != os.getuid() or not stat.S_ISDIR(st.st_mode):
        raise SystemExit("unsafe runtime directory")
    return path


def read_exact(fd, n):
    data = b""
    while len(data) < n:
        c = os.read(fd, n - len(data))
        if not c:
            return None
        data += c
    return data


def read_message(fd):
    head = read_exact(fd, 4)
    if head is None:
        return None
    body = read_exact(fd, struct.unpack("=I", head)[0])
    return None if body is None else json.loads(body.decode("utf-8"))


def write_message(fd, msg):
    data = json.dumps(msg).encode("utf-8")
    os.write(fd, struct.pack("=I", len(data)) + data)


def main():
    stdin, stdout = sys.stdin.fileno(), sys.stdout.fileno()
    path = os.path.join(runtime_dir(), "bridge-%d.sock" % os.getpid())
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(path)
    os.chmod(path, 0o600)
    srv.listen(4)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    next_id = 0
    try:
        while True:
            ready, _, _ = select.select([stdin, srv], [], [])
            if stdin in ready and read_message(stdin) is None:
                return  # the browser closed the port
            if srv not in ready:
                continue
            conn, _ = srv.accept()
            conn.settimeout(3)
            try:
                if not conn.recv(64).startswith(b"snapshot"):
                    continue
                next_id += 1
                write_message(stdout, {"id": next_id, "cmd": "snapshot"})
                reply = None
                while reply is None:
                    r, _, _ = select.select([stdin], [], [], 3.5)
                    if not r:
                        reply = {"error": "the browser extension did not answer"}
                        break
                    msg = read_message(stdin)
                    if msg is None:
                        return
                    if msg.get("id") == next_id:
                        reply = msg
                conn.settimeout(10)
                conn.sendall(json.dumps(reply).encode("utf-8"))
            except OSError:
                pass
            finally:
                conn.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
