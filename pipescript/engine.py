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
from .lexer       import Lexer,       LexerError
from .parser      import Parser,      ParseError
from .semantic    import SemanticAnalyzer
from .interpreter import Interpreter, PipeScriptRuntimeError
from typing import Any, Dict, List


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

        # ── Phases 6–8: Interpretation ────────────────────────────────────
        try:
            interpreter      = Interpreter()
            output           = interpreter.run(ast, input_data=data)
            result["success"]   = True
            result["output"]    = _annotate_output(copy.deepcopy(data), _make_serialisable(output))
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
        original_items = _source_items_for_output(original)
        if value and all(isinstance(item, dict) for item in value):
            return [
                _annotate_output_row(
                    original_items[index] if index < len(original_items) and isinstance(original_items[index], dict) else None,
                    item,
                )
                for index, item in enumerate(value)
            ]
        return [
            _wrap_output_item(original_items[index] if index < len(original_items) else None, item)
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        original_dict = original if isinstance(original, dict) else {}
        return {k: _annotate_output(original_dict.get(k), v) for k, v in value.items()}
    return _wrap_output_item(original, value)


def _source_items_for_output(original: Any) -> List[Any]:
    if not isinstance(original, list):
        return []
    if all(isinstance(item, dict) for item in original):
        return [item for item in original if _infer_row_status(item) != "blank"]
    return [item for item in original if not _is_blank(item)]


def _wrap_output_item(original_item: Any, value: Any) -> Dict[str, Any]:
    return {
        "value": _annotate_statuses(value),
        "status": _infer_output_status(original_item, value),
    }


def _annotate_output_row(original_row: Dict[str, Any] | None, row: Dict[str, Any]) -> Dict[str, Any]:
    annotated = {k: _annotate_output(original_row.get(k) if isinstance(original_row, dict) else None, v) for k, v in row.items()}
    annotated["status"] = _infer_output_status(original_row, row)
    return annotated


def _annotate_row(row: Dict[str, Any]) -> Dict[str, Any]:
    annotated = {k: _annotate_statuses(v) for k, v in row.items()}
    annotated["status"] = _infer_row_status(row)
    return annotated


def _infer_output_status(original_row: Dict[str, Any] | None, row: Dict[str, Any]) -> Dict[str, Any]:
    if original_row is None:
        return {"state": "generated", "implemented": ["generated"]}

    if not isinstance(row, dict):
        source_value = _row_source_value(original_row)
        if source_value is None:
            return {"state": "generated", "implemented": ["generated"]}
        if _is_blank(source_value):
            return {"state": "generated", "implemented": ["fillNull"]}
        if _is_negative(source_value) and row == abs(source_value):
            return {"state": "cleaned", "implemented": ["removeNegatives"]}
        if source_value == row:
            return {"state": "ok", "implemented": []}
        return {"state": "transformed", "implemented": ["transformed"]}

    if not isinstance(original_row, dict):
        if _is_blank(original_row):
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
