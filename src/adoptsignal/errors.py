"""Domain errors with messages written for non-technical users."""


class DataProblem(ValueError):
    """A data or configuration problem that the user can correct."""


def friendly_message(exc: Exception) -> str:
    """Return a concise, actionable message without exposing internals."""
    if isinstance(exc, DataProblem):
        return str(exc)
    if isinstance(exc, MemoryError):  # includes pyarrow's ArrowMemoryError
        return (
            "There is not enough memory on this computer for this file or step. Close other programs, keep only the "
            "period and adoption columns, or aggregate the file before upload."
        )
    return (
        "The analysis could not finish. Check that the selected columns contain usable values, "
        "then try again. Technical details are available below."
    )

