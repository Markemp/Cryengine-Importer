class ImportReport:
    """Collects per-item outcomes during a mech/asset import so the operator
    can surface a single summary message instead of leaving failures in the
    system console only.
    """

    def __init__(self):
        self.imported = []          # list[str]
        self.skipped = []           # list[(name, reason)]
        self.warnings = []          # list[str]

    def add_imported(self, name):
        self.imported.append(name)

    def add_skipped(self, name, reason):
        self.skipped.append((name, reason))
        print(f"  SKIPPED: {name} — {reason}")

    def add_warning(self, message):
        self.warnings.append(message)
        print(f"  WARNING: {message}")

    @property
    def severity(self):
        if not self.imported and self.skipped:
            return 'ERROR'
        if self.skipped or self.warnings:
            return 'WARNING'
        return 'INFO'

    def summary(self, max_skipped_listed=5):
        parts = [f"Imported {len(self.imported)} item(s)"]
        if self.skipped:
            shown = self.skipped[:max_skipped_listed]
            names = ", ".join(name for name, _ in shown)
            extra = len(self.skipped) - len(shown)
            tail = f" (+{extra} more)" if extra > 0 else ""
            parts.append(f"skipped {len(self.skipped)}: {names}{tail}")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return ". ".join(parts) + "."
