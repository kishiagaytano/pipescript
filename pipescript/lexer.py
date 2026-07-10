# pipescript/lexer.py
# Phase 2 — Lexical Analysis: Lexer (tokenizer)
from .tokens import Token, TokenType, KEYWORDS
from typing import List


class LexerError(Exception):
    """Raised when the source contains an unrecognised character or malformed literal."""
    def __init__(self, message: str, line: int, col: int):
        super().__init__(message)
        self.line = line
        self.col  = col


class Lexer:
    """
    Scans PipeScript source code left-to-right and produces a flat list of Tokens.

    Usage:
        tokens = Lexer(source_code).tokenize()
    """

    def __init__(self, source: str):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1
        self._tokens: List[Token] = []

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _error(self, msg: str) -> None:
        raise LexerError(msg, self.line, self.col)

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else '\0'

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match_next(self, expected: str) -> bool:
        """Consume the next character only if it equals *expected*."""
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace_and_comments(self) -> None:
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in ' \t\r\n':
                self._advance()
            elif ch == '/' and self._peek(1) == '/':
                # Single-line comment — consume until end of line
                while self.pos < len(self.source) and self._peek() != '\n':
                    self._advance()
            else:
                break

    # ── Scanning helpers ─────────────────────────────────────────────────────

    def _scan_string(self) -> Token:
        line, col = self.line, self.col
        self._advance()  # opening "
        chars: List[str] = []
        while self.pos < len(self.source) and self._peek() != '"':
            ch = self._advance()
            if ch == '\\':
                esc = self._advance()
                chars.append({'n': '\n', 't': '\t', '\\': '\\', '"': '"'}.get(esc, esc))
            else:
                chars.append(ch)
        if self.pos >= len(self.source):
            self._error("Unterminated string literal")
        self._advance()  # closing "
        return Token(TokenType.STRING_LIT, ''.join(chars), line, col)

    def _scan_number(self) -> Token:
        line, col = self.line, self.col
        digits: List[str] = []
        is_float = False

        while self.pos < len(self.source) and self._peek().isdigit():
            digits.append(self._advance())

        if self.pos < len(self.source) and self._peek() == '.' and self._peek(1).isdigit():
            is_float = True
            digits.append(self._advance())  # '.'
            while self.pos < len(self.source) and self._peek().isdigit():
                digits.append(self._advance())

        text = ''.join(digits)
        if is_float:
            return Token(TokenType.FLOAT_LIT, float(text), line, col)
        return Token(TokenType.INT_LIT, int(text), line, col)

    def _scan_ident_or_keyword(self) -> Token:
        line, col = self.line, self.col
        chars: List[str] = []
        while self.pos < len(self.source) and (self._peek().isalnum() or self._peek() == '_'):
            chars.append(self._advance())
        text = ''.join(chars)

        tok_type = KEYWORDS.get(text, TokenType.IDENT)
        # Give booleans and null their Python values directly
        if tok_type == TokenType.TRUE:
            value: object = True
        elif tok_type == TokenType.FALSE:
            value = False
        elif tok_type == TokenType.NULL:
            value = None
        else:
            value = text

        return Token(tok_type, value, line, col)

    # ── Main entry point ─────────────────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        """
        Scan the entire source and return the complete token list.
        The last token is always TokenType.EOF.
        """
        while True:
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                self._tokens.append(Token(TokenType.EOF, None, self.line, self.col))
                break

            line, col = self.line, self.col
            ch = self._peek()

            # String literal
            if ch == '"':
                self._tokens.append(self._scan_string())

            # Number literal
            elif ch.isdigit():
                self._tokens.append(self._scan_number())

            # Identifier or keyword
            elif ch.isalpha() or ch == '_':
                self._tokens.append(self._scan_ident_or_keyword())

            # Operators and delimiters
            else:
                self._advance()  # consume the character before matching

                if ch == '+':
                    self._tokens.append(Token(TokenType.PLUS, '+', line, col))
                elif ch == '-':
                    self._tokens.append(Token(TokenType.MINUS, '-', line, col))
                elif ch == '*':
                    self._tokens.append(Token(TokenType.STAR, '*', line, col))
                elif ch == '/':
                    self._tokens.append(Token(TokenType.SLASH, '/', line, col))
                elif ch == '=':
                    if self._match_next('='):
                        self._tokens.append(Token(TokenType.EQ, '==', line, col))
                    else:
                        self._tokens.append(Token(TokenType.ASSIGN, '=', line, col))
                elif ch == '!':
                    if self._match_next('='):
                        self._tokens.append(Token(TokenType.NEQ, '!=', line, col))
                    else:
                        self._tokens.append(Token(TokenType.BANG, '!', line, col))
                elif ch == '<':
                    if self._match_next('='):
                        self._tokens.append(Token(TokenType.LTE, '<=', line, col))
                    else:
                        self._tokens.append(Token(TokenType.LT, '<', line, col))
                elif ch == '>':
                    if self._match_next('>'):
                        self._tokens.append(Token(TokenType.PIPE, '>>', line, col))
                    elif self._match_next('='):
                        self._tokens.append(Token(TokenType.GTE, '>=', line, col))
                    else:
                        self._tokens.append(Token(TokenType.GT, '>', line, col))
                elif ch == '&':
                    if self._match_next('&'):
                        self._tokens.append(Token(TokenType.AND, '&&', line, col))
                    else:
                        self._error("Unexpected character '&' — did you mean '&&'?")
                elif ch == '|':
                    if self._match_next('|'):
                        self._tokens.append(Token(TokenType.OR, '||', line, col))
                    else:
                        self._error("Unexpected character '|' — did you mean '||'?")
                elif ch == '{':
                    self._tokens.append(Token(TokenType.LBRACE,   '{', line, col))
                elif ch == '}':
                    self._tokens.append(Token(TokenType.RBRACE,   '}', line, col))
                elif ch == '(':
                    self._tokens.append(Token(TokenType.LPAREN,   '(', line, col))
                elif ch == ')':
                    self._tokens.append(Token(TokenType.RPAREN,   ')', line, col))
                elif ch == '[':
                    self._tokens.append(Token(TokenType.LBRACKET, '[', line, col))
                elif ch == ']':
                    self._tokens.append(Token(TokenType.RBRACKET, ']', line, col))
                elif ch == ';':
                    self._tokens.append(Token(TokenType.SEMI,     ';', line, col))
                elif ch == ',':
                    self._tokens.append(Token(TokenType.COMMA,    ',', line, col))
                elif ch == ':':
                    self._tokens.append(Token(TokenType.COLON,    ':', line, col))
                elif ch == '.':
                    self._tokens.append(Token(TokenType.DOT,      '.', line, col))
                else:
                    self._error(f"Unexpected character '{ch}'")

        return self._tokens
