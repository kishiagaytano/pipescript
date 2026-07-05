# pipescript/tokens.py
# Phase 2 — Lexical Analysis: Token definitions
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    # ── Literals ─────────────────────────────────────────────
    INT_LIT    = auto()   # e.g.  25
    FLOAT_LIT  = auto()   # e.g.  3.14
    STRING_LIT = auto()   # e.g.  "hello"

    # ── Identifiers ──────────────────────────────────────────
    IDENT = auto()        # myVar, removeBlanks, …

    # ── Reserved keywords ────────────────────────────────────
    PIPELINE = auto()
    CLASS    = auto()
    NEW      = auto()
    IF       = auto()
    ELSE     = auto()
    FOR      = auto()
    WHILE    = auto()
    RETURN   = auto()
    TRUE     = auto()
    FALSE    = auto()
    NULL     = auto()
    GLOBAL   = auto()
    LOCAL    = auto()
    CAST     = auto()

    # ── Type keywords ────────────────────────────────────────
    T_INT    = auto()   # Int
    T_FLOAT  = auto()   # Float
    T_STRING = auto()   # String
    T_BOOL   = auto()   # Bool

    # ── Arithmetic operators ─────────────────────────────────
    PLUS  = auto()   # +
    MINUS = auto()   # -
    STAR  = auto()   # *
    SLASH = auto()   # /

    # ── Relational operators ─────────────────────────────────
    EQ  = auto()   # ==
    NEQ = auto()   # !=
    LT  = auto()   # <
    GT  = auto()   # >
    LTE = auto()   # <=
    GTE = auto()   # >=

    # ── Logical operators ────────────────────────────────────
    AND  = auto()   # &&
    OR   = auto()   # ||
    BANG = auto()   # !

    # ── Pipeline operator ────────────────────────────────────
    PIPE = auto()   # >>

    # ── Assignment ───────────────────────────────────────────
    ASSIGN = auto()   # =

    # ── Delimiters ───────────────────────────────────────────
    LBRACE   = auto()   # {
    RBRACE   = auto()   # }
    LPAREN   = auto()   # (
    RPAREN   = auto()   # )
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    SEMI     = auto()   # ;
    COMMA    = auto()   # ,
    COLON    = auto()   # :
    DOT      = auto()   # .

    # ── Special ──────────────────────────────────────────────
    EOF = auto()


# Map identifier strings → their keyword token type
KEYWORDS: dict[str, TokenType] = {
    'pipeline': TokenType.PIPELINE,
    'class':    TokenType.CLASS,
    'new':      TokenType.NEW,
    'if':       TokenType.IF,
    'else':     TokenType.ELSE,
    'for':      TokenType.FOR,
    'while':    TokenType.WHILE,
    'return':   TokenType.RETURN,
    'true':     TokenType.TRUE,
    'false':    TokenType.FALSE,
    'null':     TokenType.NULL,
    'global':   TokenType.GLOBAL,
    'local':    TokenType.LOCAL,
    'cast':     TokenType.CAST,
    'Int':      TokenType.T_INT,
    'Float':    TokenType.T_FLOAT,
    'String':   TokenType.T_STRING,
    'Bool':     TokenType.T_BOOL,
}


@dataclass
class Token:
    type:  TokenType
    value: Any      # Python value (int, float, str, bool, None, or the raw string)
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"
