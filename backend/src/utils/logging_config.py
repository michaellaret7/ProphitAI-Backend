import os
import logging
import builtins
from dotenv import load_dotenv

load_dotenv()

__all__ = ["init_logger", "patch_print_for_logging"]

DEFAULT_LEVEL = os.getenv("LOG_LEVEL").upper()

# ----------------------------------------------------------------------------
# Helper – configure root logging once
# ----------------------------------------------------------------------------

_logging_already_configured = False

def _configure_root_logger(level: str = DEFAULT_LEVEL):
    global _logging_already_configured
    if _logging_already_configured:
        return

    numeric_level = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _logging_already_configured = True


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------

def init_logger(name: str | None = None) -> logging.Logger:
    """Return a module-specific logger with root configuration applied."""
    _configure_root_logger()
    return logging.getLogger(name if name else __name__)


def patch_print_for_logging():
    """Redirect built-in print() calls to the logging system.

    * Messages containing the words "Error"/"Warning" or emoji markers ⚠️/❌
      are sent at WARNING level so they still appear by default.
    * All other messages are downgraded to DEBUG, keeping the normal INFO log
      stream clean.
    * Idempotent – safe to call multiple times.
    """
    if getattr(builtins, "_print_is_patched", False):
        return  # Already patched

    original_print = builtins.print  # In case we need it for debugging

    def _logged_print(*args, **kwargs):  # noqa: ANN001 – *args signature matches print
        msg = " ".join(str(a) for a in args)
        logger = logging.getLogger("stdout")
        if any(token in msg for token in ("Error", "Warning", "⚠️", "❌")):
            logger.warning(msg)
        else:
            logger.debug(msg)

    builtins.print = _logged_print  # type: ignore[assignment]
    builtins._print_is_patched = True
    # Expose the original for rare debugging sessions
    builtins._original_print = original_print 