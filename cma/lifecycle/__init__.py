"""Memory lifecycle management.

Tools for keeping a vault healthy as it grows: archive cold notes that no
longer earn their keep, mark old decisions as superseded by newer ones.
This is the answer to "you can't have infinite learned memory" - explicit
curation, not silent dropouts.
"""

from cma.lifecycle.archive import (
    ArchiveResult,
    archive_cold_notes,
    archive_note,
)
from cma.lifecycle.migrate_tier import (
    MigrateTierResult,
    migrate_vault_tiers,
)
from cma.lifecycle.supersede import supersede_decision

__all__ = [
    "ArchiveResult",
    "MigrateTierResult",
    "archive_cold_notes",
    "archive_note",
    "migrate_vault_tiers",
    "supersede_decision",
]
