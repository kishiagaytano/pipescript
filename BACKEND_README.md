# PipeScript — Backend Integration Guide

This document is for the **backend developer**.  
Your job is to wrap the `pipescript/` package in a FastAPI server.  
You do **not** need to touch any of the compiler files — just import and call one function.

> **✅ Status: implemented & deployed.** This backend now lives in [`main.py`](main.py) and is
> deployed as a serverless function on **Vercel**. See the [main README](README.md#architecture--the-hybrid-deployment)
> for the full hybrid architecture (static frontend on GitHub Pages + this API on Vercel).
>
> - **Live API:** <https://pipescript.vercel.app> · interactive docs at [`/docs`](https://pipescript.vercel.app/docs)
> - **Live endpoints** are served at the domain root: `/run`, `/validate`, `/examples`, `/health`.
> - The Vercel entry point is [`api/index.py`](api/index.py); local runs use `uvicorn main:app --port 8000`.

---

## What You're Getting

The `pipescript/` folder is a complete Python package that implements the PipeScript language compiler and interpreter.  
It covers all 8 phases of the language:

| File | What it does |
|---|---|
| `tokens.py` | Defines every token type (keywords, operators, delimiters) |
| `lexer.py` | Scans source code text into a list of tokens |
| `ast_nodes.py` | Data classes for every node in the syntax tree |
| `parser.py` | Builds the syntax tree from tokens, enforces grammar |
| `symbol_table.py` | Tracks variable scopes (global / local) |
| `semantic.py` | Type-checks the tree and catches logical errors |
| `interpreter.py` | Executes the tree — runs if/else, loops, classes, pipelines |
| `engine.py` | **The only file you need to import.** Chains all the phases together. |

---

## Setup

```bash
# No external dependencies — pure Python 3.10+
# Just make sure the pipescript/ folder is in the same directory as your main.py

your_project/
├── main.py          ← your FastAPI app goes here
├── pipescript/      ← the package (do not modify)
│   ├── __init__.py
│   ├── engine.py
│   └── ...
└── requirements.txt
```

Your `requirements.txt`:
```
fastapi
uvicorn
```

---

## The One Function You Need

```python
from pipescript import PipeScriptEngine

code = """
pipeline {
  local Dict record = { age: -2, name: "Ada", active: true, score: null };
  local Dict cleaned = record >> removeNegatives() >> removeBlanks() >> fillNull(0);
  print(cleaned);
  cleaned;
}
"""

result = PipeScriptEngine().run(code=code)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `code` | `str` | The PipeScript source code the user typed in the editor |
| `data` | `any` (optional) | External input dataset — injected as the variable `input_data` inside the script when supplied. If the dataset is written directly in the script as an array or dict literal, the backend can infer it and `data` may be omitted. |

### Return value

`run()` always returns a dict — it never raises an exception:

```python
{
    "success":   True,           # False if any error occurred
    "output":    [...],          # The final value produced by the pipeline block
    "print_log": ["cleaned: 5"], # Every print() call in order — show these in the console pane
    "tokens":    [...],          # Full token list — send this to the frontend for syntax highlighting
    "errors": [                  # Empty list on success
        {
            "phase":   "Semantic",          # Which compiler phase caught the error
            "message": "Type mismatch ...", # Plain-English explanation — show this to the user
            "line":    3                    # Line number in the editor to highlight
        }
    ]
}
```

---

## FastAPI Integration (Full Example)

Create `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List, Optional
from pipescript import PipeScriptEngine

app = FastAPI(title="PipeScript API")

# Allow requests from the frontend (adjust origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    code: str
    data: Optional[Any] = None   # list, list of dicts, or null


@app.post("/run")
def run_pipeline(req: RunRequest):
    """
    Execute PipeScript code and return the result.
    The frontend sends the code string + optional input data.
    """
    return PipeScriptEngine().run(code=req.code, data=req.data)


@app.get("/health")
def health():
    return {"status": "ok"}
```

Run it:
```bash
uvicorn main:app --reload --port 8000
```

---

## API Contract with the Frontend

### POST /run

**Request body (JSON):**
```json
{
  "code": "pipeline { local Int[] ages = [-3, 25, null]; local Int[] c = ages >> removeNegatives() >> removeBlanks(); print(c); }",
  "data": null
}
```

**Success response:**
```json
{
  "success": true,
  "output": [3, 25],
  "print_log": ["[3, 25]"],
  "tokens": [
    { "type": "PIPELINE", "value": "pipeline", "line": 1, "col": 1 },
    { "type": "LBRACE",   "value": "{",        "line": 1, "col": 10 }
  ],
  "errors": []
}
```

**Error response (e.g. type mismatch):**
```json
{
  "success": false,
  "output": null,
  "print_log": [],
  "tokens": [...],
  "errors": [
    {
      "phase": "Semantic",
      "message": "Type mismatch on line 2: cannot assign a 'String' value to 'x' which is declared as 'Int'.",
      "line": 2
    }
  ]
}
```

---

## What to Tell the Frontend Developer

From the response, the frontend needs to use:

| Field | Where to display it |
|---|---|
| `tokens` | Color the editor — each token has a `type`, `line`, and `col` |
| `print_log` | The **After / Console** pane — one line per entry |
| `errors[].message` | The console pane when `success` is false |
| `errors[].line` | Highlight that line number red in the editor |
| `output` | Optionally show as the final cleaned dataset in the bottom-right table |

### Token types for syntax highlighting

Use the `type` field from each token. Suggested color scheme matching the UI spec:

| Token types | Suggested color |
|---|---|
| `T_INT`, `T_FLOAT`, `T_STRING`, `T_BOOL` | Green |
| `PIPELINE`, `CLASS`, `IF`, `ELSE`, `FOR`, `WHILE`, `RETURN` | Blue / purple |
| `GLOBAL`, `LOCAL`, `CAST`, `NEW` | Blue |
| `PIPE` (`>>`) | Bright orange |
| `STRING_LIT` | Orange / amber |
| `INT_LIT`, `FLOAT_LIT` | Teal |
| `TRUE`, `FALSE`, `NULL` | Red |
| `IDENT` | White / default |

---

## Built-in Functions Available in PipeScript

These are callable inside any pipeline without importing anything:

**Array cleaning:**
`removeBlanks()`, `removeNegatives()`, `fillNull(default)`, `unique()`, `sort()`, `reverse()`, `flatten()`

**Array info:**
`len(arr)`, `sum(arr)`, `avg(arr)`, `max(arr)`, `min(arr)`, `get(arr, i)`, `slice(arr, start, end)`

**Array building:**
`append(arr, item)`, `prepend(arr, item)`, `range(start, stop, step)`

**String:**
`upper(s)`, `lower(s)`, `capitalize(s)`, `trim(s)`, `replace(s, old, new)`,
`split(s, sep)`, `join(sep, arr)`, `contains(s, sub)`, `startsWith(s, pre)`, `endsWith(s, suf)`

**Type conversion:**
`toString(x)`, `toInt(x)`, `toFloat(x)` — or use `cast(Type, expr)` syntax

**Type checks:**
`isNull(x)`, `isNumber(x)`, `isString(x)`, `isBool(x)`

**I/O:**
`print(...)` — output appears in `print_log`

---

## Quick Test (no FastAPI needed)

Run this from your terminal to confirm the package works before writing any API code:

```python
# test_pipescript.py
from pipescript import PipeScriptEngine

code = """
pipeline {
    local Int[] ages = [-3, 25, null, -10, 42];
    local Int[] cleaned = ages >> removeNegatives() >> removeBlanks() >> fillNull(0);
    print(cleaned);
}
"""

result = PipeScriptEngine().run(code)
print("Success:", result["success"])
print("Output: ", result["output"])
print("Printed:", result["print_log"])
print("Errors: ", result["errors"])
```

Expected output:
```
Success: True
Output:  [3, 25, 10, 0, 42]
Printed: ['[3, 25, 10, 0, 42]']
Errors:  []
```
