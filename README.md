<div align="center">

# PipeScript

**A minimal, statically-typed language for data-cleaning pipelines.**

*Design & Implementation of a Mini Programming Language — Final Project*
FEU Institute of Technology · Computer Science · Programming Languages

[![Live Site](https://img.shields.io/badge/Live_Site-GitHub_Pages-DA6B15?style=for-the-badge&logo=github)](https://kishiagaytano.github.io/pipescript/)
[![Live API](https://img.shields.io/badge/Live_API-Vercel-000000?style=for-the-badge&logo=vercel)](https://pipescript.vercel.app/docs)
[![Presentation](https://img.shields.io/badge/Slides-Deck-2A6E8C?style=for-the-badge)](https://kishiagaytano.github.io/pipescript/pipescript_presentation.html)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)

</div>

---

## 🔗 Live demo

| | Link |
|---|---|
| 🖥️ **Landing page & Studio** | **<https://kishiagaytano.github.io/pipescript/>** |
| 🎞️ **Presentation deck** | <https://kishiagaytano.github.io/pipescript/pipescript_presentation.html> |
| ⚡ **Live API** (FastAPI) | <https://pipescript.vercel.app> · interactive docs at [`/docs`](https://pipescript.vercel.app/docs) |

> Open the **Studio**, type a program, and hit **Run** — it executes on the live API in real time. No install required.

---

## What is PipeScript?

Most code that touches real-world data isn't analysis — it's **cleanup**. Removing negatives, dropping nulls, filling defaults, sorting. It's the same handful of steps, in the same order, every time. General-purpose tools like pandas can do it, but they wrap a four-word intent in six lines of ceremony.

**PipeScript makes that straight line the syntax.** Its defining feature is the `>>` **pipeline operator**, which feeds the output of one stage directly into the next:

```pipescript
pipeline {
    local Int[] ages    = [25, -3, null, 41, -9, null];
    local Int[] cleaned = ages >> removeNegatives() >> fillNull(0) >> sort();

    print("Cleaned:", cleaned);      // Cleaned: [0, 0, 3, 9, 25, 41]
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
| **Frontend** | **HTML + vanilla JS + CSS** | No framework, no build step |
| **Frontend hosting** | **GitHub Pages** | Static: landing page, presentation, Studio |
| **Backend hosting** | **Vercel** (Python serverless) | Runs the FastAPI app as a serverless function |

---

## Architecture — the hybrid deployment

PipeScript runs as a **hybrid**: a fully static frontend on **GitHub Pages**, and the Python backend as **serverless functions on Vercel**. The two are wired together at runtime — the Studio calls the Vercel API directly (CORS is open), so a visitor gets a live, interactive language with zero infrastructure to run.

```
┌────────────────── GitHub Pages · static frontend ──────────────────┐
│  index.html  ·  pipescript_presentation.html  ·  pipescript_studio.html
│  assets/styles.css
│  https://kishiagaytano.github.io/pipescript/
└───────────────────────────────┬────────────────────────────────────┘
                                 │
                    Studio  fetch()  ──►  POST /run, /validate …
                    (cross-origin, CORS "*")
                                 │
                                 ▼
┌────────────────── Vercel · Python serverless ──────────────────────┐
│  api/index.py   →   FastAPI app (main.py)   →   pipescript/ compiler
│  https://pipescript.vercel.app   →   /run  /validate  /examples  /health
└─────────────────────────────────────────────────────────────────────┘
```

**Why hybrid?** The presentation deck and landing page are 100% static — perfect for free, fast, zero-maintenance Pages hosting. Only the Studio needs a live backend, and the interpreter is **stateless**, which is an ideal fit for serverless functions. This also keeps the portfolio URL (`kishiagaytano.github.io/pipescript`) while still shipping a working Studio.

- **Frontend deploy:** GitHub Pages serves from the `main` branch root (`.nojekyll` disables Jekyll processing).
- **Backend deploy:** Vercel builds `api/index.py` (see `vercel.json`) from `requirements.txt` and serves the FastAPI app. Live endpoints are at the domain root: `https://pipescript.vercel.app/run`, `/validate`, `/examples`, `/health`, `/docs`.

---

## Repository structure

```
pipescript/                     # ── The language (pure-stdlib Python package) ──
├── tokens.py                   # Phase 2 · Token types + keyword table
├── lexer.py                    # Phase 2 · Scans source text into tokens
├── ast_nodes.py                # Phase 3 · Dataclasses for every AST node
├── parser.py                   # Phase 3–4 · Recursive-descent parser → AST
├── symbol_table.py             # Phase 4 · Chained scope frames (names & binding)
├── semantic.py                 # Phase 5 · Two-pass type checker
├── interpreter.py              # Phase 6–8 · Tree-walking interpreter
├── engine.py                   # Façade: chains all phases, returns one result dict
└── __init__.py                 # Public exports + version

main.py                         # ── FastAPI server: /run, /validate, /examples, /health ──
models.py                       # Pydantic request/response schemas
requirements.txt                # Backend dependencies (fastapi, uvicorn, pydantic)

api/index.py                    # ── Vercel serverless entry point (wraps main.py) ──
vercel.json                     # Vercel build & routing config
.nojekyll                       # Tell GitHub Pages to serve files as-is

index.html                      # ── Frontend: landing page (GitHub Pages home) ──
assets/styles.css               # Landing-page styles ("Schematic" design system)
pipescript_studio.html          # The browser-based PipeScript Studio (live IDE)
pipescript_presentation.html    # Self-contained slide deck

BACKEND_README.md               # Detailed backend/API integration guide
presentation_script.md          # Speaker + live-demo script for the defense
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
2. **`parser.py`** consumes those tokens via recursive descent and builds an **Abstract Syntax Tree** from the nodes in `ast_nodes.py`. The `>>` operator is parsed at the lowest precedence so a whole expression can flow into a pipe.
3. **`semantic.py`** walks the AST in two passes — collect definitions, then type-check — reporting type mismatches, undeclared names, bad conditions, and more. `symbol_table.py` provides the chained scopes used for name resolution.
4. **`interpreter.py`** walks the validated tree and executes it: control flow, data types, casting, and object orientation.
5. **`engine.py`** ties the four together behind a single call — `PipeScriptEngine().run(code, data)` — and returns **one JSON-serialisable dict**, never an exception.
6. **`main.py`** exposes that engine over HTTP; **`models.py`** types the request/response; **`api/index.py`** adapts it for Vercel; **`pipescript_studio.html`** is the client that renders it all.

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

## Getting started — local vs. production

You don't need to install anything to *try* PipeScript — just open the [live Studio](https://kishiagaytano.github.io/pipescript/). The steps below are for running it yourself.

### Prerequisites
- **Python 3.10 or newer** (the compiler uses `dataclass(kw_only=...)`).
- A modern web browser.

### Local development

```bash
# 1 · clone
git clone https://github.com/kishiagaytano/pipescript.git
cd pipescript

# 2 · install backend deps (the pipescript/ package itself has none)
pip install -r requirements.txt

# 3 · start the API locally
uvicorn main:app --reload --port 8000
#   → confirm at http://localhost:8000/docs

# 4 · open the Studio
#   double-click pipescript_studio.html (or drag it into a browser)
```

**How the Studio finds the backend.** On load it resolves its API base in this order:

1. `window.PIPESCRIPT_API_BASE__` — set by a small script in the page.
2. `localStorage["pipescriptApiBase"]` — an optional manual override.
3. Fallback: **`file://` → `http://127.0.0.1:8000`** (local), otherwise **same-origin**.

The Studio's `<head>` contains this hookup, which routes production traffic to Vercel while leaving local runs pointed at your own server:

```html
<script>
  // Served over the web (GitHub Pages) → use the hosted API.
  // Opened locally as a file:// → skipped, so it falls back to localhost:8000.
  if (location.protocol !== "file:") {
    window.PIPESCRIPT_API_BASE__ = "https://pipescript.vercel.app";
  }
</script>
```

So:
- **Opened locally** (`file://`) → the Studio talks to **your local `uvicorn` backend**. Ideal for development and the live demo.
- **Served in production** (GitHub Pages, `https://`) → the Studio automatically talks to the **Vercel API** at `https://pipescript.vercel.app`.

### Production deployment (reference)

- **Frontend → GitHub Pages:** *Settings → Pages → Deploy from a branch → `main` / `root`.* Everything static is served from the repo root.
- **Backend → Vercel:** import the repo at [vercel.com](https://vercel.com); Vercel detects `api/index.py` + `requirements.txt` and deploys the FastAPI app. CORS is already `allow_origins=["*"]`, so the Pages-hosted Studio can call it cross-origin.

---

## Using PipeScript

### As a web app (the Studio)
Open the [live Studio](https://kishiagaytano.github.io/pipescript/) — or run it locally per the steps above.

### As a REST API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/run` | Lex → parse → analyze → **execute**; returns output, prints, tokens, errors |
| `POST` | `/validate` | Lint only (no execution) — ideal for as-you-type checking |
| `GET` | `/examples` | Canned example programs |
| `GET` | `/health` | Liveness check |

```bash
curl -X POST https://pipescript.vercel.app/run \
  -H "Content-Type: application/json" \
  -d '{"code":"pipeline { print([ -3, 25, null ] >> removeNegatives() >> removeBlanks()); }"}'
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
global Int passingScore = 50;

class Grader {
    String evaluate(Int score) {
        if (score >= passingScore) { return "PASS"; }
        return "FAIL";
    }
}

pipeline {
    local Int[]  scores = [72, 40, 88, 15, 63];
    Grader grader = new Grader();

    // a method in a pipe runs on every item
    local Array results = scores >> grader.evaluate();   // ["PASS","FAIL","PASS","FAIL","PASS"]

    // control flow: if / else, for, while
    for (local Int i = 0; i < len(scores); i = i + 1) {
        if (get(scores, i) > passingScore) { print("high:", get(scores, i)); }
    }

    local Int n = cast(Int, "42");   // type conversion
    print(results);
}
```

**Built-in verbs** span array cleaning (`removeBlanks`, `removeNegatives`, `fillNull`, `unique`, `sort`, `reverse`, `flatten`), info (`len`, `sum`, `avg`, `max`, `min`, `get`, `slice`), building (`append`, `prepend`, `range`), strings (`upper`, `lower`, `trim`, `replace`, `split`, `join`, `contains`), conversion (`toInt`, `toFloat`, `toString`, `cast`), and type checks (`isNull`, `isNumber`, `isString`, `isBool`). Full list in [BACKEND_README.md](BACKEND_README.md#built-in-functions-available-in-pipescript).

---

## Presentation materials

- **[pipescript_presentation.html](pipescript_presentation.html)** — a self-contained slide deck. Navigate with `←`/`→`, press `F` for fullscreen and `N` for speaker notes.
- **[presentation_script.md](presentation_script.md)** — the full word-for-word speaker script (10-min design talk + 20-min live demo + roles).

---

## Known limitations

PipeScript is a teaching implementation with a deliberately small scope:

- **Array element types are not deeply checked** — `Int[]` is validated as an array, but individual element types are dynamic at runtime.
- **No user file I/O** — input arrives via the API's `data` parameter or in-script literals; output is returned in the result, not written to disk.
- **Cold starts** — the free-tier Vercel function may take ~1–2s to wake on the first request after a period of inactivity.

---

## Team

| Member | Role |
|---|---|
| Badilla, Don Lancelot F. | Backend & Project Lead |
| Regalado, Gian Carlo Miguel Q. | Data Modeling & Test Datasets |
| Lastrollo, Khylle Ghabriell D. | Frontend — PipeScript Studio |
| Gaytano, Kishia Nikole S. | Documentation, Script, Presentation, Video, Landing Page & Deployment |

*All four members contributed to ideation and language design.*

---

## License

No license has been declared yet. As an academic project, all rights are reserved by the authors unless a license file is added.
