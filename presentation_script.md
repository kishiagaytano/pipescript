# PipeScript — Full Presentation Script

**Final Project · Design & Implementation of a Mini Programming Language**
FEU Institute of Technology · Programming Languages

| Segment | Length | Content |
|---|---|---|
| 1. Design Presentation | 10 min | Slides 1–17, split across 4 members |
| 2. Live Demo | 20 min | Two programs in the PipeScript Studio + a live error |
| 3. Roles & Participation | 4 min | Slide 18 |

**Team**

| Member | Role |
|---|---|
| Badilla, Don Lancelot F. | Backend & Project Lead |
| Regalado, Gian Carlo Miguel Q. | Data Modeling & Test Datasets |
| Lastrollo, Khylle Ghabriell D. | Frontend — PipeScript Studio |
| Gaytano, Kishia Nikole S. | Docs · Script · Presentation · Video |

**Cue key:** `[SLIDE CHANGE]` = press `→` once · `[POINT]` = gesture at screen · `[PAUSE]` = beat · `[TYPE]` / `[CLICK]` / `[EXPECT]` = demo actions.
The deck is slide-based (no sub-animations) — one `[SLIDE CHANGE]` per advance.

---
---

# SEGMENT 1 — DESIGN PRESENTATION (10 min)

**Runtime:** ~10:00 · **Pace:** conversational, ~140 wpm

| Part | Speaker | Slides | Time |
|---|---|---|---|
| 1 | Kishia Gaytano | 1–4 | ~2:30 |
| 2 | Don Badilla | 5–8 | ~2:45 |
| 3 | Gian Regalado | 9–12 | ~2:30 |
| 4 | Khylle Lastrollo | 13–17 | ~2:15 |

---

## PART 1 — KISHIA · The Hook & The Problem
*(Slides 1–4 · ~2:30)*

**`[SLIDE 1 — Title/Hook]`**

> Quick question… have you ever written code just to *fix a spreadsheet?*
>
> …Yeah. All of us.
>
> Here's the uncomfortable truth about working with data: most of the code we write **isn't the interesting part.** It's not the analysis. It's not the insight. It's **cleanup.**
>
> Today, we're going to show you a language we built that treats cleanup as a first-class citizen. It's called **PipeScript.** I'm Kishia — with me are Don, Gian, and Khylle — and in the next ten minutes, we'll take you from a **messy spreadsheet** all the way down to the **compiler** that cleans it.

**`[SLIDE CHANGE → 2 — The Problem]`**

> So let's start with the mess.
>
> Here's a tiny column of ages. **`[POINT]`** Look at it. There's a **negative three** — nobody is negative three years old. Two **nulls**, where somebody just… forgot to type. And it isn't even sorted.
>
> Before you can compute a *single* average, you have to fix all of this. And here's the thing… it's always the **same** fixes. Drop the blanks. Correct the negatives. Fill the gaps. Sort. Every dataset — the same ritual.

**`[SLIDE CHANGE → 3 — The Friction]`**

> Now — you *could* reach for Python and pandas. People do.
>
> But watch what happens. The **intent** is four words: remove negatives, drop nulls, fill defaults, sort. Four words. **`[PAUSE]`**
>
> The **code?** Import a library… build a DataFrame… boolean masks… dropna… fillna… sort… reset the index. That's six lines of ceremony for four words of meaning.
>
> The task is a **straight line**… but the code **zig-zags.** So we asked ourselves — what if the code could be as straight as the intent?

**`[SLIDE CHANGE → 4 — The Solution]`**

> That's PipeScript.
>
> Here is that *exact* same cleanup. **`[POINT to the line]`** **One line.** And you read it left to right, like a sentence: take `ages`… pipe it through `removeNegatives`… then `fillNull`… then `sort`.
>
> That little **double-arrow** — the pipe operator — is the **heart** of the whole language. Each stage hands its result straight to the next. No masks. No imports. No reset-index. Forty-plus cleaning verbs, built right in.
>
> But a language that reads *this* simply has to do a **lot** of work underneath. So I'll hand it to Don, our project lead, to open up the engine.

---

## PART 2 — DON · The Design & The Engine
*(Slides 5–8 · ~2:45)*

**`[SLIDE CHANGE → 5 — Phase 1: Language Design]`**

> Thanks, Kishia.
>
> So before we wrote a single line of the compiler, we made some deliberate design decisions.
>
> PipeScript has **one job** — data pipelines — and **one strong opinion:** that pipe operator flows over *everything*, so we made it the **lowest-precedence** operator in the language.
>
> Around that, we kept it familiar and safe. It's **statically typed** — Int, Float, Bool, String, plus Arrays and Dicts. It uses **C-style** braces and semicolons, so nobody has to relearn how to write an if-statement. And every program has exactly **one entry point:** the `pipeline` block.

**`[SLIDE CHANGE → 6 — Program Anatomy]`**

> Here's a whole program.
>
> Up top — **globals**, our shared constants. Then a **class**, which gives us objects — Gian and Khylle will come back to those. And then the **pipeline** block, which is where execution actually begins.
>
> Notice it still reads top-to-bottom like any language you already know. The only magic is in that **pipe line** at the bottom.

**`[SLIDE CHANGE → 7 — Architecture]`**

> Now this is my favorite part — and it's the idea that ties this entire talk together.
>
> How does the interpreter turn that text into a result? **It runs its own pipeline.** **`[POINT across the flow]`**
>
> Your source code flows through a **Lexer**… then a **Parser**… then a **Semantic** analyzer… then the **Interpreter**… and out comes a **result.** The compiler is literally built the same way the language *thinks.*
>
> And all of it lives behind **one function** — `engine.run()`. Here's the best part: it **never crashes.** It never throws an exception in your face. Every possible error — a typo, a type mismatch — comes back as **clean data:** which phase failed, what went wrong, and the exact **line number.**

**`[SLIDE CHANGE → 8 — Phase 2: Lexical Analysis]`**

> So let's actually follow the data through. Stage one — the **Lexer.**
>
> Its job is simple but critical: turn raw text into **tokens.** It scans left to right, one character at a time, and tags every piece — *this* is an identifier, *this* is the pipe, *this* is a paren. It even records the **line and column** of every token — that's how our errors can point at exactly the right spot later.
>
> And here's a subtle one: when it sees a greater-than sign, it has to **decide** — is this "greater than"… or the start of our double-arrow pipe? That one decision is where the language's personality begins.
>
> Gian will take it from tokens… into structure.

---

## PART 3 — GIAN · Structure & Safety
*(Slides 9–12 · ~2:30)*

**`[SLIDE CHANGE → 9 — Phase 3: Syntax Analysis]`**

> Thanks, Don.
>
> So now we have a flat **list** of tokens — but a list isn't a program. Stage two, the **Parser**, gives it shape.
>
> It's a **recursive-descent** parser, and it turns those tokens into a **tree** — an Abstract Syntax Tree. Look at our pipe line *as* a tree: **`[POINT]`** the whole thing becomes a **Pipeline node**, with a *source* — `ages` — and a list of *steps* hanging off it.
>
> And remember Don said the pipe is the lowest-precedence operator? **This** is why — it lets an *entire* expression flow into a pipe with zero ambiguity. The grammar guarantees the structure is **legal** before we run a thing.

**`[SLIDE CHANGE → 10 — Phase 4: Names, Scope & Binding]`**

> Once we have the tree, we need to know where every **name** lives. That's scope and binding.
>
> We use a **chain** of scope frames — global on the outside, then the pipeline, then each block nested inside. When you use a variable, the language checks your current block first… then walks **outward** until it finds it. An inner variable can **shadow** an outer one.
>
> So the language always knows *exactly* which `i`, or which `score`, you meant. And if you use a name that was never declared — it **catches** you.

**`[SLIDE CHANGE → 11 — Phase 5: Semantic Analysis]`**

> Now the safety net — **semantic analysis.** This is where we catch mistakes **before a single line runs.**
>
> It makes two passes: first it collects every definition, then it type-checks the whole tree. It catches type mismatches, undeclared variables, conditions that aren't actually true-or-false, wrong argument counts, calling a method that doesn't exist.
>
> Here's a real one. **`[POINT]`** Declare `x` as an Int… then try to assign it the string `"hello"`. The analyzer **stops**, and tells you: *line 3 — you can't put a String into an Int.*
>
> And because we caught it **here**… the interpreter never even starts. Bad data never gets to run.

**`[SLIDE CHANGE → 12 — Phase 6: Control Flow]`**

> And when the code *is* valid — we run it.
>
> PipeScript has the control flow you'd expect: `if`/`else`, `for`, and `while`, all executed by walking that tree.
>
> And one thing we're proud of — a **safety valve.** If a loop ever runs past a **hundred thousand** iterations, we assume it's infinite and stop it cleanly. So a student's typo becomes a **friendly error**… not a frozen screen.
>
> Khylle will take us into data types and objects.

---

## PART 4 — KHYLLE · Data, Objects & The Handoff
*(Slides 13–17 · ~2:15)*

**`[SLIDE CHANGE → 13 — Phase 7: Data Types]`**

> Thanks, Gian.
>
> So what can PipeScript actually **hold?** Four primitives — Int, Float, Bool, String — plus **Arrays** and **Dicts** for real records.
>
> And the operators are **type-aware.** Plus between two numbers *adds*; plus between two strings *joins* them. Divide two ints, you get an int; bring in a float, you get a float. And when you need to convert, there's **`cast`** — turn the string `"42"` into the *number* 42.
>
> The language knows the type of **every value, at every step.**

**`[SLIDE CHANGE → 14 — Phase 8: Object Orientation]`**

> It's also **object-oriented.** You define a class with its own fields and methods, create instances with `new`, and each method can read its own object's data — that's **encapsulation.**
>
> But here's the payoff — and it's my favorite feature in the whole language. Drop a method **into a pipe** — like `grader >> evaluate` — and it automatically runs on **every item** in the list. **`[POINT]`** One line… grades the whole class.
>
> That's objects and pipelines, working together.

**`[SLIDE CHANGE → 15 — Recap]`**

> So let's zoom all the way back out.
>
> **Eight phases** — from design, through the lexer, the parser, scope, semantics, control flow, types, and objects — and it *all* collapses into **one clean result.** Success or failure, the output, everything printed, the tokens, and any errors — all as **structured data.**
>
> And that is *exactly* what our frontend — the **PipeScript Studio** — reads to highlight your code and show your results.

**`[SLIDE CHANGE → 16 — The Bridge]`**

> So we've taken you all the way **down** — from a messy spreadsheet, through every stage of a real interpreter — and back **up** to a finished result.
>
> But the best way to *believe* it… is to watch it run.

**`[SLIDE CHANGE → 17 — Demo Title Card]`**

> And that's exactly what's next.
>
> In our demo, we'll open the Studio and run **two real programs** — the data-cleaning pipeline you saw at the very start, and the object-oriented grader — from raw text… to tokens… to **cleaned output**, live.
>
> Let's watch PipeScript make cleanup **the point.** **`[PAUSE]`**
>
> Roll the demo.

**`[END OF 10-MINUTE SEGMENT — cut to the demo video]`**

---
---

# SEGMENT 2 — LIVE DEMO (20 min)

**Setup before recording:**
1. Backend running: `uvicorn main:app --port 8000` (status pill in the Studio should read **online**).
2. Open `pipescript_studio.html` in the browser, full screen.
3. Clear the editor before each example so the audience sees it typed fresh.

> **Every output below is the real, verified result from the interpreter.** If your screen shows something different, the backend isn't running or the code was mistyped.

| Part | Driver / Voice | Content | Time |
|---|---|---|---|
| A | Khylle | Studio tour | ~2:00 |
| B | Don + Kishia | Demo 1 — data-cleaning pipeline | ~7:00 |
| C | Gian | Demo 2 — OOP grading pipeline | ~7:00 |
| D | Gian / Don | Live error — semantic safety net | ~3:00 |
| E | Kishia | Wrap | ~1:00 |

---

## PART A — KHYLLE · The Studio Tour *(~2:00)*

> This is the **PipeScript Studio** — the environment we built to run the language.
>
> On the **left**, the code editor. As you type, it's **syntax-highlighted** using the exact token stream Don described — every color you see is the Lexer's output coming straight back from the backend.
>
> Up here **`[POINT to status pill]`** is our backend status — right now it says **online**, meaning the FastAPI server and the interpreter are live.
>
> On the **right**, three things we'll watch on every run: the **console**, where anything you `print` shows up in order… the **Before / After** view of your data… and inline **errors**, if the compiler catches anything.
>
> Nothing here is faked — every time we hit **Run**, the code makes a real round trip: through the lexer, the parser, the semantic analyzer, and the interpreter… and comes back as one structured result. Let's prove it. Don?

---

## PART B — DON + KISHIA · Demo 1 · The Data-Cleaning Pipeline *(~7:00)*

**`[CLEAR EDITOR]`**

**DON:**
> Remember the messy ages from the start of the talk? Let's actually clean them — for real this time. I'll build it up step by step.

**`[TYPE — line by line, narrating as you go]`**

```
pipeline {
    local Int[] ages = [25, -3, null, 41, -9, null];
    print("Raw ages:", ages);
    local Int[] cleaned = ages >> removeNegatives() >> fillNull(0) >> sort();
    print("Cleaned:", cleaned);
    print("Average age:", avg(cleaned));
    cleaned;
}
```

**DON (while typing):**
> We open the `pipeline` block — that's our entry point. We declare `ages` as an `Int` array, and it's got everything wrong with it: a negative three, a negative nine, and two nulls.
>
> Then the star of the show — the pipe line. `ages`… pipe into `removeNegatives`… pipe into `fillNull` with a default of zero… pipe into `sort`. Three stages, left to right.
>
> And I'll print the raw and the cleaned versions so we can compare.

**KISHIA:**
> Before we run it — notice the highlighting already happened as Don typed. That's the lexer working live. Now watch the pipe operator turn this list from dirty to clean.

**`[CLICK — Run]`**

**`[EXPECT — Console shows exactly:]`**
```
Raw ages: [25, -3, None, 41, -9, None]
Cleaned: [0, 0, 3, 9, 25, 41]
Average age: 13.0
```

**KISHIA (walking the result):**
> There it is. **`[POINT to "Raw"]`** The input — negatives, nulls, unsorted.
>
> **`[POINT to "Cleaned"]`** And the output. Look what each stage did: `removeNegatives` flipped the negative three and negative nine into **positive** three and nine… `fillNull` turned the two nulls into **zeros**… and `sort` lined them all up. `[0, 0, 3, 9, 25, 41]`.
>
> And then, because the data's finally clean, we could do something useful with it — `avg` gives us **thirteen**. That average would've been *impossible* on the raw data.

**DON:**
> And that's the whole point of the language in one screen. The code reads exactly like the sentence: *remove negatives, fill nulls, sort.* No loops. No masks. No imports. The pipe did the threading for us — each stage's output became the next stage's input, automatically.

*(Optional, if time allows — show tokens:)*
> If we peek at the token view, you can see the raw material the parser worked from — `IDENT`, then our `PIPE`, then `IDENT`, `LPAREN`, `RPAREN`. That flat stream is what became the tree.

---

## PART C — GIAN · Demo 2 · Objects in a Pipe *(~7:00)*

**`[CLEAR EDITOR]`**

**GIAN:**
> Demo one was data flowing through built-in verbs. Now let's bring in **our own logic** — a class — and show off Phase 8, object orientation. We're going to grade a batch of exam scores.

**`[TYPE]`**

```
global Int passingScore = 50;

class Grader {
    String evaluate(Int score) {
        if (score < passingScore) {
            return "FAIL";
        }
        return "PASS";
    }
}

pipeline {
    local Int[] scores = [72, 40, 88, 15, 63];
    Grader grader = new Grader();
    local Array results = scores >> grader.evaluate();
    print("Results:", results);
    results;
}
```

**GIAN (while typing):**
> First, a **global** — `passingScore`, fifty. That's a program-wide constant.
>
> Then a **class**, `Grader`, with one method: `evaluate`. It takes a `score`, and if it's **below** the passing score, it returns `"FAIL"`, otherwise `"PASS"`. Notice the method reads `passingScore` even though it's not a parameter — that's scope walking outward to the global, exactly like the scope chain we showed.
>
> *(Aside for the panel:)* we're using **less-than** here deliberately — it keeps the logic clean and reads naturally as "below passing."
>
> Now the pipeline. Five scores. We create a `Grader` with `new`. And here's the magic line: `scores` pipe into `grader.evaluate`.

**`[CLICK — Run]`**

**`[EXPECT — Console shows exactly:]`**
```
Results: ['PASS', 'FAIL', 'PASS', 'FAIL', 'PASS']
```

**GIAN (walking the result):**
> Look closely at what just happened. I wrote `evaluate` to grade **one** score — a single Int. But I piped in a **list of five.**
>
> And the language **automatically mapped** my method over every element. `72` → PASS. `40` → FAIL. `88` → PASS. `15` → FAIL. `63` → PASS. **`[POINT]`** One line graded the entire class.
>
> That's the feature we're proudest of: your own object methods behave just like the built-in verbs the moment you drop them into a pipe. Encapsulated logic — a class that owns its own rule — flowing through the exact same operator. Objects and pipelines, working as one.

---

## PART D — GIAN / DON · The Safety Net · A Live Error *(~3:00)*

**`[CLEAR EDITOR]`**

**DON:**
> One more thing — because a language is only as trustworthy as its *errors*. Let me deliberately make a mistake.

**`[TYPE]`**

```
pipeline {
    local Int x = 5;
    x = "hello";
}
```

**DON (while typing):**
> I declare `x` as an **Int**, give it five… and then, on the next line, I try to shove the **string** `"hello"` into it. That's a type violation. In a lot of little interpreters, this would blow up at runtime with an ugly stack trace.

**`[CLICK — Run]`**

**`[EXPECT — Error panel / console shows:]`**
```
Semantic · line 3
Cannot assign a 'String' value to 'x' (declared as 'Int').
```

**GIAN:**
> No crash. No stack trace. Instead — a clean, plain-English message: **line three**, you can't put a String into an Int.
>
> And notice the label: **Semantic.** This never reached the interpreter. Our analyzer caught it *before* execution and the engine returned it as **structured data** — the phase, the message, and the line number — which is exactly what lets the Studio underline line three for you.
>
> That's the "never throws" promise Don made earlier, on screen. Every mistake becomes feedback, not a failure.

*(Optional — show it's fixable:)*
> **`[CHANGE `"hello"` to `50`, Run again → succeeds]`** Fix the type… and it runs. The compiler was right.

---

## PART E — KISHIA · Demo Wrap *(~1:00)*

> So — three runs, no smoke and mirrors.
>
> We cleaned a messy dataset in a single readable line. We graded a whole batch of scores by dropping a **class method into a pipe.** And we watched the compiler **catch a bad type before it ran** and explain itself in plain English.
>
> Every one of those went through all eight phases we walked you through — lexer, parser, scope, semantics, control flow, types, and objects — and came back as one clean result.
>
> That's PipeScript: a small language, with a strong opinion, that makes the boring part — **cleanup** — the part you actually enjoy writing.
>
> **`[PAUSE]`** Next, we'll quickly cover who built what.

**`[CUT TO — Roles & Participation segment, Slide 18]`**

---
---

# SEGMENT 3 — ROLES & PARTICIPATION (4 min)

**`[SLIDE 18 — Roles & Participation]`**

Each member states their contribution (~45 sec each):

- **Don Badilla — Backend & Project Lead.**
  Owned the interpreter and the `engine.py` that chains all eight phases, wrapped it in the FastAPI server, and coordinated the team.

- **Gian Regalado — Data Modeling & Test Datasets.**
  Designed the sample datasets and the `Dict` / `Array` record shapes the language cleans, and stress-tested the pipeline against messy, real-world-style inputs.

- **Khylle Lastrollo — Frontend, PipeScript Studio.**
  Built the browser-based Studio — the live editor, token-based syntax highlighting, and the console / before-after / error panels wired to the API.

- **Kishia Gaytano — Docs, Script, Presentation & Video.**
  Authored the documentation, wrote this script, designed the slide deck, and produced and edited the presentation video.

> And all four of us shared the **ideation and language design** — the syntax, the `>>` operator, and the decision to build the whole thing around data cleaning.

**`[SLIDE CHANGE → 19 — Closing]`**

> **`[Any member, together:]`** Most data code is cleanup. PipeScript makes cleanup the point. **`[PAUSE]`** Thank you — we're happy to take questions.

**`[END]`**
