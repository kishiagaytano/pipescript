# pipescript/symbol_table.py
# Phase 4 — Names, Scope, and Binding: Symbol table with parent-chaining
from typing import Any, Dict, Optional


class SymbolTable:
    """
    A single scope frame.  Frames are chained: each inner scope holds a
    reference to its parent so that lookup walks outward automatically.

    Scope chain:
        global → pipeline → block → nested block …
    """

    def __init__(self, parent: Optional['SymbolTable'] = None, name: str = 'global'):
        self.symbols: Dict[str, Any] = {}
        self.parent  = parent
        self.name    = name   # for debugging

    # ── Declaration ──────────────────────────────────────────────────────────

    def declare(self, name: str, value: Any = None) -> None:
        """Create a new binding in *this* scope (shadows outer scopes)."""
        self.symbols[name] = value

    # ── Assignment ───────────────────────────────────────────────────────────

    def assign(self, name: str, value: Any) -> bool:
        """
        Update an existing binding.  Walks outward to find where the variable
        lives.  Returns True on success, False if the name is not declared
        anywhere in the chain.
        """
        if name in self.symbols:
            self.symbols[name] = value
            return True
        if self.parent is not None:
            return self.parent.assign(name, value)
        return False

    # ── Lookup ───────────────────────────────────────────────────────────────

    def lookup(self, name: str) -> Any:
        """
        Return the value bound to *name*.
        Raises KeyError if the name is not found in any scope.
        """
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise KeyError(f"Variable '{name}' is not defined")

    def is_defined(self, name: str) -> bool:
        """Check existence without raising."""
        if name in self.symbols:
            return True
        if self.parent is not None:
            return self.parent.is_defined(name)
        return False

    # ── Child scope factory ───────────────────────────────────────────────────

    def child_scope(self, name: str = 'block') -> 'SymbolTable':
        """Create a new inner scope that inherits from this one."""
        return SymbolTable(parent=self, name=name)

    def __repr__(self) -> str:
        return f"SymbolTable(name={self.name!r}, vars={list(self.symbols.keys())})"
