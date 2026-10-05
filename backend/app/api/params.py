"""Shared path-parameter types."""
from __future__ import annotations

from typing import Annotated

from fastapi import Path

# Ids beyond SQLite's 64-bit integer range raise OverflowError deep in the
# driver (a 500); nothing real is anywhere near this, so bound them and let
# validation answer 422 instead.
MAX_ID = 2**31 - 1

# Annotated rather than a shared `= Path(...)` default: FastAPI copies an
# Annotated FieldInfo per parameter, whereas one FieldInfo instance reused
# as the default of several parameters gets bound to the first one's name.
DbId = Annotated[int, Path(ge=1, le=MAX_ID)]
