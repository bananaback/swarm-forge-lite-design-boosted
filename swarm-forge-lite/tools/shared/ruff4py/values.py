"""Frozen value objects: the check request, its options, and the invocation."""

from dataclasses import dataclass
from pathlib import Path

from .errors import InvalidConfiguration, InvalidUsage

VERB = "check"
CACHE_OPTION = "--cache-dir"
CONFIG_OPTION = "--config"
HELP_FLAGS = ("-h", "--help")
CONFIG_NAME = "ruff.toml"
CACHE_DIR_NAME = "ruff-cache"


@dataclass(frozen=True)
class CheckArguments:
    """The pass-through arguments the caller supplied after the program name."""

    tokens: tuple

    def __post_init__(self):
        if not all(isinstance(token, str) for token in self.tokens):
            raise InvalidUsage("arguments must be strings")

    def requests_help(self) -> bool:
        return any(token in HELP_FLAGS for token in self.tokens)

    def mentions_verb(self) -> bool:
        return VERB in self.tokens

    def supplies(self, option: str) -> bool:
        return any(
            token == option or token.startswith(option + "=")
            for token in self.tokens
        )

    def as_list(self) -> list:
        return list(self.tokens)


@dataclass(frozen=True)
class CacheDirectory:
    """Where ruff keeps its cache, pinned so nothing lands in the project tree."""

    path: Path

    def __post_init__(self):
        if not self.path.is_absolute():
            raise InvalidConfiguration("cache directory must be absolute")

    def prepare(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RuffConfig:
    """The ruff.toml every check must use."""

    path: Path

    def __post_init__(self):
        if not self.path.is_file():
            raise InvalidConfiguration("ruff config not found: " + str(self.path))


@dataclass(frozen=True)
class RuffInvocation:
    """The exact argv handed to the ruff process."""

    executable: Path
    arguments: tuple

    def as_list(self) -> list:
        return [str(self.executable), *self.arguments]


@dataclass(frozen=True)
class CheckRequest:
    """The caller's options plus the defaults the wrapper injects."""

    arguments: CheckArguments
    pack_root: Path
    artifacts_root: Path
    config_override: str | None = None

    def prepare(self) -> None:
        """Create the default cache directory unless the caller named one."""
        if not self.arguments.supplies(CACHE_OPTION):
            self.cache_directory().prepare()

    def invocation(self, executable: Path) -> RuffInvocation:
        """The argv for `executable`, adding the wrapper's cache and config."""
        injected = [VERB]
        if not self.arguments.supplies(CACHE_OPTION):
            injected += [CACHE_OPTION, str(self.cache_directory().path)]
        if not self.arguments.supplies(CONFIG_OPTION):
            injected += [CONFIG_OPTION, str(self.config().path)]
        return RuffInvocation(executable, tuple(injected) + self.arguments.tokens)

    def cache_directory(self) -> CacheDirectory:
        return CacheDirectory(self.artifacts_root / CACHE_DIR_NAME)

    def config(self) -> RuffConfig:
        override = self.config_override
        if override:
            return RuffConfig(Path(override).expanduser())
        return RuffConfig(self.pack_root / CONFIG_NAME)
