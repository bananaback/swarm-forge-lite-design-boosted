"""Adapter that renders the wrapper's usage to a text stream."""

USAGE = (
    "usage: ruff4py [ruff check arguments...]\n"
    "\n"
    "Wrapper around `ruff check`. Runs:\n"
    "  ruff check --cache-dir <artifacts>/ruff-cache <args>\n"
    "\n"
    "`check` is supplied automatically; pass only paths and options.\n"
    "Ruff discovers the repository config from each file's own directory."
)


class ConsoleUsage:
    """Prints the usage text to a stream."""

    def __init__(self, stream):
        self._stream = stream

    def show(self) -> None:
        print(USAGE, file=self._stream)
