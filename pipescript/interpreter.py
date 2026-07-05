# pipescript/interpreter.py
# Phases 6, 7 & 8 — Control Flow, Data Types, Object-Oriented Features
# Tree-walking interpreter: evaluates the AST and produces a Python value.
from __future__ import annotations
from .ast_nodes import *
from .symbol_table import SymbolTable
from typing import Any, Dict, List, Optional


# ── Internal control-flow signals ────────────────────────────────────────────

class _ReturnSignal(Exception):
    """Unwinds the call stack when a 'return' statement is executed."""
    def __init__(self, value: Any):
        self.value = value


class PipeScriptRuntimeError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(message)
        self.line = line


# ── OOP runtime representation ────────────────────────────────────────────────

class PipeScriptInstance:
    """A live object created by  new ClassName(...)"""
    def __init__(self, class_name: str,
                 fields:  Dict[str, Any],
                 methods: Dict[str, FuncDecl]):
        self.class_name = class_name
        self.fields     = fields
        self.methods    = methods

    def __repr__(self) -> str:
        return f"<{self.class_name} {self.fields}>"


# ── Built-in data-cleaning functions ─────────────────────────────────────────
# These are the "batteries" that make PipeScript useful for data pipelines.

def _make_builtins(log: List[str]) -> Dict[str, Any]:
    def _print(*args):
        msg = ' '.join(str(a) for a in args)
        log.append(msg)
        return None

    def _map_values(value, transform):
        if isinstance(value, list):
            return [_map_values(item, transform) for item in value]
        if isinstance(value, dict):
            return {key: _map_values(item, transform) for key, item in value.items()}
        return transform(value)

    def _remove_blanks(value):
        if isinstance(value, list):
            return [item for item in value if not (item is None or item == '' or str(item).lower() == 'null')]
        if isinstance(value, dict):
            return {key: _remove_blanks(item) for key, item in value.items()}
        return value

    def _remove_negatives(value):
        if isinstance(value, list):
            return [abs(item) if isinstance(item, (int, float)) and not isinstance(item, bool) and item < 0 else item for item in value]
        if isinstance(value, dict):
            return {key: _remove_negatives(item) for key, item in value.items()}
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
            return abs(value)
        return value

    def _fill_null(value, default=0):
        if isinstance(value, list):
            return [default if item is None or item == '' else item for item in value]
        if isinstance(value, dict):
            return {key: _fill_null(item, default) for key, item in value.items()}
        return default if value is None or value == '' else value

    return {
        # I/O
        'print':          _print,
        # String utilities
        'upper':          lambda s: str(s).upper(),
        'lower':          lambda s: str(s).lower(),
        'capitalize':     lambda s: str(s).capitalize(),
        'trim':           lambda s: str(s).strip(),
        'strip':          lambda s: str(s).strip(),
        'replace':        lambda s, old, new: str(s).replace(old, new),
        'contains':       lambda s, sub: sub in str(s),
        'startsWith':     lambda s, prefix: str(s).startswith(prefix),
        'endsWith':       lambda s, suffix: str(s).endswith(suffix),
        'split':          lambda s, sep=',': str(s).split(sep),
        'join':           lambda sep, arr: sep.join(str(x) for x in arr),
        'toString':       lambda x: str(x),
        # Numeric utilities
        'toInt':          lambda x: int(float(str(x))),
        'toFloat':        lambda x: float(str(x)),
        'abs':            lambda x: abs(x),
        'round':          lambda x, n=0: round(x, n),
        # Type checks
        'isNull':         lambda x: x is None,
        'isNumber':       lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        'isString':       lambda x: isinstance(x, str),
        'isBool':         lambda x: isinstance(x, bool),
        # Array / pipeline cleaning
        'len':            lambda arr: len(arr) if isinstance(arr, (list, dict)) else len(str(arr)),
        'removeBlanks':   lambda arr: _remove_blanks(arr),
        'removeNegatives':lambda arr: _remove_negatives(arr),
        'fillNull':       lambda arr, default=0: _fill_null(arr, default),
        'flatten':        lambda arr: [item for sub in arr
                                       for item in (sub if isinstance(sub, list) else [sub])],
        'unique':         lambda arr: list(dict.fromkeys(arr)),
        'sort':           lambda arr: sorted(arr),
        'reverse':        lambda arr: list(reversed(arr)),
        'max':            lambda arr: max(arr) if arr else None,
        'min':            lambda arr: min(arr) if arr else None,
        'sum':            lambda arr: sum(arr),
        'avg':            lambda arr: (sum(arr) / len(arr)) if arr else 0,
        'get':            lambda arr, i: arr[i],
        'slice':          lambda arr, start, end=None: arr[start:end],
        'append':         lambda arr, item: arr + [item],
        'prepend':        lambda arr, item: [item] + arr,
        'range':          lambda start, stop=None, step=1: (
                              list(range(start)) if stop is None else list(range(start, stop, step))
                          ),
    }


# ── Interpreter ───────────────────────────────────────────────────────────────

class Interpreter:
    """
    Walks the AST produced by the Parser and evaluates it.

    Phases covered:
      Phase 6 — Control Flow  (if / else / for / while / return)
      Phase 7 — Data Types    (Int, Float, String, Bool + cast)
      Phase 8 — OOP           (class definition, new, field/method access)
    """

    MAX_LOOP_ITER = 100_000   # Safety limit to catch infinite loops

    def __init__(self):
        self.global_scope = SymbolTable(name='global')
        self._class_defs:  Dict[str, ClassDecl]  = {}
        self._func_defs:   Dict[str, FuncDecl]   = {}
        self.print_log:    List[str]              = []
        self._builtins     = _make_builtins(self.print_log)

    # ════════════════════════════════════════════════════════════════════════
    # PUBLIC ENTRY POINT
    # ════════════════════════════════════════════════════════════════════════

    def run(self, program: Program, input_data: Any = None) -> Any:
        """
        Execute *program*.  Returns the value of the last expression evaluated
        inside the pipeline block (useful for chaining results back to the API).
        """
        # Optionally inject external data as a pre-declared global
        if input_data is not None:
            self.global_scope.declare('input_data', input_data)

        # Register class and function definitions (no code runs yet)
        for cls  in program.classes:   self._class_defs[cls.name]  = cls
        for func in program.functions: self._func_defs[func.name]  = func

        # Execute global variable declarations
        for gvar in program.globals:
            val = self._eval(gvar.initializer, self.global_scope) if gvar.initializer else None
            self.global_scope.declare(gvar.name, val)

        # Execute the pipeline block
        result = None
        if program.pipeline:
            scope = self.global_scope.child_scope('pipeline')
            result = self._exec_block(program.pipeline.body, scope)

        return result

    # ════════════════════════════════════════════════════════════════════════
    # STATEMENT EXECUTION
    # ════════════════════════════════════════════════════════════════════════

    def _exec_block(self, stmts: List, scope: SymbolTable) -> Any:
        result = None
        for stmt in stmts:
            result = self._exec_stmt(stmt, scope)
        return result

    def _exec_stmt(self, stmt, scope: SymbolTable) -> Any:

        # ── Variable declaration ──────────────────────────────────────────
        if isinstance(stmt, VarDecl):
            val = self._eval(stmt.initializer, scope) if stmt.initializer else None
            scope.declare(stmt.name, val)
            return val

        # ── Assignment ────────────────────────────────────────────────────
        if isinstance(stmt, AssignStmt):
            val = self._eval(stmt.value, scope)
            if not scope.assign(stmt.name, val):
                raise PipeScriptRuntimeError(
                    f"Cannot assign to '{stmt.name}' — variable is not declared.", stmt.line)
            return val

        # ── Phase 6: if / else ────────────────────────────────────────────
        if isinstance(stmt, IfStmt):
            if self._truthy(self._eval(stmt.condition, scope)):
                child = scope.child_scope('if')
                return self._exec_block(stmt.then_block, child)
            elif stmt.else_block:
                child = scope.child_scope('else')
                return self._exec_block(stmt.else_block, child)

        # ── Phase 6: while ────────────────────────────────────────────────
        if isinstance(stmt, WhileStmt):
            result = None
            iterations = 0
            while self._truthy(self._eval(stmt.condition, scope)):
                if iterations >= self.MAX_LOOP_ITER:
                    raise PipeScriptRuntimeError(
                        "Infinite loop detected — exceeded 100,000 iterations.", stmt.line)
                child = scope.child_scope('while')
                result = self._exec_block(stmt.body, child)
                iterations += 1
            return result

        # ── Phase 6: for ─────────────────────────────────────────────────
        if isinstance(stmt, ForStmt):
            for_scope = scope.child_scope('for')
            self._exec_stmt(stmt.init, for_scope)
            result = None
            iterations = 0
            while self._truthy(self._eval(stmt.condition, for_scope)):
                if iterations >= self.MAX_LOOP_ITER:
                    raise PipeScriptRuntimeError(
                        "Infinite loop detected — exceeded 100,000 iterations.", stmt.line)
                body_scope = for_scope.child_scope('for_body')
                result = self._exec_block(stmt.body, body_scope)
                self._exec_stmt(stmt.update, for_scope)
                iterations += 1
            return result

        # ── return ────────────────────────────────────────────────────────
        if isinstance(stmt, ReturnStmt):
            val = self._eval(stmt.value, scope) if stmt.value else None
            raise _ReturnSignal(val)

        # ── Expression statement ──────────────────────────────────────────
        if isinstance(stmt, ExprStmt):
            return self._eval(stmt.expr, scope)

        return None

    # ════════════════════════════════════════════════════════════════════════
    # EXPRESSION EVALUATION
    # ════════════════════════════════════════════════════════════════════════

    def _eval(self, node, scope: SymbolTable) -> Any:
        if node is None:
            return None

        # ── Literals ─────────────────────────────────────────────────────
        if isinstance(node, (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral)):
            return node.value
        if isinstance(node, NullLiteral):
            return None

        # ── Identifier (variable lookup) ──────────────────────────────────
        if isinstance(node, Identifier):
            try:
                return scope.lookup(node.name)
            except KeyError:
                raise PipeScriptRuntimeError(
                    f"Variable '{node.name}' is not defined.", node.line)

        # ── Array literal ─────────────────────────────────────────────────
        if isinstance(node, ArrayLiteral):
            return [self._eval(el, scope) for el in node.elements]

        # ── Dictionary literal ───────────────────────────────────────────
        if isinstance(node, DictLiteral):
            result: Dict[str, Any] = {}
            for key_node, value_node in node.entries:
                key_value = self._eval(key_node, scope)
                result[str(key_value)] = self._eval(value_node, scope)
            return result

        # ── Binary / unary operators ──────────────────────────────────────
        if isinstance(node, BinaryOp):
            return self._eval_binop(node, scope)
        if isinstance(node, UnaryOp):
            return self._eval_unary(node, scope)

        # ── Phase 7: cast ─────────────────────────────────────────────────
        if isinstance(node, CastExpr):
            val = self._eval(node.expr, scope)
            return self._cast(val, node.target_type, node.line)

        # ── Phase 8: new ──────────────────────────────────────────────────
        if isinstance(node, NewExpr):
            return self._create_instance(node, scope)

        # ── Function call ─────────────────────────────────────────────────
        if isinstance(node, FuncCall):
            args = [self._eval(a, scope) for a in node.args]
            return self._call(node.name, args, scope, node.line)

        # ── Phase 8: member access / method call ──────────────────────────
        if isinstance(node, MemberAccess):
            return self._eval_member(node, scope)

        # ── Pipeline expression ───────────────────────────────────────────
        if isinstance(node, PipelineExpr):
            return self._eval_pipeline(node, scope)

        raise PipeScriptRuntimeError(
            f"Unknown AST node type: {type(node).__name__}", getattr(node, 'line', 0))

    # ── Binary operations ─────────────────────────────────────────────────────

    def _eval_binop(self, node: BinaryOp, scope: SymbolTable) -> Any:
        op = node.op

        # Short-circuit logical operators
        if op == '&&':
            left = self._eval(node.left, scope)
            return left if not self._truthy(left) else self._eval(node.right, scope)
        if op == '||':
            left = self._eval(node.left, scope)
            return left if self._truthy(left) else self._eval(node.right, scope)

        left  = self._eval(node.left,  scope)
        right = self._eval(node.right, scope)

        try:
            if op == '+':
                # String concatenation or numeric addition
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            if op == '-': return left - right
            if op == '*': return left * right
            if op == '/':
                if right == 0:
                    raise PipeScriptRuntimeError("Division by zero.", node.line)
                # Return float for float operands, else integer division
                if isinstance(left, float) or isinstance(right, float):
                    return left / right
                return left // right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<':  return left <  right
            if op == '>':  return left >  right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
        except TypeError as exc:
            raise PipeScriptRuntimeError(
                f"Type error in '{op}' operation: {exc}", node.line)

        raise PipeScriptRuntimeError(f"Unknown operator '{op}'.", node.line)

    def _eval_unary(self, node: UnaryOp, scope: SymbolTable) -> Any:
        val = self._eval(node.operand, scope)
        if node.op == '-': return -val
        if node.op == '!': return not self._truthy(val)
        raise PipeScriptRuntimeError(f"Unknown unary operator '{node.op}'.", node.line)

    # ── Phase 6: pipeline >> chaining ────────────────────────────────────────

    def _eval_pipeline(self, node: PipelineExpr, scope: SymbolTable) -> Any:
        """
        Evaluate  source >> step1() >> step2() …
        The result of each step becomes the *first* argument of the next call.
        """
        result = self._eval(node.source, scope)

        for step in node.steps:
            if isinstance(step, FuncCall):
                # Extra arguments after the piped value
                extra_args = [self._eval(a, scope) for a in step.args]
                result = self._call(step.name, [result] + extra_args, scope, step.line)

            elif isinstance(step, MemberAccess):
                # obj.method(args) — piped value is first argument
                if scope.is_defined(step.obj):
                    obj = scope.lookup(step.obj)
                    if isinstance(obj, PipeScriptInstance):
                        method = obj.methods.get(step.member)
                        if method is None:
                            raise PipeScriptRuntimeError(
                                f"Class '{obj.class_name}' has no method '{step.member}'.", step.line)
                        extra_args = [self._eval(a, scope) for a in (step.call_args or [])]
                        result = self._call_method(obj, method, [result] + extra_args, step.line)
                    else:
                        extra_args = [self._eval(a, scope) for a in (step.call_args or [])]
                        result = self._call(step.member, [result] + extra_args, scope, step.line)
                else:
                    extra_args = [self._eval(a, scope) for a in (step.call_args or [])]
                    result = self._call(step.member, [result] + extra_args, scope, step.line)

            elif isinstance(step, Identifier):
                result = self._call(step.name, [result], scope, step.line)

        return result

    # ── Phase 8: OOP ─────────────────────────────────────────────────────────

    def _create_instance(self, node: NewExpr, scope: SymbolTable) -> PipeScriptInstance:
        cls = self._class_defs.get(node.class_name)
        if cls is None:
            raise PipeScriptRuntimeError(
                f"Class '{node.class_name}' is not defined.", node.line)

        # Initialise fields
        fields: Dict[str, Any] = {}
        for field in cls.fields:
            fields[field.name] = self._eval(field.initializer, scope) if field.initializer else None

        methods = {m.name: m for m in cls.methods}
        return PipeScriptInstance(node.class_name, fields, methods)

    def _eval_member(self, node: MemberAccess, scope: SymbolTable) -> Any:
        try:
            obj = scope.lookup(node.obj)
        except KeyError:
            raise PipeScriptRuntimeError(
                f"Variable '{node.obj}' is not defined.", node.line)

        if isinstance(obj, PipeScriptInstance):
            if node.call_args is not None:
                # Method call
                method = obj.methods.get(node.member)
                if method is None:
                    raise PipeScriptRuntimeError(
                        f"Class '{obj.class_name}' has no method '{node.member}'.", node.line)
                args = [self._eval(a, scope) for a in node.call_args]
                return self._call_method(obj, method, args, node.line)
            else:
                # Field access
                if node.member not in obj.fields:
                    raise PipeScriptRuntimeError(
                        f"Class '{obj.class_name}' has no field '{node.member}'.", node.line)
                return obj.fields[node.member]

        # Sugar: list / string built-in methods
        if isinstance(obj, list) and node.call_args is not None:
            args = [self._eval(a, scope) for a in node.call_args]
            list_methods: Dict = {
                'length':   lambda: len(obj),
                'get':      lambda i: obj[i],
                'contains': lambda item: item in obj,
                'append':   lambda item: obj + [item],
                'remove':   lambda item: [x for x in obj if x != item],
            }
            if node.member in list_methods:
                return list_methods[node.member](*args)

        if isinstance(obj, str) and node.call_args is not None:
            args = [self._eval(a, scope) for a in node.call_args]
            str_methods: Dict = {
                'upper':     lambda: obj.upper(),
                'lower':     lambda: obj.lower(),
                'capitalize':lambda: obj.capitalize(),
                'strip':     lambda: obj.strip(),
                'length':    lambda: len(obj),
                'replace':   lambda old, new: obj.replace(old, new),
                'contains':  lambda sub: sub in obj,
                'split':     lambda sep=',': obj.split(sep),
            }
            if node.member in str_methods:
                return str_methods[node.member](*args)

        raise PipeScriptRuntimeError(
            f"Cannot access member '{node.member}' on a {type(obj).__name__} value.", node.line)

    # ── Function calling ──────────────────────────────────────────────────────

    def _call(self, name: str, args: List, scope: SymbolTable, line: int) -> Any:
        # User-defined function takes priority
        if name in self._func_defs:
            return self._call_user_func(self._func_defs[name], args, line)

        # Built-in function
        if name in self._builtins:
            fn = self._builtins[name]
            try:
                return fn(*args)
            except Exception as exc:
                raise PipeScriptRuntimeError(
                    f"Error in built-in '{name}': {exc}", line)

        raise PipeScriptRuntimeError(
            f"'{name}' is not defined. Check the function name for typos.", line)

    def _call_user_func(self, func: FuncDecl, args: List, line: int) -> Any:
        func_scope = self.global_scope.child_scope(f'func:{func.name}')
        for (_, param_name), arg_val in zip(func.params, args):
            func_scope.declare(param_name, arg_val)
        try:
            self._exec_block(func.body, func_scope)
        except _ReturnSignal as sig:
            return sig.value
        return None

    def _call_method(self, instance: PipeScriptInstance,
                     method: FuncDecl, args: List, line: int) -> Any:
        method_scope = self.global_scope.child_scope(f'method:{method.name}')
        # Inject instance fields so the method body can read them
        for fname, fval in instance.fields.items():
            method_scope.declare(fname, fval)
        for (_, param_name), arg_val in zip(method.params, args):
            method_scope.declare(param_name, arg_val)
        try:
            self._exec_block(method.body, method_scope)
        except _ReturnSignal as sig:
            return sig.value
        return None

    # ── Phase 7: type casting ─────────────────────────────────────────────────

    def _cast(self, value: Any, target: str, line: int) -> Any:
        try:
            if target == 'Int':
                return int(float(str(value)))
            if target == 'Float':
                return float(str(value))
            if target == 'String':
                return str(value)
            if target == 'Bool':
                if isinstance(value, str):
                    return value.strip().lower() in ('true', '1', 'yes')
                return bool(value)
        except (ValueError, TypeError) as exc:
            raise PipeScriptRuntimeError(
                f"Cannot cast '{value}' to {target}: {exc}", line)
        raise PipeScriptRuntimeError(f"Unknown cast target type '{target}'.", line)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _truthy(value: Any) -> bool:
        if value is None:             return False
        if isinstance(value, bool):   return value
        if isinstance(value, (int, float)): return value != 0
        if isinstance(value, str):    return len(value) > 0
        if isinstance(value, list):   return len(value) > 0
        return True
