# ERR0RS Academic Architecture

**Codename:** The Equalizer
**Status:** Vision document v1 (2026-05-20) — living architecture
**Mission statement:** *Give the student with nothing a teacher better than what money can buy.*

---

## Part I — The mission

### Who we serve

ERR0RS is built for everyone curious about cybersecurity:

- **Kids** — the 12-year-old who watched their parent on the laptop and wondered "how does that work?"
- **High schoolers** — the senior who found offensive security through HackTheBox or a video and wants to go deep
- **Self-funded students** — the community-college student working full-time who can't drop $1,600 on OSCP or $8K on SANS
- **Career-changers** — the 35-year-old in IT helpdesk who knows they could do this if someone would teach them
- **International students** — anyone whose internet is unreliable, monitored, or expensive; offline-first isn't a feature, it's their only option
- **The curious** — anyone, any age, anywhere, who wants to think like an attacker and a defender

This is not a slogan. It is the constraint that drives every design decision. If a feature serves credentialed CS majors at well-funded R1 universities but excludes the 16-year-old on a hand-me-down laptop in Oklahoma City, the feature is wrong. We design for the latter and let the former benefit incidentally.

### What we're competing with

Not other educational platforms. The real competitors are:

1. **Cost** — every dollar charged is a student excluded
2. **Internet access** — every cloud dependency is a student excluded
3. **Privacy** — every datapoint we capture is a student we make vulnerable
4. **Cognitive load** — every confusing interface is a student who quits
5. **Mediocrity** — every educational platform that produces graduates who can pass a cert but can't operate

We win by giving away, locally, privately, simply, and excellently what others charge for, host remotely, surveil, complicate, and water down.

---

## Part II — The soul

### What makes ERR0RS different

**Other platforms teach about tools. ERR0RS teaches tools.** A student finishing ERR0RS should drop into a real engagement and operate — not describe operating.

But the deeper thing, the soul:

**The goal is to nurture a mind that thinks adversarially AND defensively.** Tools are vocabulary. Tradecraft is grammar. Mindset is the language. We are in the business of cultivating minds, not transferring facts.

### What "thinking like an attacker" actually means

It is a cognitive posture, not a body of knowledge:

- **Threat modeling reflexively** — looking at any system and asking "what does the attacker want here?" before "how does this work?"
- **Asymmetric thinking** — defenders must be right always; attackers must be right once. Living inside this asymmetry changes how you see every system.
- **Misuse imagination** — given a feature, immediately seeing the 4-5 ways it can be turned against its owner
- **Patience as a weapon** — real attacks aren't speed-runs. Recon, wait, recon, wait, strike. Most students never feel the rhythm.
- **Comfort with uncertainty** — you don't know what's behind the firewall. You hypothesize, test, revise. Most education teaches certainty; this is the opposite.
- **Opsec as identity, not checklist** — leaving no trace isn't a step; it's a state of being while operating

### What "thinking like a defender" means (and why most aren't)

- **Detection over prevention** — assume breach. The question becomes "how fast did I see them?"
- **Threat-informed defense** — defending against *something specific* (a TTP, an actor, an asset target), not "everything"
- **Adversarial empathy** — to defend against an attacker, you must genuinely understand why they'd come for you
- **Cost asymmetry awareness** — every control costs. Bad defenders deploy controls; good defenders deploy the right ones for the actual threat.
- **Telemetry as a sense organ** — logs aren't paperwork; they're how you see in the dark
- **Communication under fire** — IR is 30% technical, 70% communication. Most programs don't teach this at all.

### Why ERR0RS uniquely can do this

Real academia struggles to teach mindset because:
- Lectures are one-way (no chance to *practice* the thinking)
- Labs are scripted (the "attacker" path is predetermined — no adversarial creativity required)
- Most professors don't have current operator experience

ERR0RS is conversational. It's not a content-delivery system; it's a *partner that already has the mindset and helps the student grow theirs through dialogue.* That is the unlock.

---

## Part III — The structure

### Three tiers, mindset throughout

Students progress through three tiers as they mature. Each tier has its own pedagogy, scope, and risk profile. **Mindset cultivation is layered into every tier — it is not a separate track.**

#### EXPLORE (curiosity stage)

**Who:** kids, total beginners, the curious
**Goal:** "I understand how the magic works."
**Stakes:** none — pure exploration, no real targets, no real consequences
**Pedagogy:** story-driven, concept-first, narrative explanations of why systems are vulnerable
**Tools:** illustrated, simulated, gameplay-shaped
**Mindset seeds (age-appropriate):**
- Reflexive curiosity: "I wonder what would happen if..."
- Pattern recognition: "I've seen this kind of thing before"
- Empathy for both sides: explain a heist from the thief's view AND the bank's view
- No real-world tradecraft yet — we're building the *muscle of looking*, not teaching the moves

**Example session:** "How does a website know who you are?" → playful walkthrough of cookies, sessions, what happens if someone steals one → simple visualization → "what would you do if you were defending against this?"

#### LEARN (skill stage)

**Who:** self-funded students, career-changers, high-schoolers ready for real
**Goal:** "I can do this in a lab and explain why each step matters."
**Stakes:** controlled — vulnerable labs (Juice Shop, DVWA, HTB starting boxes), simulated environments, sandbox VMs
**Pedagogy:** guided scenario-based learning with real tools, with ERR0RS coaching through choices
**Tools:** the real registry tools used on safe targets, with full opsec teach attached
**Mindset cultivation:**
- Dual-perspective teach on every card (attacker view + defender view, side by side)
- "Why did you do that?" probing after every meaningful action
- Threat actor narrative framing ("APT28 used this technique in 2022 against X")
- Beginning of adversarial role-play (small scenarios, clear boundaries)

**Example session:** Guided Juice Shop SQL injection with full opsec walkthrough — what the WAF would see, what shows up in mod_security logs, what a defender's first detection signal would be, what the attacker does to evade it. Student does it themselves; ERR0RS coaches and probes.

#### OPERATE (judgment stage)

**Who:** aspiring red teamers, students prepping for OSCP/PNPT/CRTP, working operators sharpening skills
**Goal:** "I can make calls in ambiguous, time-pressured, real-world engagements."
**Stakes:** real — open-ended engagements against complex lab networks, full kill chains, real deliverables
**Pedagogy:** scoped-freedom engagements; ERR0RS as senior operator partner, not handholder
**Tools:** full registry, full BlackArch Phoenix arsenal, real C2 frameworks
**Mindset cultivation:**
- Full adversarial role-play (engagement scenarios with red/blue switching)
- Mindset assessment via conversation (ERR0RS judges *reasoning*, not just whether the box got popped)
- Reflection prompts as standard engagement closer
- Threat actor emulation exercises (operate as a specific APT against an assumed target profile)

**Example session:** "You have 4 hours, one foothold on an internal Windows workstation, and the objective of demonstrating domain compromise. Plan your approach. I'll question your choices and surface what you're not thinking about." Student operates; ERR0RS probes, doesn't railroad.

### The bridge problem

**The most important pedagogical design problem in the project: how does a student safely move from EXPLORE to LEARN to OPERATE without either getting stuck or getting hurt?**

Specifically: a kid in EXPLORE running real tools against real targets is a legal disaster waiting to happen (CFAA does not care about age). A student in LEARN attempting OPERATE-tier engagements without the foundations will flail and quit.

Our answer:

1. **Capability gating** — certain tools/features are locked until the student has demonstrated the prerequisite understanding (not just clicked through a lesson — *demonstrated*)
2. **Lab-by-default, scope checking always** — real tools only operate against environments that have been explicitly authorized; ERR0RS guardrails check every target every time
3. **Legal/ethical curriculum BEFORE tradecraft** — a student cannot reach LEARN without completing the legal foundations module (CFAA, ROE, authorization, responsible disclosure). This is non-negotiable.
4. **Bridges are explicit** — moving tiers is a deliberate event with a conversation, not an automatic level-up

---

## Part IV — The mindset features (prototype priority)

Five features that operationalize mindset cultivation. These are the features that make ERR0RS *not just another tool*.

### 1. Dual-perspective teach (HIGHEST LEVERAGE — prototype first)

Every teach card already has red-team tradecraft. We add a `defender_view` field with matched depth:
- What the SIEM operator sees during this attack
- What EDR alerts fire and which artifacts trigger them
- What the forensic analyst will find later (file artifacts, registry, memory)
- What the incident responder's first 30 minutes look like
- What the threat hunter looks for to find this proactively

Result: **the 67 teach cards become 134 perspectives**, and every student finishing ERR0RS thinks adversarially AND defensively about every tool. This alone is the single biggest differentiator we can build.

Schema impact: add `defender_view` field to v3 registry. Backward compatible. Generator (`tools/generate_teach.py`) extends to produce paired content. Build-time only.

### 2. "Why did you do that?" probing (HIGH LEVERAGE — prototype second)

After any meaningful action a student takes — running a tool, choosing a payload, selecting a target — ERR0RS asks one of a rotating set of metacognitive probes:

- "Why this tool over the alternatives?"
- "What does this leave behind?"
- "What's the noisy version of this? Why didn't you do that?"
- "If you had to redo this in half the time, what would you cut?"
- "What would a defender see right now?"
- "What's the next thing you assume is true that might not be?"

The questions are short. The student answers in their own words. The student's pattern of answers becomes their growth signal.

Implementation: hooks into the existing event bus we shipped in `af1f0e3`. Tool-completion event fires a metacog probe in the CLI.

### 3. Adversarial role-play scenarios

Structured scenarios where the student picks a side. Two formats:

**Red-side:** "You have [time], [access], [objective]. Plan and execute. ERR0RS asks why at decision points but doesn't solve for you."

**Blue-side:** "You see [anomaly] in [system]. Walk me through your hypothesis, your investigation, your response. ERR0RS plays the attacker covering tracks."

Real magic: same scenarios available from both sides. A student plays it as red, then plays it as blue against a recording of their own red-side run. Adversarial empathy made visceral.

Implementation: scenario YAML/JSON in `src/scenarios/` with success/failure criteria, plus an engagement-mode wrapper around the conversation engine.

### 4. Threat actor narrative mode

When teaching a TTP, ERR0RS frames it through real-world threat actors:

- "This is how APT28 used Kerberoasting in 2022 against German government targets..."
- "Conti used this exact privilege escalation in the [target] breach. Here's why it worked, here's where they slipped up, here's what they did differently in the next campaign..."
- "Lapsus$ favored this approach because [reason]. Here's what made them effective and where the operator discipline broke down..."

Tools become attached to consequences and context. Students learn that the line between operator and criminal is not the tool — it's authorization, scope, and judgment.

Implementation: extend teach cards with `threat_actor_examples` field. Cross-reference MITRE Groups (G####) the same way we already cross-reference Techniques (T####).

### 5. Mindset assessment via conversation (THE RADICAL ONE)

Forget multiple choice. ERR0RS evaluates whether a student *thinks like* an operator by having a conversation with them.

Example: *"You just got shell on a domain-joined Windows workstation. Slow down. Don't run any commands yet. Talk me through your thinking. What's your first hypothesis? What are you NOT going to do, and why?"*

The student's *reasoning* is the assessment. ERR0RS evaluates:
- Did the student threat-model before acting?
- Did they identify what they don't know?
- Did they consider opsec before tradecraft?
- Did they articulate priorities and tradeoffs?
- Could they defend their choices when challenged?

This requires real LLM judgment — exactly what we have. It's also unfakeable in a way multiple-choice tests aren't. **No other platform does this.**

Implementation: scenario library + LLM rubric for evaluation + reflection summary written to the student's portfolio. Highest engineering complexity of the five features; highest pedagogical payoff.

### 6. Reflection journal (THE COMPOUNDING ONE — sequenced after features 1-5)

Every engagement and meaningful teach session ends with structured reflection:

- *"What did you assume that turned out wrong?"*
- *"What surprised you?"*
- *"What would you tell yourself before starting this engagement again?"*
- *"Which opsec consideration almost cost you this run?"*
- *"What's the one thing you'd do differently with another hour?"*

The student answers in their own words. Each entry is timestamped, tagged with the tool/scenario/MITRE-technique involved, and stored privately to the student's local journal. Over time, **the journal compounds into the student's own pattern data** — the curriculum tailored to them, written by them, drawn from their own growth.

**Why this is sequenced AFTER features 1-5:** the journal has nothing to compound until students are doing real metacognition (feature 2), running real engagements (feature 3), and being assessed on reasoning (feature 5). Building the journal first would mean students journaling about nothing. Building it after means students journaling about content that already taught them something. It is the keystone feature that locks the other five into long-term skill development.

Implementation: SQLite-backed local journal + reflection prompt rotation hooked into engagement-end and teach-session-end events + retrospective query mode ("show me everywhere I struggled with opsec last month"). Privacy: lives in `~/.err0rs/journal/`, never leaves the device.

---

## Part V — The honest tensions

This document would be dishonest if it didn't name the hard problems.

### Tension 1: "All ages" vs. real tools

A 12-year-old running real pen-test tools against real targets is a legal disaster. CFAA doesn't care about age. The bridge from EXPLORE (story-driven, no real tools) to LEARN (real tools, vulnerable labs) is the most important pedagogical design problem. **Answer:** capability gating + legal foundations as gateway + lab-by-default with scope guardrails. EXPLORE never touches real tools; LEARN only touches authorized targets; OPERATE requires explicit lab provisioning.

### Tension 2: Open-ended engagements vs. assessment

Open scenarios resist objective grading. **Answer:** assessment is mindset, not outcome. A student who solved a box brilliantly with bad opsec failed the lesson. A student who didn't solve the box but showed clear adversarial reasoning learned the lesson. Mindset assessment via conversation (feature 5) is how we measure this. Pass/fail on whether the box popped is irrelevant.

### Tension 3: All ages + offline-first + Pi 5 hardware

Kids on Chromebooks aren't running our Pi image. **Answer:** we accept that the *deepest* ERR0RS experience requires hardware (Pi 5 or laptop). EXPLORE tier could eventually have a hosted, sandboxed web version with reduced features for accessibility. But we never compromise the LEARN/OPERATE experience to fit a Chromebook — those tiers demand the full local stack. The mission isn't "every student gets ERR0RS-Lite for free." It's "every student who can borrow/afford/scrounge a $40 Pi or use an old laptop gets a teacher better than money can buy."

### Tension 4: Building it solo

This document describes years of work. One person can't build it. **Answer:** the call-for-contributors in the README is not decoration — it is the mechanism. Every feature above is decomposable into contributor-scale chunks. The teach pipeline (cards + RAG + merge tool) proved we can scale content via LLM-assisted authorship; the architecture above does the same for curriculum, scenarios, and assessment. Solo started this. Solo doesn't finish it.

### Tension 5: Speed vs. depth on Pi 5

**Just-measured baseline** (`docs/BENCHMARKS/2026-05-20-164838_clean-baseline/`):
- gemma3:1b small prompt (chunked): 34s TTFT — interactive
- gemma3:1b medium prompt: 76s TTFT — borderline
- gemma3:1b large prompt (full card): all runs failed

**Implication:** v3.7 chunked RAG is not optional. It's required. Without it, ERR0RS is unreliable on Pi 5 even with the best local model. The architecture above assumes chunked retrieval is the runtime baseline.

---

## Part VI — The roadmap

| Release | Theme | What ships |
|---|---|---|
| **v3.6.0** (shipped) | Teach Knowledge Drop | 67 fully-taught tools, RAG online, merge pipeline |
| **v3.7.0** (in progress) | Make the Pi Actually Teach | gemma3:1b default, chunked RAG, online toggle |
| **v3.8.0** | Dual-Perspective Teach | `defender_view` field on every teach card; LLM-generated paired content; "blue team mode" toggle in UI |
| **v3.9.0** | Metacognition | "Why did you do that?" probing wired to event bus; tracks student answer patterns; metacog response capture (groundwork for journal in v4.2.5) |
| **v4.0.0** | Adversarial Engagements | Scenario library, red/blue role-play mode, structured engagement wrapper |
| **v4.1.0** | Threat Actor Narratives | MITRE Group cross-references; APT framing in teach cards; real-world consequence storytelling |
| **v4.2.0** | Mindset Assessment | Conversation-based eval rubric; portfolio writes; student growth tracking |
| **v4.2.5** | Reflection Journal | SQLite-backed local journal; rotating reflection prompts hooked to engagement-end and teach-session-end; retrospective query mode. Compounds the prior 5 mindset features into long-term skill data. Lives at `~/.err0rs/journal/`, never leaves the device. |
| **v4.3.0** | EXPLORE Tier | Story-driven concept narratives for kids/beginners; safe simulated tooling |
| **v4.5.0** | LEARN Tier consolidation | Guided lab integrations (Juice Shop, DVWA, HTB starter boxes); capability gating; legal-foundations gateway |
| **v5.0.0** | OPERATE Tier consolidation | Full engagement framework; scoped-freedom mode; lab provisioning |
| **v∞** | The Mission | Free, local, private, excellent. For every curious mind on earth. |

---

## Part VII — How to start

For any contributor reading this and wondering where to begin:

**If you have an afternoon:** read `docs/STRESS_TESTS/FINDINGS_2026-05-20.md` and `docs/v3.7_PLAN_2026-05-20.md`. The fastest path to user value is finishing v3.7. Pick a Phase 1/2/3 item and ship it.

**If you have a week:** prototype the `defender_view` field. Take five teach cards, write the blue-team perspective for each by hand at the same depth as the existing red-team content, schema-validate, and propose the format. This is v3.8 unblocking work.

**If you have technical research instincts:** look at the Hailo-10H integration. v3.9.0+ all benefit from faster inference. The performance ceiling is the platform ceiling.

**If you write well and think well about pedagogy:** start drafting scenario YAML. What does a "you just got shell on a workstation" engagement look like as a structured exercise? Pick one TTP from the 67 cards and build the full engagement around it.

**If you care about kids and beginners:** the EXPLORE tier is the most green-field part of this whole document. We have *zero* content for it today. A single excellent "how does HTTP work, from both sides of the wire" walkthrough is more valuable than another 50 teach cards in LEARN/OPERATE right now.

**If none of those fit:** open an issue. Tell us who you are. We'll find where you fit.

---

## Closing

This document is a promise to a specific person: **the kid who has nothing but curiosity and a borrowed laptop, and wants to learn cybersecurity well enough to one day work in it, defend things that matter, or just understand how the world works.**

Every commit in this repo should be evaluated against that promise. *Does this make ERR0RS more useful to that person? Less? Neutral?* If the answer isn't "more," we're working on the wrong thing.

This is not a slogan. It's the constraint.

*"We learn from our errors. The name isn't ironic. It's a statement of belief. We learn from each other's errors too — and we make sure that the price of learning isn't paid in dollars or access."*

— ERR0RS Academic Architecture, v1
