# pipescript/__init__.py
"""
PipeScript — a mini data-pipeline programming language.

Quick start
───────────
    from pipescript import PipeScriptEngine

    result = PipeScriptEngine().run(
        code=open("my_script.ps").read(),
        data=[25, -3, None, 17, ""]
    )

    if result["success"]:
        print("Cleaned data:", result["output"])
    else:
        for err in result["errors"]:
            print(f"[{err['phase']}] line {err['line']}: {err['message']}")
"""

from .engine      import PipeScriptEngine
from .lexer       import Lexer,       LexerError
from .parser      import Parser,      ParseError
from .semantic    import SemanticAnalyzer
from .interpreter import Interpreter, PipeScriptRuntimeError

__all__ = [
    "PipeScriptEngine",
    "Lexer",      "LexerError",
    "Parser",     "ParseError",
    "SemanticAnalyzer",
    "Interpreter","PipeScriptRuntimeError",
]

__version__ = "1.0.0"
