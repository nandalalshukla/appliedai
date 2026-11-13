# Module 10: Career - portfolio, interviews, job search

**Week 16.** You have the skills. This module is about making them visible to the people who hire, and about what the interviews look like.

A caution first: no course can promise a job. Hiring depends on the market, your location, your background and luck. What you control is whether you can do the work and whether that is obvious within two minutes of someone opening your profile. This module is about that.

---

## 10.1 What companies hire AI engineers to do

Read twenty job descriptions for "AI engineer", "applied AI engineer", "LLM engineer" or "software engineer, AI". The same needs recur:

| They write | They mean | Where you learned it |
|---|---|---|
| "Build LLM-powered features" | Prompts, structured outputs, tool use, shipped behind an API | Modules 2-3, Projects 1 and 6 |
| "Experience with RAG" | Retrieval that is measured and debugged, not a tutorial copy | Module 4, Project 2 |
| "Build agents" | Loops with limits, approvals and recovery | Modules 5-6, Projects 3-4 |
| "Evaluation" | Datasets, scorers, a regression gate | Module 7, Project 5 |
| "Production experience" | Latency, cost, monitoring, reliability, security | Module 8, Project 6 |
| "Strong software engineering" | Clean code, tests, APIs, git, debugging | Every project |

Notice the last row. An AI engineer is a software engineer first. If your general engineering is weak (data structures, HTTP, databases, testing, git), strengthen it in parallel; it is examined in almost every hiring process.

**Roles to search for:** AI engineer, applied AI engineer, LLM engineer, generative AI engineer, software engineer (AI/ML), forward-deployed engineer, solutions engineer (AI), AI product engineer. At smaller companies the title is often just "software engineer" on a team building AI features.

## 10.2 Your portfolio

Three strong projects beat ten weak ones. Reviewers spend about two minutes; design for that.

### What a strong project README contains

1. **One sentence:** what it does and for whom.
2. **A demo:** a link that works, or a 60-second video or GIF.
3. **An architecture diagram.** A simple box diagram is enough.
4. **Numbers.** An eval table, latency, cost per request. This is the single thing that most sets a portfolio apart.
5. **Decisions and trade-offs.** "I chose hybrid search because keyword search alone missed paraphrases: recall@3 went from 0.6 to 0.9."
6. **What went wrong.** Two or three failures and how you found and fixed them.
7. **Limitations and next steps.** Shows judgment.
8. **How to run it.** Three commands.

### Which projects to show

- **Lead with the capstone** (deployed, traced, tested).
- **Add the coding agent** (recognizable, and it shows you understand agents from the loop up).
- **Add one that is unmistakably yours**: a course project rebuilt on your own data or for a real user. A RAG system over your university's regulations that classmates use, an agent that triages issues on an open-source project you care about, a tool for a family business. A real user, even one, changes how the project reads.

### Make it yours

Reference solutions exist in this repository, and reviewers have seen many tutorial clones. What distinguishes yours: a different domain, your own eval set, your own measurements, and a write-up of what *you* learned. Never present the reference solution as your own work; a single interview question exposes it.

## 10.3 Write in public

One short post per project, on a blog, LinkedIn or X. Not a tutorial: a finding.

- "My RAG system's recall was 60%. Here are the three changes that took it to 92%, and the two that did nothing."
- "I compared one agent with four on the same eight questions. The team cost five times more and won only twice."
- "Six ways I got my own assistant to leak its system prompt, and what stopped each."

Writing proves that you can communicate, which is half the job. It also gives interviewers something specific to ask about, and it is how most unexpected opportunities arrive.

Other ways to become visible: fix a bug or improve the docs in an open-source AI project you used; answer questions in communities; give a ten-minute talk at a local meetup.

## 10.4 The CV

- One page. Projects above education if you lack relevant experience.
- Every bullet has the shape **did X, using Y, resulting in Z (a number)**.

| Weak | Strong |
|---|---|
| Built a RAG chatbot using LangChain | Built a cited Q&A service over 2,000 documents with hybrid retrieval and query rewriting; raised recall@3 from 0.61 to 0.93 on a 60-question eval set |
| Worked on AI agents | Built a coding agent that fixed 4 of 5 seeded-bug tasks in a median of 7 steps at about $0.04 per task, with sandboxed file access and human approval for commands |
| Familiar with evals | Wrote an eval harness with a CI regression gate; a validated LLM judge raised bad-answer detection from 67% to 95% |

The numbers above are illustrations of the format. Use only numbers you measured yourself.

- Link the deployed capstone and the repositories at the top.
- List skills you can discuss for ten minutes each. Nothing else.

## 10.5 The interview loop

Loops vary. These rounds are common.

### 1. Coding

Ordinary software-engineering problems, sometimes with an AI flavour (implement a rate limiter, an LRU cache, a tokenizer, top-k search, a retry wrapper). Practise standard data structures and algorithms. Several labs in this course are real interview questions: BPE merges (1.1), BM25 and RRF (4.2), cycle detection (6.4), a sliding-window limiter (capstone).

### 2. AI system design

"Design a customer-support agent." Use the framework in [Module 9](../09-system-design/README.md), in order: clarify, define success, choose the simplest shape, draw the data flow, go deep on the hard parts, failure modes, evaluation. Practise aloud with a timer. The seven designs and five practice prompts are your preparation.

### 3. Practical AI engineering

Either a take-home or a live session: "here is a prompt and twenty failing cases, improve it", or "build a small RAG pipeline over these files". What they watch for:

- Do you **look at the data** before changing anything?
- Do you **build a small eval** first, or tune by feel?
- Do you **check `stop_reason`**, validate outputs, handle errors?
- Can you **explain trade-offs** as you go?

This is where having built the projects by hand pays off.

### 4. Project deep dive

"Tell me about something you built." They will keep asking why. Prepare for each portfolio project:

- The problem, and who had it
- The architecture, drawn in under two minutes
- The hardest bug, and how you found it
- A decision you would make differently
- The numbers: quality, latency, cost
- What would break at 100 times the scale

### 5. Behavioural

Collaboration, disagreement, ownership, a failure. Use real examples with the structure situation, action, result, and what you learned.

### Questions you should be able to answer

**Fundamentals**
1. What happens between sending a prompt and receiving a response?
2. Why do models hallucinate, and what reduces it?
3. What is a context window, and why not always fill it?
4. Explain embeddings and cosine similarity to a non-engineer.

**Prompting and structured outputs**
5. How do you make a prompt reliable across thousands of inputs?
6. Constrained output guarantees valid JSON. What does it not guarantee?
7. What is prompt injection, and why are delimiters insufficient?

**Tools and agents**
8. Walk through a tool call from request to final answer.
9. What makes a good tool description?
10. Workflow or agent: how do you decide?
11. How do you stop an agent that is stuck in a loop?
12. How would you make an agent resumable after a crash? What could go wrong on resume?
13. When is a multi-agent system justified?

**RAG**
14. A RAG answer is wrong. Describe your debugging process.
15. Keyword search, vector search, hybrid: when does each win?
16. What is re-ranking, and why two stages?
17. How do you enforce document permissions in RAG?

**Evals**
18. How do you know your system is good?
19. How do you build an eval set from nothing?
20. When would you use an LLM as a judge, and how do you trust it?
21. A change improves the average and breaks two cases. What do you do?

**Production**
22. How does prompt caching work, and what silently breaks it?
23. Your bill doubled this week. How do you investigate?
24. How do you cut latency for a chat feature?
25. What do you log for every model call?
26. A provider has an outage. What does your product do?

For each, practise a two-minute answer that includes an example from your own projects. "In my capstone, I..." is the strongest opening you have.

### Questions to ask them

- How do you evaluate your AI features today? What does a regression look like?
- What happens when the model is wrong in front of a customer?
- Who decides when a prompt or model change ships?
- What is the hardest production issue you have had with an LLM system?

Their answers tell you how mature the team is, and asking them shows that you know what matters.

## 10.6 A job-search routine

A sustainable weekly plan while you search:

| Activity | Share of time |
|---|---|
| Applications, tailored to the role (quality over volume) | 25% |
| Direct outreach: engineers and hiring managers at companies you would like to join, with a specific note about their product and a link to relevant work | 25% |
| Interview practice: coding, one system design aloud, mock interviews with a friend | 25% |
| Building and writing: improve a project, publish a finding | 25% |

Practical notes:

- **Referrals and direct messages work better than cold applications.** A short, specific message beats a long generic one: who you are, one thing you built that relates to their work, one clear ask.
- **Startups building AI products** often value demonstrated ability over credentials. Show them the capstone.
- **Internal moves count.** If you are already a software engineer, the easiest path is often building an AI feature where you work now. Propose one, with an eval plan.
- **Freelance or open-source work** is real experience. A shipped project for a paying client, however small, changes your CV.
- **Track everything** in a spreadsheet: company, role, date, contact, stage, notes.
- **Expect rejection.** It is normal and mostly not about you. Ask for feedback, adjust, continue.

## 10.7 Working as an AI engineer: habits that compound

- **Look at the data.** Read real inputs and outputs every week. No dashboard replaces it.
- **Start with the simplest thing**, and add complexity only when an eval says you must.
- **Write the eval before the fix.**
- **Treat every output as untrusted** until validated.
- **Know your costs.** Per request, per user, per month.
- **Use AI tools daily** for your own work (a coding agent, a research assistant). You will understand your users, and you will be faster.
- **Stay honest about uncertainty.** "It passes 46 of 50 cases, and here are the four it fails" is the sentence of a professional.
- **Take responsibility for impact.** These systems affect people. Privacy, fairness, safety and honesty about being an AI are part of the engineering, not an afterthought.

## 10.8 After this course

Directions to grow, depending on your interests:

| Direction | What to learn next |
|---|---|
| Deeper on models | Fine-tuning, open models, inference and serving, quantization |
| Deeper on retrieval | Search engines, learning to rank, knowledge graphs, multimodal retrieval |
| Deeper on agents | Durable execution, sandboxing, computer use, long-horizon evaluation |
| Product | UX for AI, experiment design, user research |
| Infrastructure | Model gateways, GPU serving, observability platforms |
| Safety | Red teaming, interpretability, policy |
| Voice and multimodal | Real-time speech, vision, document understanding |

Pick one, build something with it, write about it. That loop is the whole career.

---

## Final checklist

- [ ] Three projects with strong READMEs, each with numbers
- [ ] The capstone deployed, with a budget on the key
- [ ] One project that is unmistakably your own
- [ ] One published post about something you measured
- [ ] A one-page CV with quantified bullets
- [ ] The 26 questions practised aloud
- [ ] Five system designs done against a timer
- [ ] Two mock interviews
- [ ] A tracking sheet and a weekly routine

You started this course able to write basic Python. You can now build, measure, secure and ship AI systems, and explain every decision in them. Go and build something people use.
