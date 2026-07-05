# pipescript/parser.py
# Phase 3 & 4 - Syntax Analysis + Names/Scope: Recursive-descent parser
from __future__ import annotations
from .tokens import Token, TokenType
from .ast_nodes import (
    Node, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral,
    Identifier, ArrayLiteral, DictLiteral, BinaryOp, UnaryOp, CastExpr, NewExpr,
    FuncCall, MemberAccess, PipelineExpr,
    VarDecl, AssignStmt, ExprStmt, IfStmt, ForStmt, WhileStmt, ReturnStmt,
    FuncDecl, ClassDecl, PipelineDecl, Program,
)
from typing import List, Optional, Tuple


class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(message)
        self.line = line
        self.col  = col


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos    = 0

    @property
    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        return self.tokens[min(idx, len(self.tokens) - 1)]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._cur.type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._cur.type in types:
            return self._advance()
        return None

    def _expect(self, type_: TokenType, hint: str = '') -> Token:
        if self._cur.type == type_:
            return self._advance()
        msg = hint or f"Expected '{type_.name}' but got '{self._cur.value}' ({self._cur.type.name})"
        raise ParseError(msg, self._cur.line, self._cur.col)

    def _error(self, msg: str) -> None:
        raise ParseError(msg, self._cur.line, self._cur.col)

    _TYPE_MAP = {
        TokenType.T_INT:    'Int',
        TokenType.T_FLOAT:  'Float',
        TokenType.T_STRING: 'String',
        TokenType.T_BOOL:   'Bool',
    }

    def _parse_type(self) -> str:
        """Parse a type name, consuming an optional trailing [] array marker."""
        if self._cur.type in self._TYPE_MAP:
            name = self._TYPE_MAP[self._advance().type]
        elif self._cur.type == TokenType.IDENT:
            name = self._advance().value
        else:
            self._error(f"Expected a type name, got '{self._cur.value}'")
        # consume Int[]  ->  still 'Int' (dynamic typing at runtime)
        if self._check(TokenType.LBRACKET) and self._peek().type == TokenType.RBRACKET:
            self._advance()
            self._advance()
        return name

    # ---- TOP-LEVEL ----

    def parse_program(self) -> Program:
        globals_: List[VarDecl]   = []
        classes:  List[ClassDecl] = []
        funcs:    List[FuncDecl]  = []
        pipeline: Optional[PipelineDecl] = None

        while not self._check(TokenType.EOF):
            if self._check(TokenType.GLOBAL):
                globals_.append(self._parse_global_decl())
            elif self._check(TokenType.CLASS):
                classes.append(self._parse_class_decl())
            elif self._check(TokenType.RETURN):
                funcs.append(self._parse_func_decl())
            elif self._check(TokenType.PIPELINE):
                pipeline = self._parse_pipeline_decl()
            else:
                self._error(
                    f"Unexpected '{self._cur.value}' at top level. "
                    "Expected: global, class, return, or pipeline."
                )

        return Program(line=1, globals=globals_, classes=classes,
                       functions=funcs, pipeline=pipeline)

    def _parse_global_decl(self) -> VarDecl:
        line = self._cur.line
        self._expect(TokenType.GLOBAL)
        type_name = self._parse_type()
        name      = self._expect(TokenType.IDENT, "Expected variable name after type").value
        init      = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after global declaration")
        return VarDecl(scope='global', type_name=type_name, name=name, initializer=init, line=line)

    def _parse_class_decl(self) -> ClassDecl:
        line = self._cur.line
        self._expect(TokenType.CLASS)
        name = self._expect(TokenType.IDENT, "Expected class name").value
        self._expect(TokenType.LBRACE, "Expected '{' to open class body")
        fields:  List[VarDecl]  = []
        methods: List[FuncDecl] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            if self._check(TokenType.RETURN):
                methods.append(self._parse_func_decl())
            else:
                fl = self._cur.line
                ft = self._parse_type()
                fn = self._expect(TokenType.IDENT).value
                fi = None
                if self._match(TokenType.ASSIGN):
                    fi = self._parse_expr()
                self._expect(TokenType.SEMI, "Expected ';' after field declaration")
                fields.append(VarDecl(scope='none', type_name=ft, name=fn,
                                      initializer=fi, line=fl))
        self._expect(TokenType.RBRACE, "Expected '}' to close class body")
        return ClassDecl(name=name, fields=fields, methods=methods, line=line)

    def _parse_func_decl(self) -> FuncDecl:
        line = self._cur.line
        self._expect(TokenType.RETURN)
        return_type = self._parse_type()
        name        = self._expect(TokenType.IDENT, "Expected function name").value
        self._expect(TokenType.LPAREN)
        params = self._parse_param_list()
        self._expect(TokenType.RPAREN)
        body   = self._parse_block()
        return FuncDecl(return_type=return_type, name=name, params=params, body=body, line=line)

    def _parse_param_list(self) -> List[Tuple[str, str]]:
        params: List[Tuple[str, str]] = []
        if not self._check(TokenType.RPAREN):
            t = self._parse_type()
            n = self._expect(TokenType.IDENT).value
            params.append((t, n))
            while self._match(TokenType.COMMA):
                t = self._parse_type()
                n = self._expect(TokenType.IDENT).value
                params.append((t, n))
        return params

    def _parse_pipeline_decl(self) -> PipelineDecl:
        line = self._cur.line
        self._expect(TokenType.PIPELINE)
        body = self._parse_block()
        return PipelineDecl(body=body, line=line)

    def _parse_block(self) -> List:
        self._expect(TokenType.LBRACE, "Expected '{'")
        stmts = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            stmts.append(self._parse_stmt())
        self._expect(TokenType.RBRACE, "Expected '}'")
        return stmts

    # ---- STATEMENTS ----

    def _parse_stmt(self):
        if self._check(TokenType.LOCAL):
            return self._parse_local_decl()
        if self._check(TokenType.IF):
            return self._parse_if_stmt()
        if self._check(TokenType.FOR):
            return self._parse_for_stmt()
        if self._check(TokenType.WHILE):
            return self._parse_while_stmt()
        if self._check(TokenType.RETURN):
            return self._parse_return_stmt()
        # Unscoped type declarations: Int x = 5;  or  TextCleaner tc = new ...;
        if self._check(TokenType.T_INT, TokenType.T_FLOAT,
                       TokenType.T_STRING, TokenType.T_BOOL):
            return self._parse_unscoped_decl()
        if self._check(TokenType.IDENT) and self._peek().type == TokenType.IDENT:
            return self._parse_unscoped_decl()
        # Assignment
        if self._check(TokenType.IDENT) and self._peek().type == TokenType.ASSIGN:
            return self._parse_assign_stmt()
        return self._parse_expr_stmt()

    def _parse_unscoped_decl(self) -> VarDecl:
        line      = self._cur.line
        type_name = self._parse_type()
        name      = self._expect(TokenType.IDENT, "Expected variable name after type").value
        init      = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after variable declaration")
        return VarDecl(scope='local', type_name=type_name, name=name,
                       initializer=init, line=line)

    def _parse_local_decl(self) -> VarDecl:
        line = self._cur.line
        self._expect(TokenType.LOCAL)
        type_name = self._parse_type()
        name      = self._expect(TokenType.IDENT, "Expected variable name").value
        init      = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after variable declaration")
        return VarDecl(scope='local', type_name=type_name, name=name,
                       initializer=init, line=line)

    def _parse_assign_stmt(self) -> AssignStmt:
        line = self._cur.line
        name = self._advance().value
        self._expect(TokenType.ASSIGN)
        value = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after assignment")
        return AssignStmt(name=name, value=value, line=line)

    def _parse_if_stmt(self) -> IfStmt:
        line = self._cur.line
        self._expect(TokenType.IF)
        self._expect(TokenType.LPAREN, "Expected '(' after 'if'")
        condition = self._parse_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after condition")
        then_block = self._parse_block()
        else_block = None
        if self._match(TokenType.ELSE):
            else_block = self._parse_block()
        return IfStmt(condition=condition, then_block=then_block,
                      else_block=else_block, line=line)

    def _parse_for_stmt(self) -> ForStmt:
        line = self._cur.line
        self._expect(TokenType.FOR)
        self._expect(TokenType.LPAREN, "Expected '(' after 'for'")
        if self._check(TokenType.LOCAL):
            init = self._parse_local_decl()
        else:
            init = self._parse_assign_stmt()
        condition = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after for-condition")
        upd_line = self._cur.line
        upd_name = self._expect(TokenType.IDENT, "Expected update variable").value
        self._expect(TokenType.ASSIGN)
        upd_val  = self._parse_expr()
        update   = AssignStmt(name=upd_name, value=upd_val, line=upd_line)
        self._expect(TokenType.RPAREN, "Expected ')' to close for header")
        body = self._parse_block()
        return ForStmt(init=init, condition=condition, update=update, body=body, line=line)

    def _parse_while_stmt(self) -> WhileStmt:
        line = self._cur.line
        self._expect(TokenType.WHILE)
        self._expect(TokenType.LPAREN, "Expected '(' after 'while'")
        condition = self._parse_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after condition")
        body = self._parse_block()
        return WhileStmt(condition=condition, body=body, line=line)

    def _parse_return_stmt(self) -> ReturnStmt:
        line = self._cur.line
        self._expect(TokenType.RETURN)
        value = None
        if not self._check(TokenType.SEMI):
            value = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after return")
        return ReturnStmt(value=value, line=line)

    def _parse_expr_stmt(self) -> ExprStmt:
        """Expression statement — >> chaining now handled inside _parse_expr."""
        line = self._cur.line
        expr = self._parse_expr()
        self._expect(TokenType.SEMI, "Expected ';' after statement")
        return ExprStmt(expr=expr, line=line)

    # ---- EXPRESSIONS  (precedence, lowest to highest) ----
    # >> pipeline is the lowest-precedence operator so it can appear anywhere
    # an expression is valid, including variable initialisers.

    def _parse_expr(self):
        return self._parse_pipeline()

    def _parse_pipeline(self):
        """source >> step1() >> step2() ...
        Lowest precedence — binds less tightly than any arithmetic/logical op."""
        left = self._parse_or()
        if not self._check(TokenType.PIPE):
            return left
        steps = []
        while self._match(TokenType.PIPE):
            steps.append(self._parse_pipeline_step())
        return PipelineExpr(source=left, steps=steps, line=left.line)

    def _parse_pipeline_step(self):
        line = self._cur.line
        name = self._expect(TokenType.IDENT, "Expected function name after '>>'").value
        if self._match(TokenType.DOT):
            member = self._expect(TokenType.IDENT).value
            call_args: Optional[List] = None
            if self._match(TokenType.LPAREN):
                call_args = self._parse_arg_list()
                self._expect(TokenType.RPAREN)
            return MemberAccess(obj=name, member=member, call_args=call_args, line=line)
        if self._match(TokenType.LPAREN):
            args = self._parse_arg_list()
            self._expect(TokenType.RPAREN)
            return FuncCall(name=name, args=args, line=line)
        return Identifier(name=name, line=line)

    def _parse_or(self):
        left = self._parse_and()
        while self._check(TokenType.OR):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_and(), line=left.line)
        return left

    def _parse_and(self):
        left = self._parse_equality()
        while self._check(TokenType.AND):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_equality(), line=left.line)
        return left

    def _parse_equality(self):
        left = self._parse_relational()
        while self._check(TokenType.EQ, TokenType.NEQ):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_relational(), line=left.line)
        return left

    def _parse_relational(self):
        left = self._parse_addition()
        while self._check(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_addition(), line=left.line)
        return left

    def _parse_addition(self):
        left = self._parse_multiplication()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_multiplication(), line=left.line)
        return left

    def _parse_multiplication(self):
        left = self._parse_unary()
        while self._check(TokenType.STAR, TokenType.SLASH):
            op = self._advance().value
            left = BinaryOp(op=op, left=left, right=self._parse_unary(), line=left.line)
        return left

    def _parse_unary(self):
        if self._check(TokenType.BANG, TokenType.MINUS):
            line = self._cur.line
            op   = self._advance().value
            return UnaryOp(op=op, operand=self._parse_unary(), line=line)
        return self._parse_primary()

    def _parse_primary(self):
        tok = self._cur

        if self._match(TokenType.INT_LIT):
            return IntLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.FLOAT_LIT):
            return FloatLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.STRING_LIT):
            return StringLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.TRUE):
            return BoolLiteral(value=True, line=tok.line)
        if self._match(TokenType.FALSE):
            return BoolLiteral(value=False, line=tok.line)
        if self._match(TokenType.NULL):
            return NullLiteral(line=tok.line)
        if self._check(TokenType.CAST):
            return self._parse_cast()
        if self._check(TokenType.NEW):
            return self._parse_new()
        if self._check(TokenType.LBRACE):
            return self._parse_dict_literal()
        if self._check(TokenType.LBRACKET):
            return self._parse_array_literal()
        if self._check(TokenType.LPAREN):
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN, "Expected ')' after grouped expression")
            return expr
        if self._check(TokenType.IDENT):
            return self._parse_ident_expr()

        self._error(f"Unexpected token '{tok.value}' in expression")

    def _parse_cast(self) -> CastExpr:
        line = self._cur.line
        self._expect(TokenType.CAST)
        self._expect(TokenType.LPAREN)
        target_type = self._parse_type()
        self._expect(TokenType.COMMA)
        expr = self._parse_expr()
        self._expect(TokenType.RPAREN)
        return CastExpr(target_type=target_type, expr=expr, line=line)

    def _parse_new(self) -> NewExpr:
        line = self._cur.line
        self._expect(TokenType.NEW)
        class_name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.LPAREN)
        args = self._parse_arg_list()
        self._expect(TokenType.RPAREN)
        return NewExpr(class_name=class_name, args=args, line=line)

    def _parse_array_literal(self) -> ArrayLiteral:
        line = self._cur.line
        self._expect(TokenType.LBRACKET)
        elements = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._parse_expr())
            while self._match(TokenType.COMMA):
                elements.append(self._parse_expr())
        self._expect(TokenType.RBRACKET)
        return ArrayLiteral(elements=elements, line=line)

    def _parse_dict_literal(self) -> DictLiteral:
        line = self._cur.line
        self._expect(TokenType.LBRACE)
        entries = []
        if not self._check(TokenType.RBRACE):
            entries.append(self._parse_dict_entry())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RBRACE):
                    break
                entries.append(self._parse_dict_entry())
        self._expect(TokenType.RBRACE)
        return DictLiteral(entries=entries, line=line)

    def _parse_dict_entry(self):
        key = self._parse_dict_key()
        self._expect(TokenType.COLON, "Expected ':' in dictionary entry")
        value = self._parse_expr()
        return (key, value)

    def _parse_dict_key(self):
        tok = self._cur
        if self._match(TokenType.STRING_LIT):
            return StringLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.INT_LIT):
            return IntLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.FLOAT_LIT):
            return FloatLiteral(value=tok.value, line=tok.line)
        if self._match(TokenType.TRUE):
            return BoolLiteral(value=True, line=tok.line)
        if self._match(TokenType.FALSE):
            return BoolLiteral(value=False, line=tok.line)
        if self._match(TokenType.NULL):
            return NullLiteral(line=tok.line)
        if self._match(TokenType.IDENT):
            return StringLiteral(value=tok.value, line=tok.line)
        self._error(f"Expected a dictionary key, got '{tok.value}'")

    def _parse_ident_expr(self):
        line = self._cur.line
        name = self._advance().value
        if self._match(TokenType.LPAREN):
            args = self._parse_arg_list()
            self._expect(TokenType.RPAREN)
            return FuncCall(name=name, args=args, line=line)
        if self._match(TokenType.DOT):
            member = self._expect(TokenType.IDENT).value
            call_args: Optional[List] = None
            if self._match(TokenType.LPAREN):
                call_args = self._parse_arg_list()
                self._expect(TokenType.RPAREN)
            return MemberAccess(obj=name, member=member, call_args=call_args, line=line)
        return Identifier(name=name, line=line)

    def _parse_arg_list(self) -> List:
        args = []
        if not self._check(TokenType.RPAREN):
            args.append(self._parse_expr())
            while self._match(TokenType.COMMA):
                args.append(self._parse_expr())
        return args
