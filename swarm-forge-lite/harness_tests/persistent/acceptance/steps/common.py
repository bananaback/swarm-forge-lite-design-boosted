"""Step handlers shared by more than one feature area."""

from .support import clean_env, step


def _no_overrides(world, params, match):
    world.state["env"] = clean_env()


HANDLERS = [
    step(r"^no harness environment overrides$", _no_overrides),
]
