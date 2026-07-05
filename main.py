# main.py
# FastAPI wrapper around the pipescript/ package.
#
# The heavy lifting is entirely inside PipeScriptEngine().run() — it never
# raises, so /run's body is little more than a pass-through. Routes are kept
# as plain `def` (not `async def`) on purpose: FastAPI runs synchronous route
# handlers in a threadpool automatically, which keeps the event loop free
# while a CPU-bound script (potentially close to the 100,000-iteration loop
# cap) is executing.
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipescript import PipeScriptEngine

from models import (
    ErrorDetail,
    HealthResponse,
    RunRequest,
    RunResponse,
    ValidateResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipescript_api")

app = FastAPI(title="PipeScript API", version="1.0.0")

# Adjust allow_origins to the deployed frontend's origin before shipping
# past a class demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# A couple of canned scripts so the frontend can offer a "try an example"
# dropdown without needing a database. The first one mirrors the README's
# success example, the second its type-mismatch error example.
EXAMPLES = [
    {
        "name": "Clean dictionary records",
        "description": "Code-only dict literal with removeNegatives() -> removeBlanks() -> fillNull(0)",
        "code": (
            "pipeline {\n"
            "    local Dict record = { age: -2, name: \"Ada\", active: true, score: null };\n"
            "    local Dict cleaned = record >> removeNegatives() >> removeBlanks() >> fillNull(0);\n"
            "    print(cleaned);\n"
            "    cleaned;\n"
            "}\n"
        ),
    },
    {
        "name": "Type mismatch (error demo)",
        "description": "Assigns a String to an Int-declared variable to trigger a Semantic error",
        "code": (
            "pipeline {\n"
            "    local Int x = 5;\n"
            "    x = \"hello\";\n"
            "}\n"
        ),
    },
]


@app.post("/run", response_model=RunResponse)
def run_pipeline(req: RunRequest) -> dict:
    """
    Execute PipeScript code and return the result.

    Always returns HTTP 200 — an error inside the user's script is data
    (`success: false` + populated `errors`), not a transport failure. 4xx is
    reserved for malformed requests (e.g. missing/empty `code`), which
    Pydantic already handles as a 422.
    """
    logger.info("POST /run code_len=%d has_data=%s", len(req.code), req.data is not None)

    result = PipeScriptEngine().run(code=req.code, data=req.data)

    if not result.get("success"):
        errors = result.get("errors") or []
        phase = errors[0]["phase"] if errors else "Unknown"
        logger.info("POST /run failed phase=%s", phase)

    return result


@app.post("/validate", response_model=ValidateResponse)
def validate_pipeline(req: RunRequest) -> dict:
    """
    Lint-only endpoint: runs Lexer -> Parser -> Semantic and stops before
    execution, so the frontend can validate as-you-type without triggering
    print() output or waiting on loop-heavy scripts.
    """
    from pipescript.lexer import Lexer, LexerError
    from pipescript.parser import Parser, ParseError
    from pipescript.semantic import SemanticAnalyzer

    try:
        lexer = Lexer(req.code)
        raw_tokens = lexer.tokenize()
    except LexerError as exc:
        return {
            "success": False,
            "tokens": [],
            "errors": [ErrorDetail(phase="Lexer", message=str(exc), line=exc.line)],
        }

    tokens = [
        {
            "type": tok.type.name,
            "value": str(tok.value) if tok.value is not None else "null",
            "line": tok.line,
            "col": tok.col,
        }
        for tok in raw_tokens
    ]

    try:
        parser = Parser(raw_tokens)
        ast = parser.parse_program()
    except ParseError as exc:
        return {
            "success": False,
            "tokens": tokens,
            "errors": [ErrorDetail(phase="Parser", message=str(exc), line=exc.line)],
        }

    semantic_errors = SemanticAnalyzer().analyze(ast)
    if semantic_errors:
        return {"success": False, "tokens": tokens, "errors": semantic_errors}

    return {"success": True, "tokens": tokens, "errors": []}


@app.get("/examples")
def get_examples() -> list:
    """Canned scripts for a frontend 'try an example' dropdown."""
    return EXAMPLES


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}