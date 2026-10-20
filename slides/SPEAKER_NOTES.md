# Speaker notes: Grocery Inventory Copilot

Companion to the 5-slide deck at `/story` (press `→` to advance, `E` to edit text) and the live copilot at `/`. The slides carry pictures and numbers. **You** carry the story.

> **Groenhof Markets is fictional** and every number is illustrative or synthetic. Say so once, early: "I've made some assumptions to move fast. Please correct me, because your numbers beat mine." After that, use *their* numbers wherever they give you one.

## The one-sentence story

> On the same Saturday you run out of strawberries in Amsterdam and throw them away in Utrecht, because sales, stock and supplier news sit in four systems nobody joins. Connect them once, predict the gaps, let a copilot explain them from your own supplier knowledge, and your teams decide in five minutes instead of debating for weeks. Let's prove it on fresh produce in one region in 30 days.

## Customer and cast (assumptions to validate)

- **Groenhof Markets**: mid-sized Dutch grocery chain, about 110 stores, about €1.2B revenue, about €400M of it fresh.
- **Pain**: fresh waste around 3.5% of fresh sales (about €14M a year), Saturday on-shelf availability around 92% on fresh, and every Monday meeting starts with "whose number is right?".
- **Systems**: Postgres (POS and promotions), MySQL (store stock), a supplier portal (SaaS, CSV export), and years of supplier agreements, grower updates and incident notes in documents and email.
- **Panel personas**: Business leader (COO or Commercial Director), CDO or Head of Data, VP Engineering.

## Run of show (60 minutes)

| Block | Min | What | Goal |
| --- | --- | --- | --- |
| Set-up and discovery | 10 | No slides, then slide 1 | Confirm the pain, the numbers, the owners and the constraints |
| Architecture | 4 | Slide 2 | "One platform, four layers", in business words |
| Live demo | 12 | Slide 3, then the app | One morning, one decision |
| Value | 4 | Slide 4 | €4M per point of waste, measured against *their* baseline |
| Next steps | 4 | Slide 5 | Get the "go" for 30 days |
| Buffer for questions | ~6 | | Interruptions are the point. Welcome them |
| Debrief (role-play ends) | 15 | | Approach, tools, trade-offs, what you'd do differently |

**Clock rules:** at minute 25 you must be in the demo. If you're behind, skip the "How the data is governed" panel and offer it to the CDO afterwards. Never skip slide 5.

---

## 1. Discovery (10 min, start without slides)

Open: "Thanks for the time. Before I show anything, I want to check I've understood the problem. I'll ask four questions. If I'm wrong, that's the most useful thing that can happen today."

| # | Ask | Who answers | Listen for | Write down |
| --- | --- | --- | --- | --- |
| 1 | "When a store runs out of strawberries on a Saturday, how do you find out, and how long after?" | Business | Monday reports, complaints, no early warning | Hours or days of delay |
| 2 | "What does fresh waste cost you a year, and which categories hurt most?" | Business | € or % of fresh sales; bakery, produce, meat | Their waste % and € |
| 3 | "If commercial and supply chain show different numbers, who decides which one is right?" | CDO | No owner, spreadsheet merges, definitions | Owner and number of sources |
| 4 | "What must not change: systems, security rules, cloud, team skills?" | VP Eng | Cloud provider, SAP or ERP, team size, security reviews | Hard constraints |

Bonus question if there's time: "When a supplier warns you about a short harvest, where does that information go?" (It's usually an email to one buyer. That sets up the copilot.)

Then show **slide 1** and say: "This is what I heard from your team before today. Which of these numbers is wrong?" If they correct a number, press `E` and change it live. That's the strongest listening signal you can give.

## 2. Slide 1: the problem (included in discovery)

- "Two stores, same product, same week: one empty shelf, one full bin. It isn't a people problem. Nobody can see both at once."
- Point to the third box: "Four systems, so every meeting starts by debating whose number is right."
- Business translation: waste is margin you've already paid for. An empty shelf is a customer who tries the competitor.

## 3. Slide 2: architecture (about 4 min)

Explain it **left to right in business words**, adding one technical noun per layer for the engineers:

1. **Governed data**: "We connect Postgres, MySQL and the supplier portal once, and join them on one thing everybody understands: a product in a store. Bad rows are quarantined, not silently dropped." *(Lakeflow Connect, Bronze/Silver/Gold, expectations.)*
2. **Predict**: "On top of that, a demand forecast per store and product, then two predictions people can act on: will this shelf go empty, and will this stock expire?" *(MLflow, Unity Catalog model registry, monitoring.)*
3. **Explain**: "The copilot reads your supplier agreements, grower updates and past incidents, together with the risk table, and cites its sources." *(Vector Search, Model Serving.)*
4. **Act**: "Store and category managers get ranked actions. Leaders can ask in plain English; the Genie space on the Gold tables is defined in the repo but not part of the live demo."

Then the line for the CDO: "Underneath all four sits one governance layer. One copy of the data, one place for permissions, and lineage, permissions and audit that we would configure with you in the pilot; the prototype does not enable them."

## 4. Live demo (about 12 min)

Show slide 3 for 20 seconds ("one morning, one decision, three moves"), then click **Open the live copilot**.

| Step | Click | Say | Persona hook |
| --- | --- | --- | --- |
| 1 | Point at the four layer cards at the top | "This is the slide you just saw, running. Four sources, one store × product view, 2 bad rows caught, 9 store codes fixed." | CDO: trust |
| 2 | The risk list | "It's 05:30 on Tuesday. Instead of a 40-tab report, there are eight things worth doing today, sorted by euros at risk." | Business |
| 3 | Top row: Amsterdam strawberries | "Thursday, the second day of the 2+1 promotion, Amsterdam runs out." | Business |
| 4 | The chart | "Grey is forecast demand, green is what the supplier actually confirmed, the line is stock. It goes below zero on Thursday." | All |
| 5 | **Why this is happening** | "This didn't come from a model. It came from a grower update in someone's inbox: rain in Zeeland, 70% of orders confirmed. The copilot found it and cited it." | Business: wow moment |
| 6 | **Recommended actions** | "Utrecht has 80 punnets it can't sell before they expire. Move them on tomorrow's 06:00 van. Top up the rest from the approved alternative supplier. Cap the promotion. Each action cites the policy that allows it." Tick the first box. | Business: decision |
| 7 | Click **Happened before?** | "We've seen this before: week 31 cost about €4,200 in Amsterdam. The organisation learns from its own history." | Business: learning loop |
| 8 | Click Utrecht strawberries in the list | "Same transfer, seen from the other side: waste becomes sales." | Business |
| 9 | Open **How the data is governed** | "For the data team: this is the pilot design. Unity Catalog lineage, row filters and masks are what we would configure with you; they are not switched on in this prototype." | CDO |
| 10 | Optional: the **Forecast accuracy** tab | "Measured, not claimed: 10% error versus 21% with 'same as last week', on days the model never saw. In the pilot we measure on *your* history." | CDO / VP Eng |

Close the demo: "Data in, prediction, explanation, action, in one flow, in five minutes. Today that takes your team a week and three spreadsheets."

**Be honest about what's mocked:** data is synthetic. Locally the copilot assembles answers from retrieved passages, so every sentence has a source. On Databricks the same retrieved context goes to a governed LLM endpoint. Say it before someone asks.

## 5. Slide 4: value (about 4 min)

- "If fresh sales are about €400M (an assumption to validate), one point less waste is about €4M a year at cost. That's before availability, which usually matters more to you, because an empty shelf loses the whole basket, not one punnet."
- Show the formula, don't defend it: "These are my assumptions. Yours will be different, and the pilot's first job is to measure your baseline."
- Three KPIs for the scorecard: waste % of fresh sales, Saturday on-shelf availability, time from signal to decision.

## 6. Slide 5: first 30 days and the ask (about 4 min)

| Week | What happens | Who from Groenhof | Exit criterion |
| --- | --- | --- | --- |
| 1 · Connect | Lakeflow Connect to Postgres and MySQL (read replica), portal export into a volume, Unity Catalog set up with IT's access rules | DBA, security, 1 data engineer | Bronze and Silver refreshed daily for one region |
| 2 · Baseline | Measure today's waste, availability and forecast error the same way for everyone. Train and backtest the forecast on real history | Fresh category manager, finance | Baseline signed off by finance |
| 3 · Shadow | Risk list and copilot run next to planners in ~20 stores. Planners still decide; we log what they would have changed | 5 category managers, 20 store managers | Usage and feedback, top 3 wrong recommendations understood |
| 4 · Decide | Scorecard against the baseline, cost of running, go / adjust / stop | Sponsor | A decision, either way |

**The ask:** a sponsor plus one fresh category manager, read access to two databases and the portal, and agreement on the scorecard. "If it doesn't move the numbers in 30 days on fresh produce, you'll know for very little money. If it does, the next step is all categories, then the rest of the chain."

Closing line: "Can we agree today on the region and the sponsor, so the baseline workshop is next week?"

---

## Persona map

| Persona | Cares about | Lead with | Show | Avoid |
| --- | --- | --- | --- | --- |
| Business leader (COO, Commercial Director) | Margin, availability, speed, customer trust | Euros at risk, the strawberry story | Risk list, cited actions | Model names, architecture detail |
| CDO / Head of Data | One version of the truth, quality, ownership, compliance | "One copy, one set of permissions, lineage" | Quarantine counts, governance panel, Unity Catalog | Promising accuracy before seeing their data |
| VP / Director of Engineering | Complexity, run cost, skills, lock-in, security | Open formats, managed services, small team | Notebook, `app.yaml`, the 30-day plan | Hand-waving on effort |

## Objection handling (answer in under 30 seconds, then check: "Does that answer it?")

| Objection | Answer |
| --- | --- |
| **"What does this cost?"** (Business) | "For the pilot, a small team and consumption-based compute on one region. Single-digit thousands of euros of platform spend a month is a realistic starting range to validate with your account team. You pay for what runs, and the forecast runs once a night. Compare that with €4M per point of waste. We'll put the real cost in the week-4 scorecard so you decide on facts." |
| **"We tried a forecasting tool. Planners ignored it."** | "That's why week 3 is shadow mode with planners, and why every recommendation says *why* and cites the source. People trust what they can check." |
| **"Can we trust the data?"** (CDO) | "Bad rows are quarantined and counted, not hidden: you saw 2 caught today. Lineage back to source rows is part of the pilot design, and finance signs off the baseline in week 2 before anyone acts on it." |
| **"LLMs hallucinate."** | "The copilot only answers from retrieved passages and the risk table, and cites both. When it can't find an answer, it says so. Numbers come from the model and the data, never from the LLM. In week 3 a person decides on every action, and we log answers to review them." |
| **"Our supplier contracts are confidential."** (CDO, security) | "In the pilot design, documents stay in your cloud account under Unity Catalog permissions, cost columns can be masked for store roles, and model calls go to an endpoint inside the workspace. I would confirm the data-use and logging terms with your security team rather than promise them today. Approve in the demo is simulated; it sends nothing to stores or suppliers." |
| **"This sounds complex. We have three data engineers."** (VP Eng) | "That's why it's one platform instead of five tools: managed connectors, managed model serving, managed vector search. The pilot is one notebook, one app and one job. What you're seeing was built in an afternoon on synthetic data." |
| **"We already have Snowflake / Fabric / an SAP planning tool."** | "Keep what works. The question is where the forecast, the documents and the AI meet under one set of permissions. Databricks reads and writes open formats (Delta, Iceberg), so it can sit next to what you have. Specialist replenishment tools are strong at ordering, but they don't read your grower emails." |
| **"Why not just build this in Excel or Power BI?"** | "Power BI is a great front end and can sit on Gold. What it can't do is train and monitor a model, search documents and govern both. That's the gap." |
| **"What if the forecast is wrong?"** | "It will be, sometimes. That's why we show a probability, not a promise, and why we measure error every night against your current method. If it drifts, monitoring flags it and we retrain." |
| **"How long until all 110 stores?"** | "Honestly, it depends on what week 4 shows. Typically: one region in 30 days, all fresh categories in a quarter, then the rest. Each step only goes ahead if it pays for itself." |

## If something breaks

- **App won't load:** use the screenshots in `slides/` (take them in your gut-check) and keep talking. The story doesn't need the app.
- **A question you can't answer:** "Good question. I don't want to guess. Let me come back to you with the exact answer by tomorrow." Write it down where they can see.
- **Running late:** go straight from the demo to slide 5.

## Debrief (15 min, role-play ends)

- **Approach:** started from the business decision ("what should a store manager do at 05:30?") and worked back to the data, not the other way round.
- **Build:** Flask app with a deterministic engine (`app/demos/grocery/engine.py`) shared with the Databricks notebook, so local and lakehouse show the same numbers. A simple, explainable forecaster on purpose, because the story needed trust more than a few points of accuracy. A gradient-boosted model is the obvious next step (`notebooks/demand_forecast_model.py` shows the pattern).
- **Trade-offs:** synthetic data; offline copilot composer instead of a live LLM, for reliability in the room; scripted scenarios so the story is the same every run.
- **What I'd do next:** real backtests on customer data, Lakehouse Monitoring on the forecast, an evaluation set for copilot answers (MLflow evaluation), and a Genie space on the Gold tables.

## 30-minute gut check

- [ ] `python -m app.main`, then open `/` and `/story`. Click through all 5 slides and the demo path once.
- [ ] Ask the four suggestion buttons once each.
- [ ] Save screenshots of the copilot, the strawberry briefing and each slide as an offline fallback.
- [ ] Say the one-sentence story out loud without notes.
- [ ] Have your answers ready for cost, hallucinations and "we already have X".
