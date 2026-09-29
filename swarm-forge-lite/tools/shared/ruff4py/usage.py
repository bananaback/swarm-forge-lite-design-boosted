"""Adapter that renders the wrapper's usage to a text stream."""

USAGE = (
    "usage: ruff4py [ruff check arguments...]\n"
    "\n"
    "Wrapper around `ruff check`. Runs:\n"
    "  ruff check --cache-dir <artifacts>/ruff-cache --config <config> <args>\n"
    "\n"
    "`check` is supplied automatically; pass only paths and options.\n"
    "Set RUFF4PY_CONFIG to override the config file (default: pack ruff.toml)."
)


class ConsoleUsage:
    """Prints the usage text to a stream."""

    def __init__(self, stream):
        self._stream = stream

    def show(self) -> None:
        print(USAGE, file=self._stream)
