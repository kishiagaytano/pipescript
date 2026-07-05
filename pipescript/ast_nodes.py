# pipescript/ast_nodes.py
# Phase 3 — Syntax Analysis: Abstract Syntax Tree node definitions
#
# Every node stores the source line number so error messages can point to
# the exact line that caused a problem.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass
class Node:
    line: int = field(default=0, kw_only=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPRESSION NODES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class IntLiteral(Node):
    """e.g.  25"""
    value: int

@dataclass
class FloatLiteral(Node):
    """e.g.  3.14"""
    value: float

@dataclass
class StringLiteral(Node):
    """e.g.  "Alice" """
    value: str

@dataclass
class BoolLiteral(Node):
    """true / false"""
    value: bool

@dataclass
class NullLiteral(Node):
    """null"""
    pass

@dataclass
class Identifier(Node):
    """A bare variable name, e.g. messy_data"""
    name: str

@dataclass
class ArrayLiteral(Node):
    """[ expr, expr, … ]"""
    elements: List[Any]   # List[Node]

@dataclass
class DictLiteral(Node):
    """{ key: value, … }"""
    entries: List[Tuple[Any, Any]]   # List[(Node, Node)]

@dataclass
class BinaryOp(Node):
    """left OP right  (arithmetic, relational, logical)"""
    op:    str
    left:  Any   # Node
    right: Any   # Node

@dataclass
class UnaryOp(Node):
    """! expr  or  - expr"""
    op:      str
    operand: Any   # Node

@dataclass
class CastExpr(Node):
    """cast(TargetType, expr)"""
    target_type: str
    expr:        Any   # Node

@dataclass
class NewExpr(Node):
    """new ClassName(args)"""
    class_name: str
    args:       List[Any]   # List[Node]

@dataclass
class FuncCall(Node):
    """funcName(args)"""
    name: str
    args: List[Any]   # List[Node]

@dataclass
class MemberAccess(Node):
    """obj.member  or  obj.method(args)"""
    obj:       str             # variable name
    member:    str             # field or method name
    call_args: Optional[List[Any]] = None  # None = field access; list = method call

@dataclass
class PipelineExpr(Node):
    """source >> step1() >> step2() …
    The output of each step becomes the first argument of the next."""
    source: Any        # Node — initial value
    steps:  List[Any]  # List[FuncCall | MemberAccess | Identifier]


# ═══════════════════════════════════════════════════════════════════════════════
# STATEMENT NODES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VarDecl(Node):
    """Variable declaration.
    scope = 'global' | 'local' | 'none'  (none = class field or implicit)
    """
    scope:       str
    type_name:   str
    name:        str
    initializer: Optional[Any]   # Node or None

@dataclass
class AssignStmt(Node):
    """name = expr ;"""
    name:  str
    value: Any   # Node

@dataclass
class MemberAssignStmt(Node):
    """obj.field = expr ;"""
    obj:    str   # object variable name
    member: str   # field name
    value:  Any   # Node

@dataclass
class ExprStmt(Node):
    """A standalone expression (including a PipelineExpr) used as a statement."""
    expr: Any   # Node

@dataclass
class IfStmt(Node):
    """if (cond) { … } else { … }"""
    condition:  Any         # Node
    then_block: List[Any]   # List[Node]
    else_block: Optional[List[Any]]

@dataclass
class ForStmt(Node):
    """for (init; condition; update) { … }"""
    init:      Any        # VarDecl or AssignStmt
    condition: Any        # Node
    update:    Any        # AssignStmt (e.g. i = i + 1)
    body:      List[Any]  # List[Node]

@dataclass
class WhileStmt(Node):
    """while (cond) { … }"""
    condition: Any
    body:      List[Any]

@dataclass
class ReturnStmt(Node):
    """return expr? ;"""
    value: Optional[Any]


# ═══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL DECLARATION NODES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FuncDecl(Node):
    """return ReturnType name(params) { body }"""
    return_type: str
    name:        str
    params:      List[Tuple[str, str]]   # [(type_name, param_name), …]
    body:        List[Any]

@dataclass
class ClassDecl(Node):
    """class ClassName { fields… methods… }"""
    name:    str
    fields:  List[VarDecl]
    methods: List[FuncDecl]

@dataclass
class PipelineDecl(Node):
    """pipeline { stmts… } — the main execution block"""
    body: List[Any]

@dataclass
class Program(Node):
    """Root of the AST."""
    globals:  List[VarDecl]
    classes:  List[ClassDecl]
    functions: List[FuncDecl]
    pipeline: Optional[PipelineDecl]
