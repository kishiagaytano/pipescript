<div align="center">

# PipeScript

**A minimal, statically-typed language for data-cleaning pipelines.**

*Design & Implementation of a Mini Programming Language — Final Project*
FEU Institute of Technology · Computer Science · Programming Languages

`Python 3.10+` · `Pure-stdlib compiler` · `FastAPI backend` · `Zero-build web IDE`

</div>

---

## What is PipeScript?

Most code that touches real-world data isn't analysis — it's **cleanup**. Removing negatives, dropping nulls, filling defaults, sorting. It's the same handful of steps, in the same order, every time. General-purpose tools like pandas can do it, but they wrap a four-word intent in six lines of ceremony.

**PipeScript makes that straight line the syntax.** Its defining feature is the `>>` **pipeline operator**, which feeds the output of one stage directly into the next:

```pipescript
pipeline {
    local Int[] ages    = [25, -3, null, 41, -9, null];
    local Int[] cleaned = ages >> removeNegatives() >> fillNull(0) >> sort();

    print("Cleaned:", cleaned);   // Cleaned: [0, 0, 3, 9, 25, 41]
    print("Average:", avg(cleaned)); // Average: 13.0
}
```

Read it left to right, like a sentence. No imports, no boilerplate — 40+ cleaning verbs are built into the language.

Under the hood, PipeScript is a complete, hand-written interpreter that integrates all eight classic phases of language design — lexing, parsing, scope/binding, semantic analysis, control flow, data types, and object orientation — served through a REST API and a browser-based IDE.

---

## Features

- **The `>>` pipeline operator** — the lowest-precedence operator, so whole expressions flow cleanly through stages.
- **Static typing** — `Int`, `Float`, `Bool`, `String`, plus `Array` and `Dict`, checked before execution.
- **40+ built-in cleaning verbs** — `removeBlanks`, `removeNegatives`, `fillNull`, `unique`, `sort`, `avg`, and more, with no imports.
- **Object orientation** — classes, methods, `new`, encapsulation — and a method dropped into a pipe **auto-maps** over a list.
- **Real error reporting** — every error carries its phase, a plain-English message, and a line number. The engine **never throws**.
- **A live web IDE** — the PipeScript Studio: editor with token-based syntax highlighting, console, and before/after data views.
- **Safety rails** — a 100,000-iteration guard turns infinite loops into a clean error instead of a hang.

---

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| **Compiler / interpreter** | **Python 3.10+**, standard library only | No third-party dependencies — pure `pipescript/` package |
| **Backend API** | **FastAPI** + **Uvicorn** | Thin wrapper exposing the engine over HTTP |
| **Request/response models** | **Pydantic v2** | Validation and typed schemas in `models.py` |
| **Frontend** | Single **HTML + vanilla JS** file | No framework, no build step — talks to the API via `fetch` |

---

## Repository structure

```
pipescript/                     # ── The language (pure-stdlib Python package) ──
│
├── tokens.py                   # Phase 2 · Token types + keyword table + Token dataclass
├── lexer.py                    # Phase 2 · Scans source text into a list of tokens
├── ast_nodes.py                # Phase 3 · Dataclasses for every AST node
├── parser.py                   # Phase 3–4 · Recursive-descent parser → AST
├── symbol_table.py             # Phase 4 · Chained scope frames for names & binding
├── semantic.py                 # Phase 5 · Two-pass type checker & error collector
├── interpreter.py              # Phase 6–8 · Tree-walking interpreter (control flow, types, OOP)
├── engine.py                   # The façade: chains all phases, returns one result dict
└── __init__.py                 # Public exports + package version

main.py                         # ── FastAPI server: /run, /validate, /examples, /health ──
models.py                       # Pydantic request/response schemas
requirements.txt                # Backend dependencies

pipescript_studio.html          # ── Frontend: the browser-based PipeScript Studio ──

BACKEND_README.md               # Detailed backend/API integration guide
presentation_script.md          # Speaker + live-demo script for the project defense
pipescript_presentation.html    # Slide deck (self-contained, opens in any browser)
```

---

## How it works — the files, together

PipeScript's key insight is that **the interpreter is itself a pipeline**. A program flows through the same left-to-right stages the language is built to express:

```
source .ps  >>  Lexer  >>  Parser  >>  Semantic  >>  Interpreter  >>  result
              (Phase 2)  (Phase 3–4)  (Phase 5)    (Phase 6–8)
```

Each file owns one stage, and [`engine.py`](engine.py) chains them:

1. **`lexer.py`** scans raw text into **tokens** (`tokens.py` defines them), tracking line and column for every one.
2. **`parser.py`** consumes those tokens via recursive descent and builds an **Abstract Syntax Tree** out of the nodes in `ast_nodes.py`. The `>>` operator is parsed at the lowest precedence so an entire expression can flow into a pipe.
3. **`semantic.py`** walks the AST in two passes — collect definitions, then type-check — reporting type mismatches, undeclared names, bad conditions, and more. `symbol_table.py` provides the chained scopes used for name resolution here and at runtime.
4. **`interpreter.py`** walks the validated tree and executes it: control flow, data types, casting, and object orientation.
5. **`engine.py`** ties the four together behind a single call — `PipeScriptEngine().run(code, data)` — and returns **one JSON-serialisable dict**, never an exception:

   ```python
   { "success": bool, "output": ..., "print_log": [...], "tokens": [...], "errors": [...] }
   ```

6. **`main.py`** exposes that engine over HTTP; **`models.py`** defines the typed request/response shapes; **`pipescript_studio.html`** is the client that renders it all.

The 8 project phases map to the code like this:

| Phase | Topic | Where it lives |
|---|---|---|
| 1 | Language Design | This README + overall syntax |
| 2 | Lexical Analysis | `tokens.py`, `lexer.py` |
| 3 | Syntax Analysis | `parser.py`, `ast_nodes.py` |
| 4 | Names, Scope & Binding | `symbol_table.py`, `parser.py` |
| 5 | Semantic Analysis | `semantic.py` |
| 6 | Control Flow | `interpreter.py` |
| 7 | Data Types | `interpreter.py`, `semantic.py` |
| 8 | Object Orientation | `interpreter.py`, `parser.py` |

---

## Getting started

### Prerequisites

- **Python 3.10 or newer** (the compiler uses `dataclass(kw_only=...)`).
- A modern web browser (for the Studio).

### 1 · Install backend dependencies

```bash
# from the repository root
pip install -r requirements.txt
```

> The `pipescript/` package itself has **no dependencies** — you only need these to run the web server.

### 2 · Start the API server

```bash
uvicorn main:app --reload --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`. Confirm it with:

- Interactive API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

### 3 · Open the Studio

Simply **double-click `pipescript_studio.html`** (or drag it into a browser). When opened from disk it automatically talks to the backend at `http://127.0.0.1:8000`. Type a program, hit **Run**, and watch it execute.

> No XAMPP, npm, or build step is involved — the frontend is a single self-contained file.

---

## Three ways to use PipeScript

### As a web app (the Studio)
Start the server (step 2) and open the Studio (step 3). This is the full experience: live syntax highlighting, console output, and before/after data.

### As a REST API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/run` | Lex → parse → analyze → **execute**; returns output, prints, tokens, errors |
| `POST` | `/validate` | Lint only (lex → parse → analyze), no execution — ideal for as-you-type checking |
| `GET` | `/examples` | Canned example programs for a "try an example" dropdown |
| `GET` | `/health` | Liveness check |

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"code":"pipeline { local Int[] a = [ -3, 25, null ]; print(a >> removeNegatives() >> removeBlanks()); }"}'
```

Full request/response contract: **[BACKEND_README.md](BACKEND_README.md)**.

### As a Python package

```python
from pipescript import PipeScriptEngine

result = PipeScriptEngine().run(code="""
pipeline {
    local Int[] ages = [25, -3, null, 41];
    ages >> removeNegatives() >> removeBlanks();
}
""")

print(result["success"])   # True
print(result["output"])    # cleaned data
```

---

## Language at a glance

```pipescript
// Globals and classes live above the pipeline block.
global Int passingScore = 50;

class Grader {
    String evaluate(Int score) {
        if (score < passingScore) { return "FAIL"; }
        return "PASS";
    }
}

pipeline {
    // Types: Int, Float, Bool, String, Array, Dict
    local Int[]  scores = [72, 40, 88, 15, 63];
    local String label  = "Batch A";

    // Objects: create with `new`, then pipe a method over the whole list
    Grader grader = new Grader();
    local Array results = scores >> grader.evaluate();   // ["PASS","FAIL","PASS","FAIL","PASS"]

    // Control flow: if / else, for, while
    for (local Int i = 0; i < len(scores); i = i + 1) {
        if (get(scores, i) > passingScore) { print(label, "->", get(scores, i)); }
    }

    // Type conversion
    local Int n = cast(Int, "42");
    print(results);
}
```

**Built-in verbs** include array cleaning (`removeBlanks`, `removeNegatives`, `fillNull`, `unique`, `sort`, `reverse`, `flatten`), info (`len`, `sum`, `avg`, `max`, `min`, `get`, `slice`), building (`append`, `prepend`, `range`), strings (`upper`, `lower`, `trim`, `replace`, `split`, `join`, `contains`), conversion (`toInt`, `toFloat`, `toString`, `cast`), and type checks (`isNull`, `isNumber`, `isString`, `isBool`). See [BACKEND_README.md](BACKEND_README.md#built-in-functions-available-in-pipescript) for the full list.

---

## Presentation materials

This repository also contains the project-defense assets:

- **[pipescript_presentation.html](pipescript_presentation.html)** — a self-contained slide deck. Open in a browser; navigate with `←`/`→`, press `F` for fullscreen and `N` for speaker notes.
- **[presentation_script.md](presentation_script.md)** — the full word-for-word speaker script (10-min design talk + 20-min live demo + roles).

---

## Known limitations

PipeScript is a teaching implementation with a deliberately small scope. Current gaps worth noting:

- **Array element types are not deeply checked** — `Int[]` is validated as an array, but individual element types are dynamic at runtime.
- **No user file I/O** — input arrives via the API's `data` parameter or in-script literals; output is returned in the result, not written to disk.

---

## Team

| Member | Role |
|---|---|
| Badilla, Don Lancelot F. | Backend & Project Lead |
| Regalado, Gian Carlo Miguel Q. | Data Modeling & Test Datasets |
| Lastrollo, Khylle Ghabriell D. | Frontend — PipeScript Studio |
| Gaytano, Kishia Nikole S. | Documentation, Script, Presentation & Video |

*All four members contributed to ideation and language design.*

---

## License

No license has been declared yet. As an academic project, all rights are reserved by the authors unless a license file is added.
