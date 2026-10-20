# Speaker notes: demand-planning customer story

Companion to the 10-slide deck at `/story` (press `→` to advance, `E` to edit text). The deck is deliberately light on words. **You** carry the story; the slides carry the pictures and numbers.

> Every number below is **illustrative**. Replace the scenario, the numbers and the vocabulary with what the hiring manager gives you and what the panel confirms in discovery. Never present these as customer results.

## The one-sentence story

> Your planners spend part of every week assembling data instead of using it. If we connect those signals once, on a governed foundation, they get that time back and make better stock decisions. Let's prove it in six weeks on one slice.

## Time plan (60 minutes)

| Block | Minutes | Slides | Goal |
| --- | --- | --- | --- |
| Discovery validation | 10 | 1–2 | Listen, confirm the problem, earn the right to pitch |
| Problem, objectives, today | 8 | 3–5 | Agree on the pain and what must move |
| Value | 4 | 6 | Make the business case, with honest assumptions |
| Future state and demo | 11 | 7–8 | Show the art of the possible |
| Path and ask | 5 | 9–10 | Make the next step obvious |
| Buffer / interruptions | ~5 | | Panel questions will eat time. That is fine |
| Debrief (role-play ends) | 15 | | Explain approach, tools, trade-offs |

**Clock rule:** if you are behind at minute 30, skip slide 7's detail and go straight to the demo. The demo and the ask matter more than the architecture.

---

## Slide 1: Cover (about 1 min)

**Goal:** set the frame and the tone. Do not read the slide.

**Say:**
"Thanks for making the time. I'd like to spend the first ten minutes listening, because I'd rather solve your problem than present mine. After that I'll show you what's possible and propose a small first step."

**Point to:** the picture. "Many signals today, one trusted view of what's coming."

**Transition:** "So, before I show anything, let me check what I think I've heard."

---

## Slide 2: Listen first, discovery validation (about 10 min)

**Goal:** confirm the problem, baseline, stakeholders and constraints. This is the most important slide of the hour.

**Say:**
"I have four questions. I'll ask them in plain language and I'd love corrections: if I'm wrong, that's useful."

| Question | What you are really probing | Follow-ups |
| --- | --- | --- |
| **Where does the week go?** (Business) | Time lost to reconciling vs deciding | "Roughly how many hours per planner, per week?" "Who feels that most?" |
| **What does a miss cost?** (Business) | Value of better forecasts: stockouts, markdowns, rush freight | "Last quarter, what did one bad call cost?" "Which category hurts most?" |
| **Who owns the number?** (Data) | Trust, definitions, accountability | "If two teams show two numbers, who decides?" "Where does the number come from today?" |
| **What must not change?** (IT / Architecture) | Constraints: ERP, security, skills, cloud | "Which systems are untouchable?" "Who approves new tools?" |

**Capture during the conversation:**
- Baseline hours per planner per week
- Cost of a miss (euro or percentage)
- Decision owner and sponsor
- Hard constraints (security, cloud, ERP)

**Tip:** if they give you different numbers than the deck, **use theirs**. Say: "Great, I'll use your number rather than mine." Edit the slide live (press `E`) if time allows.

**Transition:** "Thank you. Let me play back what I heard in numbers."

---

## Slide 3: The problem (about 2 min)

**Goal:** make the pain tangible with one number.

**Say:**
"What I'm hearing is that planners spend about three hours a week reconciling data. That's one slice of a 40-hour week, the three red squares. It sounds small. Across 12 planners and 48 weeks it is over 1,700 hours a year of skilled people copying and checking numbers instead of acting on them."

**Evidence to state honestly:** "This is the figure from our conversation / my starting hypothesis. We'll replace it with a measured baseline in week one."

**If challenged ("it's not three hours"):** "Perfect, that is exactly what the baseline is for. If it's two hours, the value is lower but the case may still hold. Let's see on the next slides."

**Transition:** "So what do we need to change?"

---

## Slide 4: Objectives (about 3 min)

**Goal:** tie the work to measurable business objectives (OKRs).

**Say:**
"Three objectives, each with one number. First, a forecast you can trust: error from 17 percent to 10. Second, products on the shelf: about 10 percent fewer stockout days. Third, time to decide: from three hours of reconciliation to under one. These are illustrative targets. I'd like to set them together with you today or at the baseline workshop."

**Persona lens:**
- **Business leader:** talk about availability and margin.
- **Head of data:** talk about trust in one number.
- **IT / architecture:** point at "time to decide" as a reduction in manual handoffs.

**Ask:** "Which of these three is closest to your current priorities? Is there an objective I'm missing?"

**Transition:** "Let me show where we're starting from."

---

## Slide 5: Today (about 3 min)

**Goal:** show the current state in a way that feels familiar, even a bit funny, and make the pain points concrete.

**Say:**
"Today, four sources arrive at four different speeds: nightly from the ERP, hourly from the tills, manually for promotions, weekly for warehouse stock. Everything lands in spreadsheets. You'll recognise the file names. Then a weekly meeting where people debate whose numbers are right, and only then an order decision. That's about three days old by then."

**Walk the three numbered pins:**
1. "Four definitions of demand": each source has its own view.
2. "Copy-paste, version chaos": the file called `FINAL (2)`.
3. "Stale before it is used": the data is three days late when the decision is made.

**Ask:** "Is this broadly right? What did I get wrong?" (Listen. Correct the slide verbally.)

**Transition:** "What would it be worth to fix this?"

---

## Slide 6: Value (about 4 min)

**Goal:** a transparent, defensible business case. Show the calculation; do not hide it.

**Say:**
"A simple calculation: 12 planners, three hours a week, 48 weeks, at 45 euros an hour. That's 77,760 euros of capacity a year. Capacity, not cash: it only becomes savings if that time is redeployed or if we avoid hiring. If planners only save two hours, it's about 52 thousand. If four, about 104 thousand. That range is more honest than one number."

**Then:** "The two dashed boxes are the bigger prizes, fewer stockouts and less overstock. I haven't sized them because that needs your data, and I won't guess in front of you."

**Handle the CFO / business leader:**
- "Is that real money?" → "No, it's time freed. The real money is in stockouts and overstock, which we size together in the pilot."
- "Where's the payback?" → "We'll know after the pilot. The baseline gives us the before; the pilot gives us the after."

**Never say:** "This will save you 78K." Say: "This is the size of the prize if the time is redeployed."

**Transition:** "How would that work technically, in terms you can explain to colleagues?"

---

## Slide 7: Future state (about 3 min, skip detail if short on time)

**Goal:** one picture that works for business and technical people. Business message first, product names second.

**Say (business version):**
"Left to right: all your signals, connected once, brought together on a governed foundation, and then used by planners in the tools they like. Underneath the lines at the bottom you can see the outcomes: every signal, connected once, trusted and governed, used by planners."

**Say (technical version, only if asked):**
"Data lands in the Lakehouse in layers: raw (bronze), cleaned (silver) and planning-ready (gold). Forecasting models and quality checks run on the same platform. Unity Catalog gives one place for access control, lineage and audit. People consume it through an app, natural-language questions with Genie, or dashboards."

**Persona lens:**
| Persona | What they will ask | Answer |
| --- | --- | --- |
| **Head of IT** | "Is it secure? Who controls cost?" | One governance layer for access and audit; usage and cost visibility; identity from your existing provider. Confirm the specifics in the pilot. |
| **Enterprise architect** | "Does this replace our ERP?" | No. Source systems stay authoritative. The platform brings the data together and returns insight. |
| **Head of data** | "How do we trust the numbers?" | Quality checks between layers, lineage back to source, and one definition in the gold layer. |
| **Anyone** | "Are we locked in?" | Data is stored in open formats (Delta Lake) in your cloud storage. Confirm the details against their context. |

**Do not** list products. Name one or two only if someone asks.

**Transition:** "Let me show you what planners would actually see."

---

## Slide 8: Demo (about 7 min)

**Goal:** show the art of the possible. The prototype is a prop. Keep to three moves.

**Before you click:** state the story, not the tool. "A planner opens one screen instead of four spreadsheets."

**Click the button** (opens `/`, the demand-planning dashboard) and then:
1. **See demand:** pick a market and category. "Every number on this screen comes from one place."
2. **Compare forecasts:** show current vs improved forecast. "The line closer to actual demand is the improved forecast. Same data, better model." On the deployed app this is a trained model, scored only on days it never saw.
3. **Act:** use Export. "From here it goes to the order process."

**Optional fourth move, if the business persona is engaged (about 2 min):** open the Genie space and ask "How much does the model reduce forecast error during promotions?" Then let them ask one question of their own. "Your category managers could ask this themselves, without waiting for a report." Rehearse the questions beforehand; skip this move if you are behind at minute 30.

**Say once, clearly:** "This is synthetic data. The improvement you see is illustrative, to show what's possible, not a result I'm promising."

**If the demo breaks:** go back to the slide chart. "This is the same picture. The point isn't the screen, it's the decision it enables." Move on. Do not debug live.

**Ask while on the demo:** "If your planners had this on Monday morning, what would they do differently?"

**Transition:** "Let me suggest how to find out if this works for you, without a big commitment."

---

## Slide 9: The path, six-week pilot (about 3 min)

**Goal:** make the first step small, time-boxed and measurable.

**Say:**
"I would not start with a platform programme. I'd start with one slice: one region, one category, six weeks. Weeks one and two: baseline, measure today's accuracy and hours. Weeks three and four: build a thin slice end to end. Weeks five and six: planners use it live, and we compare against the baseline. At the end there's a go or no-go decision, and we measure three things: forecast error against baseline, planner hours spent reconciling, stockout days in scope."

**Key phrase:** "If the numbers don't move, we stop, and you've spent six weeks, not six months."

**Handle risk questions:**
- "Who needs to be involved?" → sponsor, 2–3 planners, a data owner, someone from IT for access.
- "What do you need from us?" → read access to sample data and a named data owner. Specifics to be agreed.
- "What if the data's messy?" → "Almost always, and that's useful: the baseline tells us how messy before we commit."

**Transition:** "So what do I need from you today?"

---

## Slide 10: Today's ask (about 3 min)

**Goal:** a clear, small call to action. Make "yes" the obvious next step.

**Say:**
"Three decisions to start. One: pick the slice, which region and category. Two: agree the scorecard, the baseline and the success measures. Three: name the owners, a business sponsor and a data owner. If we can settle those, the next step is a 90-minute baseline workshop this week."

**Close:** pause, then ask: "What would stop us from doing that?" Listen for the real objection, then address it.

**Do not** summarise the whole deck again. End on the ask.

---

## Interruptions and objections (quick answers)

| Interruption | Short answer |
| --- | --- |
| "How much will this cost?" | "Depends on scope and usage; the pilot is designed to be small. I'd rather size it with you after the baseline than quote a number blind." |
| "We already have a BI tool." | "Good. This isn't about replacing it. It's about feeding it, and the planners, with one trusted number." |
| "We tried a forecasting project before." | "What happened? (listen) That's helpful. The baseline and go/no-go gate are there precisely to avoid a long project with no proof." |
| "Our data isn't ready." | "Few people's are. Week one tells us exactly how far we are, with no commitment beyond that." |
| "Is the AI reliable?" | "It's measured against your actual demand and compared with today's method, with planners staying in control of the decision." If they push: every forecast in the demo is out-of-sample, tracked in MLflow, and the model version is registered in Unity Catalog, so you can see which model produced which number. |
| "Will Genie make up numbers?" | "It writes SQL on the governed table and shows it. The definition of forecast error is set once, so it answers the same way every time." |
| "Can't we build it ourselves?" | "Of course you can build parts. The question is how fast you get a trusted number and who maintains it. Let's compare in the pilot." |
| Anyone goes deep technical | "Great question. Let me note it and we'll go through it properly with the architects. I want to make sure the business case lands first." |

## Debrief (final 15 minutes, role-play ends)

Be ready to explain:
- **Why this story:** the problem came first, the technology followed.
- **How you built it:** which tools and AI assistants you used, what you accepted and what you corrected.
- **What you'd do next with more time:** a real baseline, sized stockout/overstock value, per-series models at customer scale, a scheduled retrain job, governance walkthrough.
- **How the model is evaluated:** expanding-window backtest, WAPE against the current method on the same days, MLflow run plus a Unity Catalog model with a `champion` alias.
- **What you chose not to show:** architecture detail, product list. Explain it was to keep the story customer-led.
- **What was illustrative:** all numbers on slides 3, 4 and 6 and the data in the demo.

## Pre-session checklist

- [ ] Hiring manager has confirmed vertical and scenario; deck text updated to match (press `E`, then **Save edits** or **Download HTML**)
- [ ] Illustrative numbers replaced or clearly labelled
- [ ] Demo app runs locally (`/`) and the `/story` page loads, with a screenshot fallback ready
- [ ] If showing the workspace: both notebooks ran, the MLflow run and registered model open, and the Genie space answers the rehearsed questions
- [ ] Notes for each persona on one page
- [ ] Browser zoom reset; deck in full-screen (`F11`/`Ctrl+Cmd+F`); notifications off
- [ ] A watch or timer visible; check at minute 10, 30 and 45
