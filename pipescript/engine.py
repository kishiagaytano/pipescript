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
            result["output"]    = _make_serialisable(output)
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
