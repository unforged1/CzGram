"""Trigger path: tell a running bar to scan, or start one if none is running."""
import os
import socket
import subprocess
import sys

from . import config


def send(command):
    """True if a running bar accepted the command."""
    if os.name == "nt":
        from . import windows
        try:
            conn = windows.connect(config.ui_socket())
        except (OSError, ValueError, EOFError):
            return False
        try:
            conn.send_bytes(command.encode())
            return True
        except OSError:
            return False
        finally:
            conn.close()
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(1)
    try:
        s.connect(config.ui_socket())
        s.sendall(command.encode() + b"\n")
        return True
    except OSError:
        return False
    finally:
        s.close()


def trigger():
    if send("scan"):
        return
    if os.name == "nt":
        from . import windows
        windows.spawn_detached(["-m", "czgram", "--bar"],
                               os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return
    subprocess.Popen([sys.executable, "-m", "czgram", "--bar"], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
