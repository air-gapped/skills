# Deep Research: Detailed Reference

## Table of Contents
- [Research Agent Prompt Template](#research-agent-prompt-template)
- [Question Decomposition Strategies](#question-decomposition-strategies): STORM · Funnel · Adversarial
- [Structured Extraction](#structured-extraction): facts · opinions · code · gaps
- [Source Quality Assessment](#source-quality-assessment): A/B/C tiers
- [Synthesis Patterns](#synthesis-patterns): Convergence · Divergence · Gap
- [Recursion Control](#recursion-control): when to recurse · when to stop · breadth halving
- [Report Templates](#report-templates): standard report · quick summary

## Research Agent Prompt Template

When spawning research subagents, use this template adapted for the specific angle:

```
You are a research agent investigating a specific angle of a broader topic.

BROADER QUESTION: {user_question}
YOUR ANGLE: {research_angle}
PRIOR LEARNINGS: {learnings_from_previous_rounds}

Instructions:
1. Use WebSearch to find 3-5 authoritative sources on your angle
2. For each promising result, use WebFetch to read the full content
3. Extract SPECIFIC information: names, numbers, dates, code snippets,
   direct quotes. Vague summaries are not useful.
4. Note any contradictions between sources
5. Identify 1-2 follow-up questions that emerged

Return your findings in this exact format:

LEARNINGS:
- [Specific finding] (Source: [url])
- [Specific finding] (Source: [url])
...

CONTRADICTIONS:
- [Source A] says X, but [Source B] says Y
...

FOLLOW_UPS:
- [Question that needs deeper investigation]
...

SOURCES:
- [url]: [one-line description of what it contained and its credibility]
...

CONFIDENCE: [high/medium/low] — how well-supported are your findings?
```

## Question Decomposition Strategies

### The STORM Pattern (Multi-Perspective)

For complex topics, decompose by perspective rather than subtopic:

```
Topic: "How should we implement rate limiting for our API?"

Perspectives:
1. Architecture: What are the standard patterns? (token bucket, sliding window, etc.)
2. Operations: What are the failure modes? What happens at scale?
3. User experience: How do clients handle rate limits? What headers/errors?
4. Security: How do attackers bypass rate limits? What are the edge cases?
5. Implementation: What libraries/services exist? Build vs. buy?
```

### The Funnel Pattern (Progressive Narrowing)

For topics where you need to go from broad to specific:

```
Round 1 (Broad): "What approaches exist for X?"
Round 2 (Narrow): "Among approaches A and B, what are the tradeoffs?"
Round 3 (Specific): "How do I implement approach A with our stack?"
```

### The Adversarial Pattern (Challenge Assumptions)

For decisions where you want to avoid confirmation bias:

```
Agent 1: Find evidence FOR approach X
Agent 2: Find evidence AGAINST approach X
Agent 3: Find alternatives to X that we haven't considered
```

## Structured Extraction

When processing search results, extract information into categories:

### Facts
Verifiable claims with specific numbers, dates, or named entities:
- "Redis supports 100K+ operations/second on a single node (source: Redis benchmarks)"
- "The sliding window algorithm uses O(1) memory per client (source: academic paper)"

### Opinions
Expert views that aren't purely factual:
- "Martin Fowler recommends starting with simple rate limiting before adding complexity"
- "The Stripe engineering blog argues against distributed rate limiting for most use cases"

### Code/Implementation Details
Specific technical artifacts:
- API signatures, configuration examples, command-line invocations
- Architecture diagrams described in text
- Performance characteristics under specific conditions

### Gaps
Things you looked for but couldn't find:
- "No benchmarks found comparing approach A vs B at our scale"
- "Couldn't find production experience reports for library X"

## Source Quality Assessment

Rate sources on a 3-tier scale:

| Tier | Description | Examples |
|------|-------------|---------|
| **A — Primary** | Official docs, peer-reviewed papers, first-party benchmarks, code repositories | RFC specs, library docs, academic papers |
| **B — Experienced** | Engineering blogs from known companies, conference talks, well-maintained tutorials | Stripe blog, InfoQ talks, Real Python |
| **C — Community** | Forum posts, Stack Overflow answers, personal blogs, social media | Reddit, HN comments, Medium posts |

When sources conflict, Tier A trumps B trumps C. When same-tier sources conflict,
note the contradiction and present both sides.

## Synthesis Patterns

### The Convergence Pattern

When multiple sources agree, strengthen the claim:
"All five sources consulted agree that X is the preferred approach for Y.
Specifically, [Source A] demonstrated this with [evidence], and [Source B]
confirmed it in a production environment at [scale]."

### The Divergence Pattern

When sources disagree, present the spectrum:
"There is no consensus on X. [Source A] argues for approach 1 because [reason],
while [Source B] prefers approach 2 because [different reason]. The choice likely
depends on [key variable that differs between their contexts]."

### The Gap Pattern

When information is missing, be explicit:
"We could not find reliable data on X. The closest information available is Y,
which applies to a related but different context. This is a gap that may require
[experimentation / asking domain experts / waiting for more data]."

## Recursion Control

### When to Recurse Deeper

- A follow-up question is directly relevant to the user's core question
- The current findings contain a significant contradiction that needs resolution
- A promising lead was found but not fully explored
- The user explicitly asked for deep/exhaustive research

### When to Stop Recursing

- The follow-up questions are tangential to the core question
- New searches are returning the same sources already consulted
- Confidence across all angles is "high"
- You've reached the configured depth limit
- The marginal value of more research is low (diminishing returns)

### Breadth Halving

At each depth level, cut the number of parallel queries in half:

```
Depth 0: 6 parallel agents (initial angles)
Depth 1: 3 parallel agents (top follow-ups)
Depth 2: 1-2 agents (final deep dives)
```

This focuses effort as you go deeper, preventing exponential blowup.

## Report Templates

### Standard Report

```markdown
# {Topic}: Research Report

*Generated on {date} | Depth: {depth} | Sources consulted: {count}*

## Executive Summary
{2-3 sentences directly answering the core question}

## Key Findings

### {Theme 1}
{Findings organized by theme, each citing sources}

### {Theme 2}
{...}

## Recommendations
{If applicable — actionable next steps based on findings}

## Competing Perspectives
{Where experts disagree, with evidence for each side}

## Gaps and Open Questions
{What we couldn't answer, and what would help}

## Methodology
{Research angles explored, depth, number of sources}

## Sources
| Source | Tier | Key Contribution |
|--------|------|-----------------|
| {url} | A | {what it provided} |
```

### Quick Summary (for Research-then-Optimize handoff)

```markdown
## Research Summary: {topic}

**Best practices found:**
1. {practice} — {evidence}
2. {practice} — {evidence}

**Common pitfalls:**
1. {pitfall} — {how to avoid}

**Recommended experiment hypotheses:**
1. {hypothesis} — based on {source}
2. {hypothesis} — based on {source}
```
