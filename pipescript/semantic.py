# pipescript/semantic.py
# Phase 5 - Semantic Analysis: type checking + variable-declaration checking
from __future__ import annotations
from .ast_nodes import *
from typing import Dict, List, Optional, Tuple


class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(message)
        self.line = line


def _result_type(left: str, right: str, op: str) -> Optional[str]:
    """Return result type of (left OP right), or None if illegal."""
    if left == 'Any' or right == 'Any':
        return 'Any'
    if op in {'+', '-', '*', '/'}:
        if left == 'Int' and right == 'Int':                        return 'Int'
        if left in ('Int','Float') and right in ('Int','Float'):    return 'Float'
        if op == '+' and left == 'String' and right == 'String':    return 'String'
        return None
    if op in {'==', '!='}:
        if left == right:                                           return 'Bool'
        if left in ('Int','Float') and right in ('Int','Float'):    return 'Bool'
        return None
    if op in {'<', '>', '<=', '>='}:
        if left in ('Int','Float') and right in ('Int','Float'):    return 'Bool'
        return None
    if op in {'&&', '||'}:
        if left == 'Bool' and right == 'Bool':                      return 'Bool'
        return None
    return None


def _compatible(declared: str, actual: str) -> bool:
    """True when actual can be stored in a variable declared as declared."""
    if declared == actual:              return True
    if 'Any' in (declared, actual):     return True
    if declared == 'Float' and actual == 'Int': return True
    if actual == 'Array':               return True  # Int[] declared as Int but value is Array
    return False


class SemanticAnalyzer:
    """Two-pass analyser: collect definitions, then walk and type-check."""

    def __init__(self):
        self.errors: List[Dict] = []
        self._global_types: Dict[str, str] = {}
        self._func_sigs:    Dict[str, Dict] = {}
        self._class_defs:   Dict[str, Dict] = {}
        self._scopes:       List[Dict[str, str]] = []
        self._current_return_type: Optional[str] = None

    def _err(self, msg: str, line: int = 0) -> None:
        self.errors.append({'phase': 'Semantic', 'message': msg, 'line': line})

    def _enter(self) -> None:
        self._scopes.append({})

    def _exit(self) -> None:
        self._scopes.pop()

    def _declare(self, name: str, type_name: str, line: int) -> None:
        if self._scopes:
            frame = self._scopes[-1]
            if name in frame:
                self._err(f"Variable '{name}' is already declared in this block.", line)
            frame[name] = type_name
        else:
            self._global_types[name] = type_name

    def _lookup_type(self, name: str) -> Optional[str]:
        for frame in reversed(self._scopes):
            if name in frame:
                return frame[name]
        return self._global_types.get(name)

    def analyze(self, program: Program) -> List[Dict]:
        self.errors = []
        # Pre-declare built-in injected by the engine at runtime
        self._global_types['input_data'] = 'Any'
        for cls  in program.classes:    self._collect_class(cls)
        for func in program.functions:  self._collect_func(func)
        for gvar in program.globals:    self._check_var_decl(gvar)
        for cls  in program.classes:    self._check_class(cls)
        for func in program.functions:  self._check_func(func)
        if program.pipeline:
            self._enter()
            for stmt in program.pipeline.body:
                self._check_stmt(stmt)
            self._exit()
        return self.errors

    def _collect_class(self, cls: ClassDecl) -> None:
        self._class_defs[cls.name] = {
            'fields':  {f.name: f.type_name for f in cls.fields},
            'methods': {m.name: {'params': m.params, 'return_type': m.return_type}
                        for m in cls.methods},
        }

    def _collect_func(self, func: FuncDecl) -> None:
        self._func_sigs[func.name] = {
            'params':      func.params,
            'return_type': func.return_type,
        }

    def _check_var_decl(self, decl: VarDecl) -> None:
        if decl.initializer is not None:
            init_t = self._infer(decl.initializer)
            if init_t and init_t != 'Any' and decl.type_name != 'Any':
                if not _compatible(decl.type_name, init_t):
                    self._err(
                        f"Type mismatch on line {decl.line}: cannot assign a '{init_t}' "
                        f"value to '{decl.name}' which is declared as '{decl.type_name}'.",
                        decl.line
                    )
        if decl.scope == 'global':
            self._global_types[decl.name] = decl.type_name
        else:
            self._declare(decl.name, decl.type_name, decl.line)

    def _check_class(self, cls: ClassDecl) -> None:
        self._enter()
        for field in cls.fields:
            self._check_var_decl(field)
        for method in cls.methods:
            self._check_func(method)
        self._exit()

    def _check_func(self, func: FuncDecl) -> None:
        prev = self._current_return_type
        self._current_return_type = func.return_type
        self._enter()
        for (ptype, pname) in func.params:
            self._declare(pname, ptype, func.line)
        for stmt in func.body:
            self._check_stmt(stmt)
        self._exit()
        self._current_return_type = prev

    def _check_stmt(self, stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._check_var_decl(stmt)

        elif isinstance(stmt, AssignStmt):
            declared_t = self._lookup_type(stmt.name)
            if declared_t is None:
                self._err(
                    f"Line {stmt.line}: Variable '{stmt.name}' is used before it was declared.",
                    stmt.line
                )
            else:
                val_t = self._infer(stmt.value)
                if val_t and val_t != 'Any' and declared_t != 'Any':
                    if not _compatible(declared_t, val_t):
                        self._err(
                            f"Line {stmt.line}: Cannot assign a '{val_t}' value to "
                            f"'{stmt.name}' (declared as '{declared_t}').",
                            stmt.line
                        )

        elif isinstance(stmt, IfStmt):
            cond_t = self._infer(stmt.condition)
            if cond_t and cond_t not in ('Bool', 'Any'):
                self._err(
                    f"Line {stmt.line}: The 'if' condition must be Bool, not '{cond_t}'.",
                    stmt.line
                )
            self._enter()
            for s in stmt.then_block: self._check_stmt(s)
            self._exit()
            if stmt.else_block:
                self._enter()
                for s in stmt.else_block: self._check_stmt(s)
                self._exit()

        elif isinstance(stmt, WhileStmt):
            cond_t = self._infer(stmt.condition)
            if cond_t and cond_t not in ('Bool', 'Any'):
                self._err(
                    f"Line {stmt.line}: The 'while' condition must be Bool, not '{cond_t}'.",
                    stmt.line
                )
            self._enter()
            for s in stmt.body: self._check_stmt(s)
            self._exit()

        elif isinstance(stmt, ForStmt):
            self._enter()
            self._check_stmt(stmt.init)
            self._infer(stmt.condition)
            self._check_stmt(stmt.update)
            for s in stmt.body: self._check_stmt(s)
            self._exit()

        elif isinstance(stmt, ReturnStmt):
            if stmt.value and self._current_return_type:
                ret_t = self._infer(stmt.value)
                if ret_t and ret_t != 'Any':
                    if not _compatible(self._current_return_type, ret_t):
                        self._err(
                            f"Line {stmt.line}: Return type mismatch - "
                            f"expected '{self._current_return_type}', got '{ret_t}'.",
                            stmt.line
                        )

        elif isinstance(stmt, ExprStmt):
            self._infer(stmt.expr)

    def _infer(self, node) -> Optional[str]:
        if node is None:                    return None
        if isinstance(node, IntLiteral):    return 'Int'
        if isinstance(node, FloatLiteral):  return 'Float'
        if isinstance(node, StringLiteral): return 'String'
        if isinstance(node, BoolLiteral):   return 'Bool'
        if isinstance(node, NullLiteral):   return 'null'
        if isinstance(node, ArrayLiteral):  return 'Array'

        if isinstance(node, Identifier):
            t = self._lookup_type(node.name)
            if t is None:
                self._err(
                    f"Line {node.line}: Variable '{node.name}' is used before it was declared.",
                    node.line
                )
                return 'Any'
            return t

        if isinstance(node, BinaryOp):
            left_t  = self._infer(node.left)
            right_t = self._infer(node.right)
            if left_t and right_t:
                result = _result_type(left_t, right_t, node.op)
                if result is None:
                    self._err(
                        f"Line {node.line}: Type error - cannot apply '{node.op}' to a "
                        f"'{left_t}' and a '{right_t}'. "
                        f"Hint: use cast() to convert types first.",
                        node.line
                    )
                    return 'Any'
                return result
            return 'Any'

        if isinstance(node, UnaryOp):
            t = self._infer(node.operand)
            if node.op == '!' and t not in ('Bool', 'Any'):
                self._err(f"Line {node.line}: '!' requires a Bool operand, not '{t}'.", node.line)
            if node.op == '-' and t not in ('Int', 'Float', 'Any'):
                self._err(f"Line {node.line}: Unary '-' requires a numeric operand, not '{t}'.", node.line)
            return t

        if isinstance(node, CastExpr):
            return node.target_type

        if isinstance(node, NewExpr):
            if node.class_name not in self._class_defs:
                self._err(f"Line {node.line}: Class '{node.class_name}' is not defined.", node.line)
            return node.class_name

        if isinstance(node, FuncCall):
            sig = self._func_sigs.get(node.name)
            if sig:
                if len(node.args) != len(sig['params']):
                    self._err(
                        f"Line {node.line}: Function '{node.name}' expects "
                        f"{len(sig['params'])} argument(s), got {len(node.args)}.",
                        node.line
                    )
                return sig['return_type']
            for arg in node.args: self._infer(arg)
            return 'Any'

        if isinstance(node, MemberAccess):
            obj_t = self._lookup_type(node.obj)
            if obj_t and obj_t in self._class_defs:
                info = self._class_defs[obj_t]
                if node.call_args is not None:
                    m = info['methods'].get(node.member)
                    if m is None:
                        self._err(
                            f"Line {node.line}: Class '{obj_t}' has no method '{node.member}'.",
                            node.line
                        )
                        return 'Any'
                    return m['return_type']
                else:
                    f = info['fields'].get(node.member)
                    if f is None:
                        self._err(
                            f"Line {node.line}: Class '{obj_t}' has no field '{node.member}'.",
                            node.line
                        )
                    return f or 'Any'
            return 'Any'

        if isinstance(node, PipelineExpr):
            self._infer(node.source)
            return 'Any'

        return 'Any'
