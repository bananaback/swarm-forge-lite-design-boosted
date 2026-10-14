"""The one failure a umlmodel op can raise."""


class UmlModelError(Exception):
    """The request is refused, or the result fails validation.

    The CLI turns this into one clear message and a non-zero exit. The model
    file stays byte-identical.
    """
