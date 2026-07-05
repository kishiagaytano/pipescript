# pipescript/engine.py
# THE SINGLE FILE YOUR BACKEND TEAM IMPORTS.
#
# PipeScriptEngine chains all 8 phases and returns a JSON-serialisable dict.
# The backend only needs to do:
#
#   from pipescript import PipeScriptEngine
#   result = PipeScriptEngine().run(code=user_code, data=user_data)
#
from __future__ import annotations
import copy
from .ast_nodes import (
    ArrayLiteral,
    AssignStmt,
    BoolLiteral,
    DictLiteral,
    ExprStmt,
    FloatLiteral,
    Identifier,
    IntLiteral,
    PipelineExpr,
    Program,
    NullLiteral,
    UnaryOp,
    ReturnStmt,
    StringLiteral,
    VarDecl,
)
from .lexer       import Lexer,       LexerError
from .parser      import Parser,      ParseError
from .semantic    import SemanticAnalyzer
from .interpreter import Interpreter, PipeScriptRuntimeError
from typing import Any, Dict, List


_MISSING = object()


class PipeScriptEngine:
    """
    Chains Phases 2–8 and returns a single result dictionary.

    Result schema
    ─────────────
    {
        "success":    bool,
        "output":     any,        # value returned by the pipeline block
        "print_log":  [str],      # everything printed with print()
        "tokens":     [{          # for the frontend syntax highlighter
            "type":  str,
            "value": str,
            "line":  int,
            "col":   int
        }],
        "errors": [{              # empty list on success
            "phase":   str,       # "Lexer" | "Parser" | "Semantic" | "Runtime"
            "message": str,       # plain-English explanation
            "line":    int
        }]
    }
    """

    def run(self, code: str, data: Any = None) -> Dict:
        result: Dict = {
            "success":   False,
            "before":    _annotate_statuses(copy.deepcopy(data)),
            "output":    None,
            "print_log": [],
            "tokens":    [],
            "errors":    [],
        }

        # ── Phase 2: Lexical Analysis ─────────────────────────────────────
        try:
            lexer  = Lexer(code)
            tokens = lexer.tokenize()
        except LexerError as exc:
            result["errors"].append({
                "phase":   "Lexer",
                "message": str(exc),
                "line":    exc.line,
            })
            return result

        # Serialise tokens for the frontend (syntax highlighting)
        result["tokens"] = [
            {
                "type":  tok.type.name,
                "value": str(tok.value) if tok.value is not None else "null",
                "line":  tok.line,
                "col":   tok.col,
            }
            for tok in tokens
        ]

        # ── Phase 3 & 4: Syntax Analysis + Scope ─────────────────────────
        try:
            parser = Parser(tokens)
            ast    = parser.parse_program()
        except ParseError as exc:
            result["errors"].append({
                "phase":   "Parser",
                "message": str(exc),
                "line":    exc.line,
            })
            return result

        # ── Phase 5: Semantic Analysis ────────────────────────────────────
        analyzer       = SemanticAnalyzer()
        semantic_errors = analyzer.analyze(ast)
        if semantic_errors:
            result["errors"] = semantic_errors
            return result   # Don't run code that has type errors

        inferred_data = data if data is not None else _infer_data_from_program(ast)
        if inferred_data is not None:
            result["before"] = _annotate_statuses(copy.deepcopy(inferred_data))

        # ── Phases 6–8: Interpretation ────────────────────────────────────
        try:
            interpreter      = Interpreter()
            output           = interpreter.run(ast, input_data=inferred_data)
            result["success"]   = True
            result["output"]    = _annotate_output(copy.deepcopy(inferred_data), _make_serialisable(output))
            result["print_log"] = interpreter.print_log
        except PipeScriptRuntimeError as exc:
            result["errors"].append({
                "phase":   "Runtime",
                "message": str(exc),
                "line":    exc.line,
            })
        except Exception as exc:
            result["errors"].append({
                "phase":   "Runtime",
                "message": f"Unexpected error: {exc}",
                "line":    0,
            })

        return result


# ── Serialisation helper ──────────────────────────────────────────────────────

def _make_serialisable(value: Any) -> Any:
    """Recursively convert any PipeScript runtime value to a JSON-safe type."""
    from .interpreter import PipeScriptInstance
    if isinstance(value, PipeScriptInstance):
        return {"__class__": value.class_name, **{k: _make_serialisable(v)
                                                    for k, v in value.fields.items()}}
    if isinstance(value, list):
        return [_make_serialisable(v) for v in value]
    if isinstance(value, dict):
        return {k: _make_serialisable(v) for k, v in value.items()}
    # int, float, str, bool, None are already JSON-safe
    return value


def _infer_data_from_program(program: Program) -> Any:
    """Infer an in-script dataset from the first pipeline source or array binding."""
    if program.pipeline is not None:
        for stmt in program.pipeline.body:
            pipeline_expr = _extract_pipeline_expr(stmt)
            if pipeline_expr is None:
                continue
            source_value = _resolve_literal_source(program, pipeline_expr.source)
            if source_value is not None:
                return source_value

    for decl in _iter_var_decls(program):
        if decl.initializer is None:
            continue
        value = _resolve_literal_source(program, decl.initializer)
        if value is not None:
            return value

    return None


def _iter_var_decls(program: Program) -> List[VarDecl]:
    decls: List[VarDecl] = []
    decls.extend(program.globals)
    if program.pipeline is not None:
        for stmt in program.pipeline.body:
            if isinstance(stmt, VarDecl):
                decls.append(stmt)
    return decls


def _extract_pipeline_expr(stmt: Any) -> PipelineExpr | None:
    if isinstance(stmt, VarDecl) and isinstance(stmt.initializer, PipelineExpr):
        return stmt.initializer
    if isinstance(stmt, AssignStmt) and isinstance(stmt.value, PipelineExpr):
        return stmt.value
    if isinstance(stmt, ExprStmt) and isinstance(stmt.expr, PipelineExpr):
        return stmt.expr
    if isinstance(stmt, ReturnStmt) and isinstance(stmt.value, PipelineExpr):
        return stmt.value
    return None


def _resolve_literal_source(program: Program, node: Any, seen: set[str] | None = None) -> Any:
    if seen is None:
        seen = set()

    if isinstance(node, ArrayLiteral):
        return [_resolve_literal_source(program, element, seen) for element in node.elements]

    if isinstance(node, DictLiteral):
        resolved: Dict[str, Any] = {}
        for key_node, value_node in node.entries:
            key_value = _resolve_literal_source(program, key_node, seen)
            value = _resolve_literal_source(program, value_node, seen)
            resolved[str(key_value)] = value
        return resolved

    if isinstance(node, (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral)):
        return node.value

    if isinstance(node, NullLiteral):
        return None

    if isinstance(node, Identifier):
        if node.name in seen:
            return None
        seen.add(node.name)
        decl = _find_var_decl(program, node.name)
        if decl is None or decl.initializer is None:
            return None
        return _resolve_literal_source(program, decl.initializer, seen)

    if isinstance(node, UnaryOp):
        operand_value = _resolve_literal_source(program, node.operand, seen)
        if node.op == '-' and isinstance(operand_value, (int, float)):
            return -operand_value
        if node.op == '!' and isinstance(operand_value, bool):
            return not operand_value
        return None

    return None


def _find_var_decl(program: Program, name: str) -> VarDecl | None:
    if program.pipeline is not None:
        for stmt in program.pipeline.body:
            if isinstance(stmt, VarDecl) and stmt.name == name:
                return stmt
    for decl in program.globals:
        if decl.name == name:
            return decl
    return None


def _annotate_statuses(value: Any) -> Any:
    """Attach a simple row status to list-of-dict data points when possible."""
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return [_annotate_row(item) for item in value]
        return [_annotate_statuses(item) for item in value]
    if isinstance(value, dict):
        return {k: _annotate_statuses(v) for k, v in value.items()}
    return value


def _annotate_output(original: Any, value: Any) -> Any:
    """Annotate final output rows with what the pipeline likely did to them."""
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            original_items = original if isinstance(original, list) else []
            return [
                _annotate_output_row(
                    original_items[index] if index < len(original_items) and isinstance(original_items[index], dict) else _MISSING,
                    item,
                )
                for index, item in enumerate(value)
            ]
        original_items = original if isinstance(original, list) else []
        consumed_indices: set[int] = set()
        annotated_items: List[Dict[str, Any]] = []
        for item in value:
            match_index = _match_original_list_item(original_items, item, consumed_indices)
            original_item = original_items[match_index] if match_index is not None else _MISSING
            if match_index is not None:
                consumed_indices.add(match_index)
            annotated_items.append(_wrap_output_item(original_item, item))
        return annotated_items
    if isinstance(value, dict):
        original_dict = original if isinstance(original, dict) else {}
        return {
            k: _annotate_output(original_dict[k] if k in original_dict else _MISSING, v)
            for k, v in value.items()
        }
    return _wrap_output_item(original, value)


def _source_items_for_output(original: Any) -> List[Any]:
    if not isinstance(original, list):
        return []
    if all(isinstance(item, dict) for item in original):
        return [item for item in original if _infer_row_status(item) != "blank"]
    return [item for item in original if not _is_blank(item)]


def _match_original_list_item(original_items: List[Any], value: Any, consumed_indices: set[int]) -> int | None:
    for index, original_item in enumerate(original_items):
        if index in consumed_indices:
            continue
        if original_item == value:
            return index
        if _is_negative(original_item) and value == abs(original_item):
            return index
    return None


def _wrap_output_item(original_item: Any, value: Any) -> Dict[str, Any]:
    return {
        "value": _annotate_statuses(value),
        "status": _infer_output_status(original_item, value),
    }


def _annotate_output_row(original_row: Dict[str, Any] | object, row: Dict[str, Any]) -> Dict[str, Any]:
    annotated = {
        k: _annotate_output(original_row.get(k) if isinstance(original_row, dict) else _MISSING, v)
        for k, v in row.items()
    }
    annotated["status"] = _infer_output_status(original_row, row)
    return annotated


def _annotate_row(row: Dict[str, Any]) -> Dict[str, Any]:
    annotated = {k: _annotate_statuses(v) for k, v in row.items()}
    annotated["status"] = _infer_row_status(row)
    return annotated


def _infer_output_status(original_row: Dict[str, Any] | object, row: Any) -> Dict[str, Any]:
    if original_row is _MISSING:
        return {"state": "generated", "implemented": ["generated"]}

    if not isinstance(row, dict):
        source_value = _row_source_value(original_row)
        if source_value is None:
            if _is_blank(row):
                return {"state": "ok", "implemented": []}
            return {"state": "generated", "implemented": ["fillNull"]}
        if _is_blank(source_value):
            if _is_blank(row):
                return {"state": "ok", "implemented": []}
            return {"state": "generated", "implemented": ["fillNull"]}
        if _is_negative(source_value) and row == abs(source_value):
            return {"state": "cleaned", "implemented": ["removeNegatives"]}
        if source_value == row:
            return {"state": "ok", "implemented": []}
        return {"state": "transformed", "implemented": ["transformed"]}

    if not isinstance(original_row, dict):
        if _is_blank(original_row):
            if _is_blank(row):
                return {"state": "ok", "implemented": []}
            return {"state": "generated", "implemented": ["fillNull"]}
        if _is_negative(original_row) and row == abs(original_row):
            return {"state": "cleaned", "implemented": ["removeNegatives"]}
        if original_row == row:
            return {"state": "ok", "implemented": []}
        return {"state": "transformed", "implemented": ["transformed"]}

    actions: List[str] = []
    for key in set(original_row.keys()) | set(row.keys()):
        before_value = original_row.get(key)
        after_value = row.get(key)
        if before_value == after_value:
            continue
        if _is_negative(before_value) and after_value == abs(before_value):
            actions.append("removeNegatives")
        elif _is_blank(before_value) and not _is_blank(after_value):
            actions.append("fillNull")
        else:
            actions.append("transformed")

    if not actions:
        return {"state": "ok", "implemented": []}

    deduped_actions: List[str] = []
    for action in actions:
        if action not in deduped_actions:
            deduped_actions.append(action)

    state = "cleaned" if any(action in {"removeNegatives", "fillNull"} for action in deduped_actions) else "transformed"
    return {"state": state, "implemented": deduped_actions}


def _row_source_value(original_row: Any) -> Any:
    if not isinstance(original_row, dict):
        return original_row
    for key in ("age", "value", "result"):
        if key in original_row:
            return original_row.get(key)
    for key, value in original_row.items():
        if key != "status":
            return value
    return None


def _infer_row_status(row: Dict[str, Any]) -> str:
    """Derive a compact row status from the row's values."""
    values = [value for key, value in row.items() if key != "status"]
    if not values:
        return "ok"

    if any(_is_blank(value) for value in values):
        return "blank"

    if any(_is_negative(value) for value in values):
        return "negative"

    if any(not _is_supported_cell(value) for value in values):
        return "invalid_type"

    return "ok"


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or (
        isinstance(value, str) and value.strip().lower() == "null"
    )


def _is_negative(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0


def _is_supported_cell(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, list, dict)) or value is None
