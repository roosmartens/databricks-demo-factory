# Speaker notes: Grocery Inventory Copilot

Companion to the 5-slide deck at `/story` (press `→` to advance, `E` to edit text) and the live copilot at `/`. The slides carry pictures and numbers. **You** carry the story.

> **Groenhof Markets is fictional** and every number is illustrative or synthetic. Say so once, early: "I've made some assumptions to move fast. Please correct me, because your numbers beat mine." After that, use *their* numbers wherever they give you one.

## The one-sentence story

> On the same Saturday you run out of strawberries in Amsterdam and throw them away in Utrecht, because sales, stock and supplier news sit in four systems nobody joins. Connect them once, predict the gaps, let a copilot explain them from your own supplier knowledge, and your teams decide in five minutes instead of debating for weeks. Let's prove it on fresh produce in one region in 30 days.


## Who the app is for, and how its features divide the work

The app is designed so you don't have to explain this; say it once in your own words when you open it.

- **Fresh planner** (category manager), 05:30, before supplier orders close at 12:00: works the list of today's decisions top to bottom. The heading says it: "Good morning. 8 shelves need a decision today."
- **Store manager**: receives the hand-over ("Draft message to the store") and moves the stock.
- **Planning manager**: reads the four numbers at the top (value at risk, run-outs, waste risks, forecast error) and asks Genie for anything else.

| Feature | Its one job | Answers from |
| --- | --- | --- |
| The list, chart and **Do this** | What will run out or go to waste, and what to do | Forecast and rules on the Gold tables. No LLM |
| **Draft message to the store** (the AI briefing) | Turn the decision into a hand-over a store manager can act on | The risk row plus the cited passages |
| **Ask the copilot** | Follow-ups the numbers can't answer: other supplier, substitutes, what happened last time | Supplier documents only. Says so when they don't cover it |
| **Ask Genie** | Any other number, across stores and weeks | The same Gold tables, as SQL you can inspect. The copilot hands numbers questions to Genie |

**Why not just Genie?** The reason Amsterdam runs out is not in a table. It's in a grower email about rain in Zeeland and a contract that names Huelva as the approved backup with a 20-case minimum. The copilot reads those; Genie does the numbers.

**Be honest about what is running:** without a model endpoint (`COPILOT_SERVING_ENDPOINT`) the draft is a labelled template and Ask quotes the documents. Retrieval is keyword search over 23 passages with a small synonym list; in the pilot it's Vector Search. Set `GENIE_SPACE_URL` before the demo so the **Ask Genie** tile appears.

**How the AI gets better (if asked "and in six months?"):** real grower emails land automatically and are searched with embeddings; 50 questions graded by category managers run through MLflow evaluation on every change; the 👍/👎 on each answer is logged and the thumbs-down answers become test questions; citation and number checks and Unity Catalog permissions stay on.

## Customer and cast (assumptions to validate)

- **Groenhof Markets**: mid-sized Dutch grocery chain, about 110 stores, about €1.2B revenue, about €400M of it fresh.
- **Pain**: fresh waste around 3.5% of fresh sales (about €14M a year), Saturday on-shelf availability around 92% on fresh, and every Monday meeting starts with "whose number is right?".
- **Systems**: Postgres (POS and promotions), MySQL (store stock), a supplier portal (SaaS, CSV export), and years of supplier agreements, grower updates and incident notes in documents and email.
- **Panel personas**: Business leader (COO or Commercial Director), CDO or Head of Data, VP Engineering.


## Run of show (60 minutes)

| Block | Min | What | Goal |
| --- | --- | --- | --- |
| Discovery | 10 | No slides, then slide 1 | Confirm the pain, the numbers, the owners and the constraints |
| The art of the possible | 14 | Slide 2, then the live app | One of their problems, solved end to end: who uses it, how |
| Behind the solution | 4 | Slide 3 | "What you just saw: four connected layers" |
| Value and future state | 5 | Slide 4 | €4M per point of waste, then the same platform for the whole chain |
| Next steps | 4 | Slide 5 | Get the "go" for 30 days |
| Buffer for questions | ~8 | | Interruptions are the point. Welcome them |
| Debrief (role-play ends) | 15 | | Approach, tools, trade-offs, what you'd do differently |

**Clock rules:** at minute 12 you must be on slide 2. If you're behind, skip **Where the numbers come from** in the app and offer it to the CDO afterwards. Never skip slide 5.

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
- Each card carries the question that tests it. Ask them out loud, to the person named: **COO** on waste and on what an empty shelf costs, **CDO and Engineering** on whose number wins and who owns each system.
- Business translation: waste is margin you've already paid for. An empty shelf is a customer who tries the competitor.
- Bridge to slide 2: "There are several problems in here. Let me show you one of them solved end to end: fresh planning."

## 3. Slide 2 and the live demo: the art of the possible (about 14 min)

On slide 2, 30 seconds: "This is for three people. The fresh planner decides by 05:30. The store manager gets the hand-over. The planning manager sees the whole week. One morning, three moves." Then click **Open the live copilot**.

| Step | Click | Say | Persona hook |
| --- | --- | --- | --- |
| 1 | The heading and the four numbers | "It's 05:30 on Tuesday. The planner opens one page: eight shelves need a decision, €1,326 at risk this week. The planning manager reads the same four numbers." | Business |
| 2 | Top of **Today's decisions**: Amsterdam strawberries | "Worst first. Amsterdam runs out on Thursday, the second day of the 2+1 promotion." | Business |
| 3 | The chart | "Grey is demand, green is what the supplier actually confirmed, the line is stock. Below zero is an empty shelf." | All |
| 4 | **Why** and its source chip | "This didn't come from a model. It came from a grower update in someone's inbox: rain in Zeeland, 70% confirmed. Hover the chip: there's the source." | Business: wow moment |
| 5 | **Do this**, then **Approve** on the transfer | "Utrecht has 80 punnets it can't sell in time. Move them on tomorrow's 06:00 van." Click Approve: the numbers at the top update and the green line says it's simulated. | Business: decision |
| 6 | **Draft message to the store** | "One click, and the store manager has the hand-over: what, why, what to do, what to watch. Here it's a template; with a model endpoint the model writes it and it's rejected if it invents a number." | Business, VP Eng |
| 7 | **Ask the copilot**: **Happened before?** | "Follow-ups go to the documents. Week 31: same story, about €4,200 lost. The organisation learns from its own history." Click 👍: "every vote is logged; the bad ones become test questions." | Business: learning loop |
| 8 | Type "How much waste per store this week?" | "It doesn't guess numbers. That's Genie's job, on the same governed tables." Click **Open in Genie** (or the **Ask Genie** tile). | CDO / VP Eng |
| 9 | Utrecht strawberries in the list, now **✓ Handled** | "Same transfer from the other side: waste becomes sales." | Business |
| 10 | Optional: **Where the numbers come from**, the **Forecast accuracy** tab | "Four sources, 2 bad rows quarantined, 9 store codes fixed. And measured, not claimed: 10% error versus 21% with 'same as last week', on days the model never saw." | CDO |

Close the demo: "One planner, one morning, five minutes. Today that takes your team a week and three spreadsheets."

**Be honest about what's mocked:** data is synthetic, Approve sends nothing, and without a model endpoint the draft is a labelled template. Say it before someone asks.

## 4. Slide 3: behind the solution (about 4 min)

"What you just saw is four connected layers." Point back at what they saw, left to right, one technical noun per layer for the engineers:

1. **Governed data**: "The four numbers and the list come from Postgres, MySQL and the supplier portal, joined once on a product in a store. Bad rows are quarantined, not dropped." *(Lakeflow Connect, Bronze/Silver/Gold, expectations.)*
2. **Predict**: "The chart is a demand forecast per store and product, turned into two questions people act on: will this shelf go empty, will this stock expire?" *(MLflow, Unity Catalog model registry, monitoring.)*
3. **Explain**: "The **Why**, the draft and the answers come from your supplier documents, cited." *(Vector Search, Model Serving.)*
4. **Act**: "Planners approve in the app. Managers ask Genie for any other number." *(Databricks Apps, Genie, AI/BI.)*

Then the line for the CDO: "Underneath sits one governance layer: one copy of the data, one place for permissions. Lineage, row filters and audit are what we'd configure with you in the pilot; the prototype doesn't enable them."

## 5. Slide 4: business value and future state (about 5 min)

- Left: "If fresh sales are about €400M (an assumption to validate), one point less waste is about €4M a year at cost. That's before availability, which usually matters more, because an empty shelf loses the whole basket."
- Right: "And this is the point for you as a company: none of this was built for strawberries. The same governed data and forecast answer the next problems." Pick the two that came up in discovery, for example promotions (the forecast already sees promo uplift) or supplier scorecards (the portal feed is already in, and Genie can answer it tomorrow).
- Bottom: "30 days on fresh in one region, a quarter for all fresh, a year for the chain. Each step goes ahead only if it pays for itself." For the CDO and engineering: "one copy of the data, one set of permissions, every use case on the same platform."
- Three KPIs for the scorecard: waste % of fresh sales, Saturday on-shelf availability, time from signal to decision.

## 6. Slide 5: next steps, the 30-day pilot (about 4 min)

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
| CDO / Head of Data | One version of the truth, quality, ownership, compliance | "One copy, one set of permissions, lineage" | Quarantine counts, "Where the numbers come from", Unity Catalog | Promising accuracy before seeing their data |
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
| **"Why not just use Genie for everything?"** | "Genie answers numbers questions on tables, and we use it for exactly that. But why Amsterdam runs out isn't in a table: it's in a grower email and a supplier contract. The copilot reads those, and the draft turns both into a hand-over for the store. Same Gold tables, same permissions underneath." |
| **"The answers aren't perfect."** | "Agreed, and here they come from keyword search over 23 passages. In the pilot: embeddings, real grower emails, and 50 questions your category managers grade, run through MLflow evaluation on every change. The 👍/👎 on each answer feeds that set." |
| **"Why not just build this in Excel or Power BI?"** | "Power BI is a great front end and can sit on Gold. What it can't do is train and monitor a model, search documents and govern both. That's the gap." |
| **"What if the forecast is wrong?"** | "It will be, sometimes. That's why we show a probability, not a promise, and why we measure error every night against your current method. If it drifts, monitoring flags it and we retrain." |
| **"How long until all 110 stores?"** | "Honestly, it depends on what week 4 shows. Typically: one region in 30 days, all fresh categories in a quarter, then the rest. Each step only goes ahead if it pays for itself." |

## If something breaks

- **App won't load:** use the screenshots in `slides/` (take them in your gut-check) and keep talking. The story doesn't need the app.
- **A question you can't answer:** "Good question. I don't want to guess. Let me come back to you with the exact answer by tomorrow." Write it down where they can see.
- **Running late:** skip slide 3 (offer it to the engineers afterwards), keep slide 4 to one minute, and never skip slide 5.

## Debrief (15 min, role-play ends)

- **Approach:** started from the business decision ("what should a store manager do at 05:30?") and worked back to the data, not the other way round.
- **Build:** Flask app with a deterministic engine (`app/demos/grocery/engine.py`) shared with the Databricks notebook, so local and lakehouse show the same numbers. A simple, explainable forecaster on purpose, because the story needed trust more than a few points of accuracy. A gradient-boosted model is the obvious next step (`notebooks/demand_forecast_model.py` shows the pattern).
- **Trade-offs:** synthetic data; offline copilot composer instead of a live LLM, for reliability in the room; scripted scenarios so the story is the same every run.
- **What I'd do next:** real backtests on customer data, Lakehouse Monitoring on the forecast, an evaluation set for copilot answers (MLflow evaluation), and a Genie space on the Gold tables.

## 30-minute gut check

- [ ] `python -m app.main`, then open `/` and `/story`. Click through all 5 slides and the demo path once.
- [ ] Ask the four suggestion buttons once each.
- [ ] Save screenshots of the copilot, the strawberry draft message and each slide as an offline fallback.
- [ ] Say the one-sentence story out loud without notes.
- [ ] Have your answers ready for cost, hallucinations and "we already have X".
