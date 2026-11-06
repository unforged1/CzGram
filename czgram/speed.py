"""When speed mode's look applies. Small and separate so the bar needn't load anything else."""
import re

_FAST = re.compile(r"opus|fable", re.I)


def is_fast_model(name):
    return bool(name) and bool(_FAST.search(name))


def configured_model(cfg):
    key = {"code": "code_model", "api": "model", "custom": "custom_model"}[cfg.get("claude_backend", "code")]
    return cfg.get(key, "")


def should_run(cfg, reported=None):
    """True if the blue look applies. `reported` is the model Claude said it's using, if known."""
    if not cfg.get("speed_mode") or not cfg.get("use_claude"):
        return False
    chosen = configured_model(cfg)
    # "default" leaves the choice to the account, so only Claude's report can settle it.
    return is_fast_model(reported if chosen == "default" else chosen)
