"""Running totals of the tokens CzGram's Claude lookups used, as Claude itself reported them.

Kept per day and per model in ~/.local/state/czgram/usage.json. It holds only numbers,
never any exercise text. Lookups through another provider aren't counted.
"""
import datetime
import fcntl
import json
import os
import tempfile

FIELDS = ("input", "output", "thinking", "cache_read", "cache_write")


def path():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "czgram", "usage.json")


def _load():
    try:
        with open(path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data.get("days"), dict) else {"days": {}}
    except (OSError, ValueError, AttributeError):
        return {"days": {}}


def _save(data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path()), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path())
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def lookup_total(entry):
    """Everything the model read or wrote. Thinking is already inside output."""
    return sum(int(entry.get(k, 0)) for k in ("input", "output", "cache_read", "cache_write"))


def record(entry, day=None):
    """Adds one lookup: {"model", "input", "output", "thinking", "cache_read", "cache_write"}."""
    os.makedirs(os.path.dirname(path()), mode=0o700, exist_ok=True)
    day = day or datetime.date.today().isoformat()
    # Two lookups can finish together, so hold a lock across the read and the write.
    with open(path() + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = _load()
        row = data["days"].setdefault(day, {}).setdefault(entry.get("model") or "unknown", {})
        row["requests"] = row.get("requests", 0) + 1
        for field in FIELDS:
            row[field] = row.get(field, 0) + int(entry.get(field, 0))
        _save(data)


def summary(days=None, today=None):
    """Totals over the last `days` days (None for all time): {model: row}, newest data included."""
    today = today or datetime.date.today()
    first = None if days is None else (today - datetime.timedelta(days=days - 1)).isoformat()
    models = {}
    for day, rows in _load()["days"].items():
        if first and day < first:
            continue
        for model, row in rows.items():
            total = models.setdefault(model, {})
            for key, value in row.items():
                total[key] = total.get(key, 0) + value
    return models


def total(days=None, today=None):
    return sum(lookup_total(row) for row in summary(days, today).values())


def reset():
    try:
        os.unlink(path())
    except FileNotFoundError:
        pass


def short(n):
    """12400 -> 12.4k"""
    if n >= 1_000_000:
        return "%.1fM" % (n / 1_000_000)
    if n >= 1000:
        return "%.1fk" % (n / 1000)
    return str(n)


def report():
    """Plain text for `czgram --usage`."""
    lines = []
    for label, days in (("Today", 1), ("Last 7 days", 7), ("All time", None)):
        models = summary(days)
        lines.append("%s: %s tokens, %d lookups" % (label, short(sum(map(lookup_total, models.values()))),
                                                     sum(r.get("requests", 0) for r in models.values())))
    rows = summary()
    if rows:
        lines.append("")
    for model, row in sorted(rows.items(), key=lambda kv: -lookup_total(kv[1])):
        lines.append("%s: %d lookups, %s input, %s output (%s thinking), %s cache read, %s cache write" % (
            model, row.get("requests", 0), short(row.get("input", 0)), short(row.get("output", 0)),
            short(row.get("thinking", 0)), short(row.get("cache_read", 0)), short(row.get("cache_write", 0))))
    return "\n".join(lines)
