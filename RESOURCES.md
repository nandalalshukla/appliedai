# Resources

The course is self-contained. These are the best free materials to go deeper, chosen after surveying the courses, repositories, talks and writing that practitioners actually recommend. They are grouped by module, and each list is short on purpose: a few things worth finishing beat fifty bookmarks.

**How to use this page.** After each module, pick the one item marked ★ and one other. Come back for the rest when a project needs it.

Links move. If one is broken, search for the title and author. Items after mid-2026 (the System One section in particular) are new and their claims are less settled; that is noted where it applies.

---

## Start here: the big picture

| Resource | Why |
|---|---|
| ★ [The Rise of the AI Engineer](https://www.latent.space/p/ai-engineer) (swyx) | The essay that named the role. Ten minutes; explains what the job is and is not |
| [AI Engineer roadmap](https://roadmap.sh/ai-engineer) (roadmap.sh) | A visual map of the skill areas; useful for seeing what this course covers and what it leaves out |
| [What We Learned from a Year of Building with LLMs](https://applied-llms.org/) | Six practitioners' hard-won lessons, tactical to strategic. Re-read it after Module 8; it will mean more |
| [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (Anthropic) | The clearest statement of "start simple; workflows before agents". Shapes Modules 2, 5 and 6 |
| *AI Engineering* by Chip Huyen (O'Reilly, 2025) | The best single book on the field. Paid, and worth it if you buy one book |
| [Arpit Bhayani's Applied AI course](https://arpitbhayani.me/applied-ai/) | The live cohort whose published topic list this course follows. Consider it if you want a live, instructor-led version |

## Full courses that pair well with this one

| Course | Best for |
|---|---|
| [Hugging Face Agents Course](https://huggingface.co/learn/agents-course) | A second angle on agents, with open-source frameworks |
| [Hugging Face LLM Course](https://huggingface.co/learn/llm-course) | Open models, transformers library, fine-tuning |
| [Generative AI for Beginners](https://github.com/microsoft/generative-ai-for-beginners) (Microsoft) | Gentle, lesson-by-lesson introduction with code |
| [AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) (Microsoft) | Agent design patterns, beginner pace |
| [Anthropic courses](https://github.com/anthropics/courses) | API fundamentals, an interactive prompt-engineering tutorial, tool use |
| [DeepLearning.AI short courses](https://www.deeplearning.ai/short-courses/) | One-to-two-hour courses on single topics (RAG, evals, agents, MCP) |
| [LLM Course](https://github.com/mlabonne/llm-course) (Maxime Labonne) | A roadmap with notebooks, strong on the open-model and fine-tuning side this course skips |
| [Large Language Model Agents](https://llmagents-learning.org/) (Berkeley MOOC) | Research-level lectures on agents |
| [Full Stack Deep Learning: LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/) | Older (2023) but the product and UX lectures hold up |

## Cookbooks to copy from

- [Claude Cookbooks](https://github.com/anthropics/claude-cookbooks): runnable notebooks for tool use, RAG, evals, caching, agents.
- [OpenAI Cookbook](https://cookbook.openai.com/): the same for OpenAI's API. Read these when porting labs to another provider.
- Provider docs: [Claude](https://platform.claude.com/docs), [OpenAI](https://platform.openai.com/docs), [Gemini](https://ai.google.dev/gemini-api/docs). Read your provider's prompt-engineering, tool-use and structured-output pages end to end once.

---

## Module 1: Foundations

- ★ [Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g) (Andrej Karpathy, 1 hour). The best general introduction there is.
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) (Karpathy). Lab 1.1, done thoroughly.
- [Neural networks series](https://www.3blue1brown.com/topics/neural-networks) (3Blue1Brown). Visual intuition for transformers and attention, no math background needed.
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) (Jay Alammar). The classic picture-led explanation.
- [Let's build GPT from scratch](https://www.youtube.com/watch?v=kCc8FmEb1nY) (Karpathy) and [LLMs from scratch](https://github.com/rasbt/LLMs-from-scratch) (Sebastian Raschka). Optional depth: build a small model yourself. Not required for the job; excellent for intuition.
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762). The transformer paper. Skim it once so the name means something.

## Module 2: Prompting

- ★ Your provider's prompt-engineering guide (for Claude: the prompt engineering section of the [docs](https://platform.claude.com/docs)). Current, specific, and written by the people who train the model.
- [Anthropic's interactive prompt engineering tutorial](https://github.com/anthropics/courses). Hands-on exercises.
- [Prompt Engineering Guide](https://www.promptingguide.ai/) (DAIR.AI). A catalogue of techniques with references.
- [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903). The original paper.
- [Prompt injection series](https://simonwillison.net/series/prompt-injection/) (Simon Willison). The most consistent, readable coverage of the problem. Read at least "the lethal trifecta" post.

### System One models

These are new (late 2026). Read the primary sources and treat vendor numbers as unverified until independently reproduced.

- [Introducing Clairic](https://blog.cloudflare.com/clairic-extraction-model/) (Cloudflare). The extraction model's announcement.
- [What is a System One model?](https://systemonemodels.org/guides/what-is-a-system-one-model/). A neutral overview of decision and extraction models.
- [awesome-system-one](https://github.com/andyrewlee/awesome-system-one). A list of models, alternatives and tools in this category.
- *Thinking, Fast and Slow* (Daniel Kahneman). Where the System 1 / System 2 names come from.

## Module 3: Tool use

- ★ "Writing effective tools for agents" on the [Anthropic engineering blog](https://www.anthropic.com/engineering). How to design, describe and evaluate tools.
- Your provider's tool-use documentation, including strict schemas and parallel calls.
- [Model Context Protocol](https://modelcontextprotocol.io/). Read the introduction and build the quickstart server.

## Module 4: RAG

- ★ [Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) (Anthropic). Hybrid search, re-ranking and chunk context, with measured gains.
- [Patterns for Building LLM-based Systems & Products](https://eugeneyan.com/writing/llm-patterns/) (Eugene Yan). RAG, evals, guardrails and caching in one long, well-referenced article.
- [Sentence Transformers documentation](https://sbert.net/). Embeddings, cross-encoders and the retrieve-then-re-rank pattern, with code.
- [Pinecone Learning Center](https://www.pinecone.io/learn/). Clear articles on vector search, HNSW and hybrid search (vendor-written; the fundamentals are sound).
- [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) (the original paper), [HyDE](https://arxiv.org/abs/2212.10496), and [Lost in the Middle](https://arxiv.org/abs/2307.03172).
- *Introduction to Information Retrieval* (Manning, Raghavan, Schütze; free online). The BM25 and evaluation chapters are the foundation under everything in this module.

## Module 5: Agents

- ★ [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (Anthropic). Read it again now.
- [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) (Lilian Weng). The reference overview of planning, memory and tool use.
- [Agents](https://huyenchip.com/2025/01/07/agents.html) (Chip Huyen). Planning, tools and failure modes, carefully explained.
- [12-Factor Agents](https://github.com/humanlayer/12-factor-agents). Principles for production agents: own your prompts, own your control flow, own your context.
- [ReAct](https://arxiv.org/abs/2210.03629). The paper behind Lab 5.2.
- [Claude Code documentation](https://code.claude.com/docs) and "Claude Code: best practices for agentic coding" on the [Anthropic engineering blog](https://www.anthropic.com/engineering). Use a coding agent daily and read how it is designed.
- [SWE-bench](https://arxiv.org/abs/2310.06770). How coding agents are evaluated; useful for Project 3, Step 10.

## Module 6: Memory and multi-agent

- ★ "Effective context engineering for AI agents" on the [Anthropic engineering blog](https://www.anthropic.com/engineering). Compaction, note-taking, subagents.
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (Anthropic). A production orchestrator-worker system, with honest cost numbers.
- [How and when to build multi-agent systems](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems) (LangChain). Reconciles the "do" and "don't" camps.
- [MemGPT](https://arxiv.org/abs/2310.08560) and [Generative Agents](https://arxiv.org/abs/2304.03442). The two papers most memory designs descend from.
- *Designing Data-Intensive Applications* (Martin Kleppmann). For Lab 6.4: locks, transactions and distributed failure, explained properly.

## Module 7: Evaluation and safety

- ★ [Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/) (Hamel Husain). The essay that convinced a generation of engineers. Then read his posts on [LLM judges](https://hamel.dev/blog/posts/llm-judge/).
- "Demystifying evals for AI agents" on the [Anthropic engineering blog](https://www.anthropic.com/engineering). Graders, tasks and trials for agents.
- [Evaluating the Effectiveness of LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) (Eugene Yan). What the research says about LLM-as-judge.
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/). The standard security checklist.
- Simon Willison's [prompt injection series](https://simonwillison.net/series/prompt-injection/), again. It matters more once your system has tools.

## Module 8: Production

- ★ [What We Learned from a Year of Building with LLMs](https://applied-llms.org/). The operational section in particular.
- [Building LLM applications for production](https://huyenchip.com/2023/04/11/llm-engineering.html) (Chip Huyen). Cost, latency and the engineering reality.
- Your provider's prompt-caching and batch-processing documentation. Read both fully; they are the largest free cost savings available.
- [OpenTelemetry](https://opentelemetry.io/docs/concepts/signals/traces/) concepts, and one LLM observability tool's docs ([Langfuse](https://langfuse.com/docs) is open source and can be self-hosted).
- [Reflexion](https://arxiv.org/abs/2303.11366). The research idea behind learning from failures (Lab 8.4).
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/). For the capstone.

## Module 9: System design

- [System Design Primer](https://github.com/donnemartin/system-design-primer). The general fundamentals (caching, queues, sharding) that AI system design assumes.
- *Designing Data-Intensive Applications* (Kleppmann). The reference.
- Engineering blogs from companies shipping AI products. Read them as case studies and ask of each: what are the evals, where is the human, what bounds the cost?
- [Arpit Bhayani's blog](https://arpitbhayani.me/) for system-design thinking generally.

## Module 10: Career

- [Louis-François Bouchard's AI engineering learning guide](https://www.louisbouchard.ai/learn-ai-engineering/). Another curated path, with difficulty levels.
- [Latent Space](https://www.latent.space/) (newsletter and podcast). The field's running conversation.
- [Simon Willison's weblog](https://simonwillison.net/). The best way to stay current without drowning.
- [AI Engineer](https://www.youtube.com/@aiDotEngineer) conference talks. Practitioners describing what they shipped.

---

## Staying current without burning out

The field changes monthly; the fundamentals in this course change slowly. A sustainable routine:

1. **One newsletter or blog**, not ten. Simon Willison's weblog or Latent Space is enough.
2. **Read release notes** of the provider you use. New features (caching options, structured outputs, tool types) are free capability.
3. **Re-run your evals** when a new model appears. That tells you more than any benchmark table.
4. **Build one small thing a month** with something new.
5. Ignore most hype. Ask of every announcement: what can I now build, or build more cheaply, that I could not before?

## A note on frameworks

This course writes loops, tools and retrieval by hand on purpose: frameworks hide the parts you most need to understand, and their APIs change faster than the ideas. Once you can build these things yourself, do learn one framework that your target employers use (LangGraph, LlamaIndex, the Vercel AI SDK, Pydantic AI, or a provider's agent SDK). You will pick it up in days, and you will know what it is doing underneath.
