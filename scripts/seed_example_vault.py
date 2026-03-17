#!/usr/bin/env python3
"""One-time script to seed example_vault with demo captures and notes."""

import re
from pathlib import Path

import frontmatter

VAULT = Path(__file__).resolve().parent.parent / "example_vault"


def _slug(title: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())[:5]
    return "-".join(words) if words else "capture"


def write_capture(title, insight, created, source="conversation", tags=None,
                  original=None, promoted_to=None):
    tags = sorted(tags or [])
    ts = created.replace("-", "").replace(":", "").replace("T", "-").split("+")[0]
    # Format: YYYY-MM-DD-HHMMSS
    # From ISO like 2026-01-10T08:30:00+00:00 → 2026-01-10-083000
    parts = created.split("T")
    date_part = parts[0]
    time_part = parts[1].split("+")[0].replace(":", "")
    filename = f"captures/{date_part}-{time_part}-{_slug(title)}.md"

    post = frontmatter.Post("")
    post["aliases"] = []
    post["created"] = created
    if promoted_to:
        post["promoted_to"] = promoted_to
    post["source"] = source
    post["status"] = "promoted" if promoted_to else "capture"
    post["tags"] = tags
    post["title"] = title
    post["updated"] = created

    # Build body
    body_parts = [insight]
    if source != "conversation":
        body_parts.append(f"Source: {source}")
    if original:
        body_parts.append(f"Original:\n{original}")
    post.content = "\n\n---\n\n".join(body_parts)

    path = VAULT / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dumps(post) + "\n")
    print(f"  ✓ {filename}")
    return filename


def write_note(title, domain, summary, content, promoted_from, tags=None,
               confidence=0.7, created="2026-03-01T10:00:00+00:00", aliases=None):
    tags = sorted(tags or [])
    slug = _slug(title)
    filename = f"notes/{slug}.md"

    post = frontmatter.Post("")
    post["aliases"] = aliases or []
    post["confidence"] = confidence
    post["created"] = created
    post["domain"] = domain
    post["promoted_from"] = promoted_from
    post["status"] = "note"
    post["tags"] = tags
    post["title"] = title
    post["updated"] = created

    post.content = f"# Summary\n\n{summary}\n\n# Notes\n\n{content}\n\n# Links"

    path = VAULT / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dumps(post) + "\n")
    print(f"  ✓ {filename}")
    return filename


def main():
    print("Seeding example_vault...\n")

    # ── tags.yaml ──────────────────────────────────────────────
    tags_yaml = VAULT / "tags.yaml"
    tags_yaml.write_text("""\
# Tag synonyms for auto-tag extraction
ai:
  - artificial intelligence
  - machine learning
  - deep learning
  - neural network
llm:
  - large language model
  - GPT
  - Claude
  - language model
learning:
  - spaced repetition
  - active recall
  - memorization
  - study
productivity:
  - workflow
  - efficiency
  - time management
  - automation
pkm:
  - personal knowledge management
  - second brain
  - note-taking
  - zettelkasten
programming:
  - coding
  - software engineering
  - development
  - code
health:
  - exercise
  - sleep
  - focus
  - wellness
writing:
  - drafting
  - editing
  - prose
  - composition
finance:
  - investing
  - budgeting
  - side project
  - revenue
prompt-engineering:
  - prompt design
  - few-shot
  - chain of thought
  - system prompt
""")
    print("  ✓ tags.yaml\n")

    # ── Group 1: Spaced Repetition & Learning (3 captures → 1 note) ──

    print("Group 1: Spaced Repetition & Learning")
    c1a = write_capture(
        "Spaced Repetition Improves Long Term Retention",
        "Spaced repetition systems like Anki leverage the forgetting curve to schedule reviews at optimal intervals. Research shows 90%+ retention rates compared to ~20% with passive re-reading after 30 days.",
        "2026-01-10T08:30:00+00:00",
        tags=["learning", "productivity"],
        promoted_to="notes/spaced-repetition-for-knowledge-workers.md",
    )
    c1b = write_capture(
        "Active Recall Beats Passive Review",
        "Testing yourself on material is far more effective than re-reading or highlighting. The retrieval practice effect strengthens memory traces each time you successfully recall information.",
        "2026-01-15T14:20:00+00:00",
        source="article",
        tags=["learning"],
        original="Dunlosky et al. (2013) meta-analysis of study strategies ranked practice testing and distributed practice as the two most effective techniques.",
        promoted_to="notes/spaced-repetition-for-knowledge-workers.md",
    )
    c1c = write_capture(
        "Integrating SRS Into Daily Workflow",
        "The key to sustainable spaced repetition is making reviews a daily habit of 10-15 minutes rather than marathon sessions. Link new cards to projects you care about to maintain motivation.",
        "2026-01-22T09:15:00+00:00",
        tags=["learning", "productivity"],
        promoted_to="notes/spaced-repetition-for-knowledge-workers.md",
    )

    n1 = write_note(
        "Spaced Repetition for Knowledge Workers",
        "learning",
        "Spaced repetition leverages the forgetting curve and active recall to achieve 90%+ long-term retention. The key is consistent daily practice of 10-15 minutes rather than cramming.",
        "1. **The forgetting curve**: Without review, we lose ~80% of new information within 30 days. SRS schedules reviews at optimal intervals to counteract this.\n\n2. **Active recall > passive review**: Testing yourself strengthens memory traces far more effectively than re-reading or highlighting (Dunlosky et al., 2013).\n\n3. **Sustainable habits**: Keep daily review sessions to 10-15 minutes. Link cards to active projects for motivation. Tools like Anki automate the scheduling.",
        promoted_from=[c1a, c1b, c1c],
        tags=["learning", "productivity"],
        confidence=0.85,
        created="2026-02-05T10:00:00+00:00",
        aliases=["SRS", "Spaced Repetition"],
    )
    print()

    # ── Group 2: LLM Prompt Engineering (3 captures → 1 note) ──

    print("Group 2: LLM Prompt Engineering")
    c2a = write_capture(
        "Chain of Thought Prompting Explained",
        "Adding 'let's think step by step' or providing worked examples dramatically improves LLM reasoning on math and logic tasks. Chain-of-thought prompting can boost accuracy by 20-40% on complex problems.",
        "2026-01-18T11:00:00+00:00",
        tags=["llm", "prompt-engineering", "ai"],
        promoted_to="notes/effective-llm-prompt-patterns.md",
    )
    c2b = write_capture(
        "System Prompts Set LLM Behavior",
        "System prompts establish the persona, constraints, and output format for LLM interactions. Well-crafted system prompts reduce the need for repeated instructions in user messages.",
        "2026-02-01T16:45:00+00:00",
        source="flash",
        tags=["llm", "prompt-engineering"],
        promoted_to="notes/effective-llm-prompt-patterns.md",
    )
    c2c = write_capture(
        "Few Shot Examples Improve Output Quality",
        "Providing 2-3 concrete input/output examples in the prompt helps the model understand the desired format and style. This technique is especially useful for structured outputs like JSON or tables.",
        "2026-02-10T08:00:00+00:00",
        tags=["llm", "prompt-engineering", "ai"],
        promoted_to="notes/effective-llm-prompt-patterns.md",
    )

    n2 = write_note(
        "Effective LLM Prompt Patterns",
        "ai",
        "Three core prompt engineering patterns—chain-of-thought, system prompts, and few-shot examples—significantly improve LLM output quality and reliability.",
        "1. **Chain-of-thought (CoT)**: Elicit step-by-step reasoning with phrases like 'think step by step' or by providing worked examples. Boosts accuracy 20-40% on complex reasoning.\n\n2. **System prompts**: Define persona, constraints, and output format upfront. Reduces repeated instructions and improves consistency across a conversation.\n\n3. **Few-shot examples**: 2-3 concrete input/output pairs help the model match desired format and style. Essential for structured outputs (JSON, tables, code).",
        promoted_from=[c2a, c2b, c2c],
        tags=["ai", "llm", "prompt-engineering"],
        confidence=0.8,
        created="2026-02-20T14:30:00+00:00",
    )
    print()

    # ── Group 3: Zettelkasten Method (2 captures → 1 note) ──

    print("Group 3: Zettelkasten Method")
    c3a = write_capture(
        "Zettelkasten Atomic Notes Principle",
        "Each zettel should contain exactly one idea, expressed in your own words. This atomicity makes notes maximally composable and reusable across different contexts and projects.",
        "2026-01-25T10:30:00+00:00",
        tags=["pkm", "writing"],
        promoted_to="notes/zettelkasten-core-principles.md",
    )
    c3b = write_capture(
        "Linking Notes Creates Emergent Structure",
        "In a Zettelkasten, structure emerges bottom-up through links between atomic notes rather than top-down through folders. This mirrors how ideas naturally connect and evolve over time.",
        "2026-02-03T19:00:00+00:00",
        source="article",
        tags=["pkm"],
        original="Ahrens, S. (2017). How to Take Smart Notes. The key insight is that a Zettelkasten is not a filing system but a thinking partner.",
        promoted_to="notes/zettelkasten-core-principles.md",
    )

    n3 = write_note(
        "Zettelkasten Core Principles",
        "pkm",
        "The Zettelkasten method centers on atomic notes (one idea each) and emergent structure through linking rather than hierarchical folders.",
        "1. **Atomicity**: Each note captures exactly one idea in your own words. This makes notes maximally composable—any note can participate in multiple lines of thought.\n\n2. **Bottom-up structure**: Instead of pre-defining folder hierarchies, let structure emerge through links between notes. This mirrors how ideas naturally connect.\n\n3. **Evergreen growth**: A Zettelkasten becomes more valuable over time as the link density increases, surfacing unexpected connections between ideas.",
        promoted_from=[c3a, c3b],
        tags=["pkm", "writing"],
        confidence=0.9,
        created="2026-03-01T10:00:00+00:00",
        aliases=["Zettelkasten"],
    )
    print()

    # ── Group 4: AI Coding Assistants (3 captures, unpromoted) ──

    print("Group 4: AI Coding Assistants")
    write_capture(
        "AI Pair Programming Changes Development Workflow",
        "Using AI coding assistants like Copilot and Claude shifts the developer's role from writing code to reviewing and guiding code generation. The key skill becomes writing clear specifications and catching subtle bugs in generated code.",
        "2026-02-08T13:00:00+00:00",
        tags=["ai", "programming"],
    )
    write_capture(
        "Context Window Limits Shape AI Coding",
        "The context window of LLMs fundamentally limits how much code an AI assistant can reason about at once. Effective use requires breaking problems into focused chunks and providing relevant context manually.",
        "2026-02-14T10:30:00+00:00",
        tags=["ai", "programming", "llm"],
    )
    write_capture(
        "Test Driven Development With AI Assistants",
        "Writing tests first and asking the AI to implement code that passes them is remarkably effective. The tests serve as an unambiguous specification that the AI can iterate against.",
        "2026-02-22T15:45:00+00:00",
        source="flash",
        tags=["ai", "programming"],
    )
    print()

    # ── Group 5: Second Brain / PKM (3 captures, unpromoted) ──

    print("Group 5: Second Brain / PKM")
    write_capture(
        "Capture Everything Process Later Principle",
        "The first step in building a second brain is lowering the friction of capture to near zero. Use quick-capture tools and worry about organization later during dedicated processing sessions.",
        "2026-01-12T07:45:00+00:00",
        tags=["pkm", "productivity"],
    )
    write_capture(
        "Progressive Summarization For Note Processing",
        "Tiago Forte's progressive summarization technique involves multiple passes: first highlight key passages, then bold the highlights, then write a brief summary. Each layer makes the note more accessible for future use.",
        "2026-02-05T11:20:00+00:00",
        source="article",
        tags=["pkm"],
        original="Forte, T. Building a Second Brain. The PARA method (Projects, Areas, Resources, Archives) provides an actionable organizational framework.",
    )
    write_capture(
        "Digital Gardens Versus Traditional Blogs",
        "Digital gardens are collections of evolving notes published at varying stages of completeness, unlike blogs which present polished, chronological posts. Gardens encourage exploration and connection over linear consumption.",
        "2026-03-05T09:30:00+00:00",
        tags=["pkm", "writing"],
    )
    print()

    # ── Group 6: Writing Workflow (2 captures, unpromoted) ──

    print("Group 6: Writing Workflow")
    write_capture(
        "Separate Drafting From Editing Phases",
        "Writing quality improves dramatically when you separate the creative drafting phase from the critical editing phase. Draft freely without self-censoring, then edit ruthlessly in a separate session.",
        "2026-02-18T08:00:00+00:00",
        tags=["writing", "productivity"],
    )
    write_capture(
        "Outline First Then Fill In Details",
        "Starting with a hierarchical outline before writing prose helps maintain coherent structure. Move sections around at the outline stage when the cost of restructuring is low.",
        "2026-03-02T14:00:00+00:00",
        source="flash",
        tags=["writing"],
    )
    print()

    # ── Group 7: Health & Focus (2 captures, unpromoted) ──

    print("Group 7: Health & Focus")
    write_capture(
        "Deep Work Requires Deliberate Environment Design",
        "Cal Newport argues that deep work—cognitively demanding tasks performed without distraction—requires intentional environment design. Remove phones, close email, and schedule focused blocks of 90 minutes or more.",
        "2026-01-20T06:30:00+00:00",
        source="article",
        tags=["health", "productivity"],
        original="Newport, C. (2016). Deep Work. The ability to perform deep work is becoming increasingly rare and increasingly valuable in our economy.",
    )
    write_capture(
        "Sleep Quality Affects Cognitive Performance",
        "Even mild sleep deprivation (6 hours vs 8 hours) significantly impairs working memory, decision-making, and creative problem-solving. Consistent sleep schedules matter more than occasional long nights.",
        "2026-02-25T21:00:00+00:00",
        tags=["health"],
    )
    print()

    # ── Group 8: Finance & Side Projects (2 captures, unpromoted) ──

    print("Group 8: Finance & Side Projects")
    write_capture(
        "Side Projects Need Clear Revenue Models",
        "Most side projects fail not from lack of technical ability but from unclear monetization strategy. Define your revenue model before writing code: who pays, how much, and why.",
        "2026-03-08T10:00:00+00:00",
        tags=["finance", "programming"],
    )
    write_capture(
        "Validate Ideas Before Building Full Products",
        "Spend 2 weeks validating demand with landing pages and waitlists before investing months in development. Talk to 10 potential customers and look for patterns in their pain points.",
        "2026-03-12T16:30:00+00:00",
        source="article",
        tags=["finance", "productivity"],
        original="Fitzpatrick, R. The Mom Test. The key is asking about their life, not your idea—people will lie to be polite about your concept.",
    )
    print()

    # ── Misc standalone captures ──

    print("Misc standalone captures")
    write_capture(
        "Obsidian Plugin Ecosystem Is Powerful",
        "Obsidian's community plugin ecosystem has over 1000 plugins covering everything from Kanban boards to spaced repetition. The Dataview plugin alone turns your vault into a queryable database.",
        "2026-01-14T12:00:00+00:00",
        tags=["pkm", "programming"],
    )
    write_capture(
        "Graph Databases Model Knowledge Naturally",
        "Graph databases like Neo4j represent knowledge as nodes and relationships, mirroring how human memory works through associations. They excel at queries like 'find all concepts connected to X within 2 hops'.",
        "2026-02-12T17:30:00+00:00",
        tags=["programming", "ai"],
    )
    write_capture(
        "Markdown Is The Universal Note Format",
        "Markdown's simplicity and ubiquity make it the safest long-term format for notes. Unlike proprietary formats, markdown files are portable, version-controllable, and readable without special software.",
        "2026-02-28T09:00:00+00:00",
        source="flash",
        tags=["pkm", "writing"],
    )
    write_capture(
        "Incremental Reading For Research Papers",
        "Incremental reading involves processing research papers in small chunks over multiple sessions, creating flashcards and notes as you go. This prevents the common pattern of reading a paper once and forgetting everything.",
        "2026-03-10T11:45:00+00:00",
        tags=["learning", "pkm"],
    )
    write_capture(
        "API Design Should Follow Conventions",
        "RESTful API design benefits from following established conventions: use nouns for resources, HTTP verbs for actions, consistent error formats, and pagination for list endpoints. Convention reduces cognitive load for consumers.",
        "2026-03-15T08:15:00+00:00",
        source="article",
        tags=["programming"],
        original="Masse, M. REST API Design Rulebook. Consistent URI design and standard HTTP status codes make APIs intuitive and self-documenting.",
    )
    print()

    # Count totals
    captures = list((VAULT / "captures").glob("*.md"))
    notes = list((VAULT / "notes").glob("*.md"))
    promoted = sum(1 for c in captures
                   if "promoted" in c.read_text().split("---")[1])
    print(f"Done! Created {len(captures)} captures ({promoted} promoted) and {len(notes)} notes.")


if __name__ == "__main__":
    main()
