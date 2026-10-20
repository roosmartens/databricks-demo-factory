# Speaker notes: Grocery Inventory Copilot

Companion to the 5-slide deck at `/story` (press `→` to advance, `E` to edit text) and the live copilot at `/`. The slides carry pictures and numbers. **You** carry the story.

> **Groenhof Markets is fictional** and every number is illustrative or synthetic. Say so once, early: "I've made some assumptions to move fast. Please correct me, because your numbers beat mine." After that, use *their* numbers wherever they give you one.

## The one-sentence story

> On the same Saturday you run out of strawberries in Amsterdam and throw them away in Utrecht, because sales, stock and supplier news sit in separate systems nobody joins. Connect them once, predict the gaps, let a copilot explain them from your own supplier knowledge, and your teams decide in five minutes instead of debating for weeks. Let's prove it on fresh produce in one region in 30 days.

## Ask a lot of questions (the hiring manager asked for it)

The panel scores discovery and listening, not how much you say. Aim for **at least two questions per block**, and every question has a job: confirm an assumption, find the pain in euros, or move to a decision.

- **Ask before you show.** Every block below opens or closes with a check-in. They're marked **Ask**.
- **Name the person.** "[COO name], how does that land for you?" beats "Any questions?", which gets silence.
- **One question at a time**, then stop talking. Count to five in your head; silence is fine.
- **Use the answer straight away.** Correct a number on the slide (`E`), use their job title, pick the use case they named. That's the strongest listening signal.
- **Write answers down where they can see**, and play them back on slide 5: "You said X, so the pilot measures X."
- **When they ask you something, ask back first** if the question is vague: "Good question. What's behind it: cost, or how your team would run it?" Then answer the real question.
- **Open questions** (what, how, who, when) for discovery; **closed questions** ("Can we agree on...?") only to close.

**The ten questions to know by heart:**

1. "What would make this hour useful for you?" (opening, each persona)
2. "When a store runs out on a Saturday, how do you find out, and how long after?"
3. "What does fresh waste cost you, and which categories hurt most?"
4. "When two teams show different numbers, who decides which one is right?"
5. "How does a planner's morning look today, and how long does it take?"
6. "When a grower warns you about a short harvest, where does that information go?"
7. "What must not change: systems, security rules, cloud, skills?"
8. "If this worked, what would you see differently in six months? Which target does it move?"
9. "What would make you say no at day 30?"
10. "Who else needs to be involved to say go, and how do decisions like this get made here?"


## Who the app is for, and how its features divide the work

The app is designed so you don't have to explain this; say it once in your own words when you open it.

- **Fresh planner** (category manager), 05:30, before supplier orders close at 12:00: works the list of today's decisions top to bottom. The heading says it: "Good morning. 8 shelves need a decision today."
- **Store manager**: receives the hand-over ("Draft message to the store") and moves the stock.
- **Planning manager**: reads the four numbers at the top (value at risk, run-outs, waste risks, forecast error) and asks Genie for anything else.

So the app is *for* three people but *used* by two: the planner works in it every morning, the planning manager opens it for the overview and Genie. The store manager never needs to open it; they get the hand-over message.

| Feature | Its one job | Answers from |
| --- | --- | --- |
| The list, chart and **Do this** | What will run out or go to waste, and what to do | Forecast and rules on the Gold tables. No LLM |
| **Draft message to the store** (the AI briefing) | Turn the decision into a hand-over a store manager can act on | The risk row plus the cited passages |
| **Ask the copilot** | Follow-ups the numbers can't answer: other supplier, substitutes, what happened last time | Supplier documents only. Says so when they don't cover it |
| **Ask Genie** | Any other number, across stores and weeks | The same Gold tables, as SQL you can inspect. The copilot hands numbers questions to Genie |

**Why not just Genie?** The reason Amsterdam runs out is not in a table. It's in a grower email about rain in Zeeland and a contract that names Huelva (the Spanish strawberry region; the backup is Huelva Berry Cooperative) as the approved backup with a 20-case minimum. The copilot reads those; Genie does the numbers.

**Be honest about what is running:** without a model endpoint (`COPILOT_SERVING_ENDPOINT`) the draft is a labelled template and Ask quotes the documents. Retrieval is keyword search over 23 passages with a small synonym list; in the pilot it's Vector Search. Set `GENIE_SPACE_URL` before the demo so the **Ask Genie** tile appears.

**How the AI gets better (if asked "and in six months?"):** see **How it learns from what happens** below.

## Reading the decision line (demo step 2)

Under the Amsterdam headline: **over 95% likely to run out · 0.7 days of cover · promotion 4 of 7 days · supplier confirmed 70%**. Four facts from three systems, in one line. Only shown for items that will run out.

| Piece | Means | Calculated as | From |
| --- | --- | --- | --- |
| over 95% likely to run out | Chance the shelf goes empty some day this week | Each day: forecast demand so far vs stock plus confirmed deliveries, with an error band from the forecast's past accuracy that widens further out. Highest day wins; ≥ 95% shows as "over 95%" | Forecast, stock, supplier portal |
| 0.7 days of cover | Today's stock lasts less than a day | Stock on hand ÷ average forecast daily sales this week (the promotion pushes it down from ~0.9) | Store stock, forecast |
| promotion 4 of 7 days | The 2+1 runs Thursday to Sunday | Counted from the promo calendar; promo days get ~1.6× demand for fresh produce | Promo calendar |
| supplier confirmed 70% | The grower confirmed 70% of what was ordered | Confirmed ÷ ordered for the next delivery; only shown below 100% | Supplier portal |

**Say:** "Almost certain to run out: less than a day of stock, a promotion pushing demand up for four days, and the grower only confirmed 70%. Three systems, one line."

## Ask the copilot: why it's in the demo

It is the visible proof of the prompt's GenAI layer: *"years of accumulated documents … that nobody can actually use."* The risk list says *what* and *what to do*; Ask answers the follow-ups that live in documents, not tables:

- "Is there another supplier?" → the backup clause in the contract
- "What can I put on the shelf instead?" → the substitution playbook
- "Has this happened before?" → week 31: same story, about €4,200 lost. **Your strongest moment for the business leader**: the organisation learns from its own history instead of one buyer's inbox

For the CDO: it answers only from the documents, cites them, says so when they don't cover it, and hands numbers questions to Genie. That is your answer to "LLMs hallucinate".

**In the demo:** click **one** suggestion button ("Happened before?"), show the citation, click 👍. Then type one numbers question to show the hand-off to Genie. Don't improvise open questions live: retrieval is keyword search over 23 passages, the buttons are reliable. Short on time? Skip it; step 4 (the **Why** with its source) already shows the documents at work.

## Forecast error (WAPE)

The "10% vs 21%" is **WAPE**, weighted absolute percentage error: total units the forecast was off ÷ total units actually sold. Sold 1,000, off by 100 in total → 10%. Measured on the last 14 days, which the model never saw, against the current method ("same weekday last week").

- **Why WAPE:** the retail standard. It copes with slow movers and zero days (MAPE explodes there) and is weighted by volume, so bananas count more than avocados, like the money does.
- **Its limits (for the CDO):** it doesn't show direction (over-forecast = waste at cost, under-forecast = empty shelf at full price), so the pilot also reports **bias**; one total can hide a weak category, so the pilot reports it per category.
- **The point:** forecast accuracy is a means. The pilot is judged on waste, availability and time to decide.
- Say "forecast error" to the business; save "WAPE" for the CDO.

**Say:** "Forecast error is 10% against 21% with your current approach, on days the model never saw. But we won't judge the pilot on forecast accuracy; we'll judge it on waste and empty shelves."

## How it learns from what happens (slide 3 loop)

The prompt's pain: *"no mechanism to learn from outcomes over time."* There are three loops, each with an owner and a check:

| Loop | What flows back | What changes | Guard rail |
| --- | --- | --- | --- |
| **Forecast** | Every night: actual sales per store and product, including how promotions really performed | The forecast retrains on the latest weeks; the promo uplift for strawberries is learned from this 2+1, not assumed | A new version only replaces the current one if it beats it on days it hasn't seen (champion vs challenger). Monitoring flags drift, e.g. week 45 when strawberries switch to imports. *(MLflow, Unity Catalog model registry, Lakehouse Monitoring)* |
| **Decisions** | Every recommendation: approved or rejected (with a reason), and what happened next: did the transfer arrive, did the shelf stay full, was stock thrown away anyway | The rule settings get tuned with the category managers: e.g. raise the 20-unit transfer minimum if small transfers aren't worth the van, or order the backup grower earlier if it keeps arriving late | Changes are reviewed by the category manager, versioned, and visible in the acceptance rate per week. A rejected recommendation is the most valuable data point |
| **AI answers** | 👍/👎 on every answer and draft; new grower emails and incident notes as they arrive | Thumbs-down answers become test questions; new documents are indexed automatically, so this week's incident is next month's "Happened before?" | 50 questions graded by category managers run through MLflow evaluation on every prompt or retrieval change; no change ships if quality drops. Citation and number checks stay on |

**Honest about the prototype:** the 14-day backtest is real; the 👍/👎 is really logged (`/api/feedback`, and to a JSONL file when `FEEDBACK_LOG` is set); approvals are simulated and not stored; retraining, the registry, monitoring and the evaluation set are the pilot design.

**Say it like this (30 seconds):** "Today, when a promotion goes wrong, the lesson lives in someone's head. Here, three things flow back every day: what actually sold, which recommendations your planners accepted or rejected and why, and their thumbs up or down on the AI's answers. The forecast retrains on real sales, but only goes live if it beats the current one. The rules get tuned with your category managers. And every new incident note makes the copilot smarter next time."

| Persona | Stress |
| --- | --- |
| Business leader | It gets better the more you use it; this week's mistake isn't repeated next month |
| CDO | Every model version, rule change and evaluation is versioned and traceable; nothing changes silently |
| VP Engineering | Standard MLOps on the same platform: scheduled retraining job, registry, monitoring, evaluation. No extra tools |

## How the recommendations are formed (say it when you click **Do this**)

**The rules decide, the AI explains, the planner approves.** The recommendations come from a small, readable rule set (`plan_actions()` in `engine.py`) applied to the forecast and the unified data. No LLM and no text-to-SQL is involved in choosing an action. Always cheapest fix first:

1. **Size the gap**: expected shortfall from the forecast, plus one forecast error as a safety buffer.
2. **Use stock you already own**: move surplus from stores that would otherwise throw it away. At least 20 units, enough shelf life left on arrival (2 days produce, 1 day dairy; bakery and meat are never moved), on tomorrow's 06:00 chilled van. Worst-hit store gets served first.
3. **Then the approved backup supplier**: only when the regular grower confirmed below 80% (the contract clause that allows it). One combined order across stores, rounded up to the 20-case minimum, split by need, showing the +18% cost and arrival date.
4. **No backup?** Ask the regular supplier for an expedited drop, where allowed.
5. **Softer actions** (not one-click): cap the promotion or switch the hero product, plan a substitute display.

For **surplus** it runs the other way: send it to a store that needs it, mark down the rest following the markdown ladder, reduce the next order.

**Where the AI comes in:** each action carries a search query; the copilot uses it to find and cite the passage that justifies it (contract clause, transfer policy, the week-31 lesson) and to draft the store hand-over. **Genie** is the only text-to-SQL in the solution, and it's for ad-hoc numbers questions, not for deciding actions.

**Say it like this (30 seconds):** "It works like your best planner, with your own rule book. First: use stock you already own. Utrecht would throw these away, so move them. Then: the backup grower your contract already approves, but only when the main grower drops below 80%, as the contract says. Then softer measures, like adjusting the promotion. Every step shows its source, so your planner can check it. The AI doesn't make the decision. It explains it, and your planner approves."

| Persona | Stress |
| --- | --- |
| Business leader | Cheapest fix first: a transfer costs €0.15 a unit, the backup grower +18%, an empty shelf the whole basket |
| CDO | Transparent and auditable: same input, same answer, every number from the forecast and the data, never from the language model |
| VP Engineering | A small, readable piece of logic. In the pilot the thresholds (20 units, 80%, shelf life) live in a governed table your category managers own and change in weeks 1 to 2 |

## Customer and cast (assumptions to validate)

- **Groenhof Markets**: mid-sized Dutch grocery chain, about 110 stores, about €1.2B revenue, about €400M of it fresh.
- **Pain**: fresh waste around 3.5% of fresh sales (about €14M a year), Saturday on-shelf availability around 95% on fresh (5% empty, deliberately conservative: published retail studies put the average out-of-stock rate at about 8%, worse in fresh and at peak times), and every Monday meeting starts with "whose number is right?".
- **Systems**: Postgres (POS and promotions), MySQL (store stock), a supplier portal (SaaS, CSV export), and years of supplier agreements, grower updates and incident notes in documents and email.
- **Panel personas**: Business leader (COO or Commercial Director), CDO or Head of Data, VP Engineering.


## Run of show (60 minutes)

| Block | Min | What | Goal |
| --- | --- | --- | --- |
| Discovery | 10 | No slides, then slide 1 | Confirm the pain, the numbers, the owners and the constraints |
| The art of the possible | 14 | Slide 2, then the live app | One of their problems, solved end to end: who uses it, how |
| Behind the solution | 4 | Slide 3 | "What you just saw: four connected layers" |
| Value and future state | 5 | Slide 4 | The platform once the pilot has proven itself: every store, every team |
| Next steps | 4 | Slide 5 | How 30 days proves it on their own data (look back, run alongside, compare), then get the "go" |
| Buffer for questions | ~8 | | Interruptions are the point. Welcome them |
| Debrief (role-play ends) | 15 | | Approach, tools, trade-offs, what you'd do differently |

**Clock rules:** at minute 12 you must be on slide 2. If you're behind, skip **Where the numbers come from** in the app and offer it to the CDO afterwards. Never skip slide 5. Questions are not overhead: if one check-in turns into a good conversation, cut a demo step, not the conversation.

---

## 1. Discovery (10 min, start without slides)

Open: "Thanks for the time. Before I show anything, I want to check I've understood the problem. I'll ask a few questions. If I'm wrong, that's the most useful thing that can happen today."

**Ask** (30 seconds per person, before the four questions): "What would make this hour useful for you?" Go round the room by name. Note each answer and make sure you hit it before the end; refer back to it ("You asked about cost, here it is").

| # | Ask | Who answers | Listen for | Write down |
| --- | --- | --- | --- | --- |
| 1 | "When a store runs out of strawberries on a Saturday, how do you find out, and how long after?" | Business | Monday reports, complaints, no early warning | Hours or days of delay |
| 2 | "What does fresh waste cost you a year, and which categories hurt most?" | Business | € or % of fresh sales; bakery, produce, meat | Their waste % and € |
| 3 | "If commercial and supply chain show different numbers, who decides which one is right?" | CDO | No owner, spreadsheet merges, definitions | Owner and number of sources |
| 4 | "What must not change: systems, security rules, cloud, team skills?" | VP Eng | Cloud provider, SAP or ERP, team size, security reviews | Hard constraints |
| 5 | "If this worked, what would you see differently in six months? Which company target does it move?" | Business | Margin, availability, a waste or sustainability target (CSRD, food waste pledges), NPS | The OKR you tie slide 5 to |

Bonus questions if there's time:

- "When a supplier warns you about a short harvest, where does that information go?" (Usually an email to one buyer. Sets up the copilot.)
- "What have you tried before, and why didn't it stick?" (Sets up the forecasting-tool objection before they raise it.)
- "Where does your data team spend most of its week today?" (CDO, VP Eng. Usually: reconciling numbers.)

**Confirm the planning morning (2 min, sets up slide 2).** Slide 2 and the demo are built on these assumptions. State each one and let them correct you; if they do, press `E` on slide 2 and change it live.

| Our assumption | Ask | If they say otherwise |
| --- | --- | --- |
| A central **fresh planner** per category (about 5 for produce) decides what each store gets | "Who decides what each store gets of fresh tomorrow: head office or the store?" | If stores order themselves, the store manager becomes the main user; the demo still works |
| Planners start around **05:30** with yesterday's sales; supplier orders close at **12:00** | "When does that person start, and when do supplier orders close?" | Change the times on slide 2 |
| Today that takes **2 to 3 hours** a morning across spreadsheets, the supplier portal and email, and risks are spotted on gut feel | "How long does that take today, and with which tools?" | Their number replaces "five minutes vs hours" in your close |
| Stock can move **between stores** on the next morning's van from the distribution centre | "Can you move fresh stock from one store to another, and how fast?" | If not, lead with the backup supplier instead of the transfer |
| Store managers hear about changes by **phone or ad-hoc email**, with no standard hand-over | "How does a store manager hear that tomorrow's delivery changed?" | Sets up the **Draft message to the store** |
| A **planning manager** (head of fresh supply) reviews the week, mostly in the Monday meeting | "Who looks across all stores and the whole week?" | Use their job title for the third person on slide 2 |
| Each product has an **approved backup supplier** in the contract, with a minimum order | "If a grower can't deliver, who is the backup, and where is that written down?" | Sets up **Ask the copilot** citing the contract |
| A region has about **20 to 30 stores**, planned by the same central planners | "How many stores are in a typical region, and does one planner cover all of them?" | Sizes the pilot on slide 5: half with it, half without (10 vs 10 by default) |

Then show **slide 1** and say: "This is what I heard from your team before today. Which of these numbers is wrong?" If they correct a number, press `E` and change it live. That's the strongest listening signal you can give.

## 2. Slide 1: the problem (included in discovery)

- "Two stores, same fresh product, same week: a shortage in Amsterdam, so the shelf is empty, and a surplus in Utrecht that ends up as waste. It isn't a people problem. Nobody can see both at once."
- Each card has a question that tests it (not on the slide). Ask them out loud, to the right person: the **COO** on where waste hurts most and what an empty shelf costs (one box or the whole basket), the **CDO and Engineering** on whose number wins and who owns each system.
- Business translation: waste is margin you've already paid for. An empty shelf is a customer who tries the competitor.
- On the 5%: "That's deliberately conservative. Research on retail out-of-stocks puts the average at about 8%, and fresh on a Saturday is usually worse. Is it better or worse for you?"
- **Ask** before moving on: "Of these three, which one hurts most right now: the waste, the empty shelves, or the time it takes to agree?" Their answer decides what you stress in the demo.
- Bridge to slide 2: "There are several problems in here. Let me show you one of them solved end to end: fresh planning."

## 3. Slide 2 and the live demo: the art of the possible (about 14 min)

On slide 2, 30 seconds: "This is for three people. The fresh planner starts at 05:30 and works in the app. The store manager gets the hand-over and doesn't need the app. The planning manager sees the whole week and asks Genie. One morning, three moves." Then click **Open the live copilot**. (The app says "Huelva Berry Cooperative": that's the backup grower from the slide, in southern Spain. Say "our Spanish backup" the first time.)

| Step | Click | Say | Persona hook |
| --- | --- | --- | --- |
| 1 | The heading and the four numbers | "It's 05:30 on Tuesday. The planner opens one page: eight shelves need a decision, €1,326 at risk this week. The planning manager reads the same four numbers." | Business |
| 2 | Top of **Today's decisions**: Amsterdam strawberries, and the line under the headline | "Worst first. Amsterdam runs out on Thursday, the first day of the 2+1 promotion." Then read the line: see **Reading the decision line**. | Business |
| 3 | The chart | "Grey is demand, green is what the supplier actually confirmed, the line is stock. Below zero is an empty shelf." | All |
| 4 | **Why** and its source chip | "This didn't come from a model. It came from a grower update in someone's inbox: rain in Zeeland, 70% confirmed. Hover the chip: there's the source." | Business: wow moment |
| 5 | **Do this**, then **Approve** on the transfer | "Utrecht has 80 boxes it can't sell in time. Move them on tomorrow's 06:00 van." Then the 30-second rules explanation (see **How the recommendations are formed**). Click Approve: the numbers at the top update and the green line says it's simulated. | Business: decision |
| 6 | **Draft message to the store** | "One click, and the store manager has the hand-over: what, why, what to do, what to watch. Here it's a template; with a model endpoint the model writes it and it's rejected if it invents a number." | Business, VP Eng |
| 7 | **Ask the copilot**: **Happened before?** | "Follow-ups go to the documents. Week 31: same story, about €4,200 lost. The organisation learns from its own history." Click 👍: "every vote is logged; the bad ones become test questions." | Business: learning loop |
| 8 | Type "How much waste per store this week?" | "It doesn't guess numbers. That's Genie's job, on the same governed tables." Click **Open in Genie** (or the **Ask Genie** tile). | CDO / VP Eng |
| 9 | Utrecht strawberries in the list, now **✓ Handled** | "Same transfer from the other side: waste becomes sales." | Business |
| 10 | Optional: **Where the numbers come from**, the **Forecast accuracy** tab | "Four sources, 2 bad rows quarantined, 9 store codes fixed. And measured, not claimed: 10% forecast error versus 21% with 'same as last week', on days the model never saw." (WAPE: see **Forecast error**.) | CDO |

Close the demo: "One planner, one morning, five minutes. Today that takes your team a week and three spreadsheets."

**Ask during the demo** (pick three or four, don't ask all; name the person):

| After step | Ask | To | Why |
| --- | --- | --- | --- |
| Slide 2, before clicking | "Does this look like your planners' morning, or would you change something?" | Business | Last chance to adjust the story before the demo |
| 2 · the risk | "Today, when would your planner have spotted this: Tuesday, or Saturday when the shelf is empty?" | Business | Makes the delay concrete in their words |
| 4 · the source | "Where does a grower email like this land today, and who else sees it?" | Business | Proves the knowledge gap is real |
| 5 · the action | "Would your planner trust this move? What would they want to check first?" | Business | Surfaces trust objections early, on your terms |
| 6 · the draft | "How does a store manager hear about a change like this today?" | Business | Confirms the hand-over pain |
| 7 · happened before | "What other knowledge sits in one person's inbox that you'd want in here?" | Business, CDO | Next use cases, in their words |
| 8 · Genie | "Which numbers does your data team get asked for most?" | CDO | Sizes the self-service value |
| 10 · accuracy | "How do you measure forecast accuracy today, if at all?" | CDO | Sets up the look back on slide 5 |
| End of demo | "What would change in your Monday meeting if planners worked like this?" | Business | Lets *them* say the value out loud |

**Be honest about what's mocked:** data is synthetic, Approve sends nothing, and without a model endpoint the draft is a labelled template. Say it before someone asks.

## 4. Slide 3: behind the solution (about 4 min)

"What you just saw is four connected layers." Point back at what they saw, left to right, one technical noun per layer for the engineers:

1. **Trusted data**: "The four numbers and the list come from Postgres, MySQL and the supplier portal, joined once on a product in a store. Bad rows are quarantined, not dropped." *(Lakeflow Connect, Bronze/Silver/Gold, expectations.)*
2. **Predict**: "The chart is a demand forecast per store and product, turned into two questions people act on: will this shelf go empty, will this stock expire?" *(MLflow, Unity Catalog model registry, monitoring.)*
3. **Explain**: "The **Why**, the draft and the answers come from your supplier documents, cited." *(Vector Search, Model Serving.)*
4. **Act**: "Planners approve in the app. Managers ask Genie for any other number." *(Databricks Apps, Genie, AI/BI.)*

Then the loop, for the business leader: "And it learns. Every approved move and every real sale goes back in, and the forecast retrains on it. Planners' thumbs up or down on the AI answers become the test set it's graded on. Today you have no way to learn from outcomes; this is that way." *(MLflow retraining and evaluation, monitoring.)* Details and the three loops: **How it learns from what happens**.

Then the line for the CDO: "Underneath sits one set of rules: who sees what, quality checked at the door, and every number traceable to its source. Lineage, row filters and audit are what we'd configure with you in the pilot; the prototype doesn't enable them."

**Ask:**

- CDO: "Who owns the definition of 'stock' and 'waste' today? Is it written down anywhere?"
- VP Eng: "Which of these pieces do you already have, and where would this sit next to your current stack?"
- VP Eng: "What would your security team ask first?" (Better to hear it now than in week 1.)

## 5. Slide 4: future state at scale (about 5 min)

- Frame it: "This is where you land once the pilot has proven itself. Nothing on this slide is a rebuild of what you saw; it's the same four layers, wider."
- Left, sources: "Today's four sources, plus your ERP, weather and loyalty. Each new source makes every forecast better."
- Middle, top to bottom: "Data comes in within minutes, not overnight. One trusted copy, owned by a named team. Forecasts for every product in every store, and AI that cites your documents, both checked every day. Then the planner app, plain-language questions for managers, dashboards, and data shared with your growers." *(For engineers: Lakeflow Connect and streaming; Delta and open formats; MLflow, Mosaic AI, Vector Search, Lakehouse Monitoring; Apps on Lakebase for instant approvals, Genie, AI/BI, Delta Sharing.)*
- Right, users: "Planners, store managers, managers and finance, and your growers. Then the next problems on the same data: promotions, markdowns, staffing, loyalty." Pick the one that came up in discovery.
- Bottom, for the CDO: "One set of rules underneath: who sees what, where every number comes from, full audit." *(Unity Catalog.)*
- Path if asked: 30 days on fresh in one region, a quarter for all fresh, a year for the chain. Each step goes ahead only if it pays for itself.
- **Ask:** "Of these next problems, which would you pick first, and why?" and "Which source is missing here that your teams rely on?" (Business, CDO). If they pick one, say it again on slide 5 as the likely next step.

## 6. Slide 5: next steps, the 30-day pilot (about 4 min)

Frame it: "I don't want you to believe a slide. I want you to see it on your own data, in 30 days, in one region."

**How we prove it on a small subset: three kinds of evidence, fast to convincing.**

| Evidence | How | Why it convinces |
| --- | --- | --- |
| **Look back** (week 2, no risk) | Replay last quarter for the region on *their* data: which run-outs and write-offs it would have flagged, how early, and the € value | A € figure on their own history within two weeks, without touching operations |
| **Run alongside** (weeks 2 to 4) | 10 stores get the recommendations; planners still decide and log whether they'd act on each one and why not | Proves planners trust and use it: acceptance rate, time from signal to decision, top reasons for "no" |
| **Compare** (weeks 2 to 4) | 10 similar stores (size, mix, city centre or suburb) run as today, over the same weeks | Takes out weather, season and promotions, so the difference stands up to finance |

Look back and run alongside start together in week 2: the look back needs only history, run alongside needs the daily feed from week 1. Three weeks alongside is short for a waste trend, so be honest: the **look back carries the €**, the **run alongside carries trust and speed**, the comparison is the early signal.

**Why 10 and 10 (if asked):**

- **Fits a mid-sized chain.** With ~110 stores a region is roughly 20 to 30 stores, so 10 + 10 is the region split in two.
- **Big enough to be fair:** one store's odd week (roadworks, a local festival, a broken fridge) doesn't decide the result.
- **Small enough to support:** a handful of planners and 10 store managers can be trained and followed closely; you can call every store if something goes wrong. The other ~90 stores aren't touched.
- **Why a comparison group at all:** late October has the switch to imported strawberries, weather and promotions. The 10 stores without it live through the same weeks, so the *difference* is what the pilot did. That's what finance trusts.
- **"Similar" means paired** on size, product mix and type of location; with this few stores, pairing beats picking at random.
- **Be honest:** 10 vs 10 over three weeks is an early signal, not statistical proof of lower waste. That's why the look back carries the €.
- **Watch the spill-over:** if the same central planner plans both groups, what they learn leaks into the comparison stores. Show recommendations only for the pilot stores and check the comparison stores' decisions stay as usual, or give them to a different planner if possible.
- **Make it a discovery question:** "How many stores are in a typical region, and does one planner cover all of them?" If a region has 14 stores, go 7 vs 7; the method stays the same.

**% accepted** on the slide means: of all recommendations the planners saw in the 10 pilot stores, the share they would act on (approved or would have approved). Each "no" is logged with a reason. It's the clearest measure of trust; a low number with good reasons is still useful, because it tells you which rules to fix.

| When | What happens | Who from Groenhof | Done when |
| --- | --- | --- | --- |
| Week 1 · Connect | Sales, stock and supplier portal connected for one region (Lakeflow Connect on a read replica, portal export into a volume); Unity Catalog set up with IT's access rules; scorecard agreed | DBA, security, 1 data engineer, sponsor | Data refreshed daily; scorecard signed off |
| Week 2 · Look back | Forecast trained and replayed on last quarter; € of run-outs and write-offs it would have caught | Fresh category manager, finance | Finance agrees with the method and the € |
| Weeks 2–4 · Run alongside | Risk list and copilot for planners in 10 stores, 10 similar stores as comparison. Planners decide; every accept or reject is logged with a reason | Fresh planners for the region, 10 store managers | Acceptance rate, time to decide, top 3 wrong recommendations understood |
| Day 30 · Decide | One scorecard: look-back €, the two store groups compared, planners' verdict, cost of running. Go, adjust or stop | Sponsor | A decision, either way |

**What you'll know after 30 days** (the three numbers on the slide): **€ saved** on last quarter replayed; **% accepted**: the share of recommendations planners would act on; **same morning** from signal to decision. Then point at the small line: "At full scale, one point of fresh waste is about €4M a year. That's what it's worth if the 30 days hold up, not what the 30 days prove."

**The ask, on the slide as "To start next week":** a sponsor and a fresh category manager; access to sales, stock and supplier data; agreement on how we measure success. It's framed as what we need to start, not a demand; make the direct ask out loud instead: "If it doesn't move the numbers, you'll know in 30 days for very little money. If it does, the next step is all fresh, then the rest of the chain."

**Ask** before the closing line (these move you to a decision):

- "Does this plan feel realistic for your team, or is there a week you'd worry about?" (VP Eng)
- "Which region would you pick, and who would be the natural sponsor?" (Business)
- "What would make you say no at day 30?" (Business, CDO) Write the answer down: that's the scorecard.
- "Who else needs to be involved to say go: finance, security, the works council?" (Business)
- "Is there a budget moment or planning cycle we should line up with?" (Business)

Closing line: "Can we agree today on the region and the sponsor, so we can connect the data next week?"

---

## Persona map

| Persona | Cares about | Lead with | Show | Avoid |
| --- | --- | --- | --- | --- |
| Business leader (COO, Commercial Director) | Margin, availability, speed, customer trust | Euros at risk, the strawberry story | Risk list, cited actions | Model names, architecture detail |
| CDO / Head of Data | One version of the truth, quality, ownership, compliance | "One copy, one set of permissions, lineage" | Quarantine counts, "Where the numbers come from", Unity Catalog | Promising accuracy before seeing their data |
| VP / Director of Engineering | Complexity, run cost, skills, lock-in, security | Open formats, managed services, small team | Notebook, `app.yaml`, the 30-day plan | Hand-waving on effort |

## Objection handling

**The method, every time (about 30 seconds):**

1. **Acknowledge** without defending: "Fair concern." / "You're right to ask."
2. **Ask back** to find the real worry: the "Ask back" column. Skip it if the question is already specific.
3. **Answer** in one or two sentences, in their language, with something from the demo if you can.
4. **Check**: "Does that answer it?" If not, offer to take it offline and write it down where they can see.

Never argue a number: "Your number beats mine, let's use it" and press `E`. If you don't know: "I don't want to guess. I'll come back to you by tomorrow."

### Value and cost (Business leader, finance)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"What does this cost?"** | "For the pilot, or at full scale?" | "For the pilot, a small team and consumption-based compute on one region. Single-digit thousands of euros of platform spend a month is a realistic starting range to validate with your account team. You pay for what runs, and the forecast runs once a night. Compare that with \u20ac4M per point of waste. We'll put the real cost in the day-30 scorecard so you decide on facts." |
| **"And at full scale?"** | "Which part worries you: the platform bill, or the people to run it?" | "It grows with stores and products, not with users, and the look back gives you the \u20ac on the other side of the scale. I'd rather give you a number from the pilot's real usage than a guess today. It goes in the day-30 scorecard." |
| **"Cloud bills can explode."** | "Have you been burned before?" | "Fair. Budgets and alerts are set from day one, every job's cost is visible, and serverless compute switches off when nothing runs. The forecast is one nightly job; that's predictable." |
| **"We don't have budget this year."** | "Is it the money, or the timing in the budget cycle?" | "The pilot is deliberately small so it fits in an existing budget. If the look back shows the \u20ac on your own history, it builds the business case for next year's budget." |
| **"What's the ROI or payback?"** | "Which number would your CFO want to see?" | "I won't promise one today. Week 2 replays last quarter on your data and puts a \u20ac figure on what would have been caught. That, plus the cost of running, is the ROI you decide on." |
| **"Your numbers are wrong."** (\u20ac14M, 5%) | "What's the right number?" | "Good, your number beats mine." Change it live with `E`. "Does the problem still hold at that size?" |
| **"Our waste is already low."** | "Is availability also where you want it?" | "Then the value is on the other side: empty shelves on a Saturday. Same system, same data; we'd measure availability first." |

### Trust in the data (CDO)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"Can we trust the data?"** | "Which source worries you most?" | "Bad rows are quarantined and counted, not hidden: you saw 2 caught today. Lineage back to source rows is part of the pilot design, and finance agrees the look-back method in week 2 before anyone acts on it." |
| **"Our data quality is bad."** | "Where is it worst: stock, sales or supplier data?" | "That's normal, and it's the point: you see the problems counted instead of hidden in a spreadsheet. We start with what you have, and the quality checks tell you which source to fix first." |
| **"Our stock figures in the system are often wrong."** | "How far off, and in which categories?" | "Common in fresh. The forecast leans on sales, which are reliable; stock gaps show up as warnings, not silent errors. The pilot measures how often stock was wrong, which is useful on its own." |
| **"We don't have enough clean history."** | "How far back do you have sales per store and product?" | "Eight weeks is enough for a first forecast; a quarter is enough for the look back. Less history means a wider error band, and the app shows that honestly." |
| **"Who owns the numbers then?"** | "Who owns them today?" | "Each table gets a named owner in the catalog, and definitions like 'waste' are written once. That's a decision for your team; the platform makes it visible and enforceable." |
| **"Does it need real-time data?"** | "Which decisions can't wait for tomorrow morning?" | "Not for planning: nightly is enough for a 05:30 decision. If stores need intraday updates later, the same pipelines can stream; that's on slide 4." |

### AI reliability (all, especially CDO)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"LLMs hallucinate."** | "Have you seen that go wrong in another project?" | "The copilot only answers from retrieved passages and the risk table, and cites both. When it can't find an answer, it says so. Numbers come from the model and the data, never from the LLM. During the pilot a person decides on every action, and we log answers to review them." |
| **"So the AI decides what we do?"** | | "No. The actions come from your rules applied to the forecast, so the same situation always gets the same answer and you can audit it. The AI's job is to explain the action with your own documents and write the hand-over. Your planner approves." |
| **"Who wrote these rules?"** | | "For the demo, I took them from typical supplier agreements and fresh policies. In the pilot your category managers set them: they're settings in a table, not code buried in a model." |
| **"What if the forecast is wrong?"** | "What would a wrong forecast cost you today?" | "It will be, sometimes. That's why we show a probability, not a promise, and why we measure error every night against your current method. If it drifts, monitoring flags it and we retrain." |
| **"Is 10% forecast error good?"** | | "It's half the error of your current 'same as last week' method, measured on days the model never saw. But it's a means, not the goal: we judge the pilot on waste and availability, and we'll also track whether it runs high or low, because over and under cost you differently." |
| **"The answers aren't perfect."** | "Which answer would you have expected?" | "Agreed, and here they come from keyword search over 23 passages. In the pilot: embeddings, real grower emails, and 50 questions your category managers grade, run through MLflow evaluation on every change. The \ud83d\udc4d/\ud83d\udc4e on each answer feeds that set." |
| **"How does it get better over time?"** | | "Three loops: real sales retrain the forecast, but it only goes live if it beats the current one; accepted and rejected recommendations tune the rules with your category managers; thumbs up and down on AI answers become the test set every change has to pass." |
| **"Can someone manipulate it, e.g. a supplier email with hidden instructions?"** | | "The AI can't take actions: it explains and drafts, and actions come from rules on the data. Answers must cite a passage, and the planner approves. That limits what a bad document can do; we'd test for it in the evaluation set." |
| **"Which AI model, and does our data go to OpenAI?"** | "Is there a policy on external AI providers?" | "You choose the model. It can run inside your Databricks workspace in your cloud region, or through a gateway you control with logging. I'd confirm data-use terms with your security team rather than promise them today." |

### Security, privacy and compliance (CDO, VP Eng)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"Our supplier contracts are confidential."** | "Who should be able to see them?" | "In the pilot design, documents stay in your cloud account under Unity Catalog permissions, cost columns can be masked for store roles, and model calls go to an endpoint inside the workspace. I would confirm the data-use and logging terms with your security team rather than promise them today. Approve in the demo is simulated; it sends nothing to stores or suppliers." |
| **"GDPR?"** | | "The pilot uses no personal data: sales per store and product per day, stock, supplier deliveries and documents. Loyalty data comes later, with its own purpose and access rules." |
| **"Our data must stay in the EU."** | "Which cloud and region are you on?" | "It runs in your own cloud account, in the region you choose, so data stays where it is today." |
| **"Who sees what? Store managers shouldn't see costs or other stores."** | | "Access is set per role: store managers see their own store, costs can be masked, and every access is logged. That's configured with IT in week 1." |
| **"What about the EU AI Act?"** | | "This is decision support with a person approving every action, which most likely isn't a high-risk use. I'd confirm with your legal team; the logging and human approval help either way." |
| **"Our security review takes months."** | "What does it usually get stuck on?" | "Then let's start it now, in parallel. The pilot needs read access to two databases and the portal export, nothing that writes back. If it helps, the look back can run on an extract while the review runs." |

### Competition and existing tools (VP Eng, CDO)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"We already have Snowflake / Fabric / an SAP planning tool."** | "What does it do well for you today?" | "Keep what works. The question is where the forecast, the documents and the AI meet under one set of permissions. Databricks reads and writes open formats (Delta, Iceberg), so it can sit next to what you have. Specialist replenishment tools are strong at ordering, but they don't read your grower emails." |
| **"Why not a specialist replenishment tool (RELEX, Blue Yonder, SAP)?"** | "Have you evaluated one?" | "They're strong at automated ordering. This is about the gaps around them: connecting your scattered data, explaining *why* with your own documents, and using the same data for promotions, markdowns and more. It can feed a replenishment tool better data rather than replace it." |
| **"Why not Microsoft Copilot or ChatGPT?"** | | "Great for documents and email. But it doesn't see your forecast, stock and supplier data under your permissions, so it can't tell you *which* store runs out and what to do. Here the AI sits on the same governed data as the forecast." |
| **"Why not just use Genie for everything?"** | | "Genie answers numbers questions on tables, and we use it for exactly that. But why Amsterdam runs out isn't in a table: it's in a grower email and a supplier contract. The copilot reads those, and the draft turns both into a hand-over for the store. Same tables, same permissions underneath." |
| **"Why not just build this in Excel or Power BI?"** | | "Power BI is a great front end and can sit on top of this data. What it can't do is train and monitor a model, search documents and govern both. That's the gap." |
| **"We can build this ourselves on AWS/Azure services."** | "How many engineers would you put on it?" | "You could. You'd be connecting five or six services and maintaining the glue. Here ingestion, governance, models, search and the app share one set of permissions, so your team spends time on the problem, not the plumbing." |
| **"Lock-in?"** | | "Data stays in open formats in your own storage, MLflow is open source, and the code is Python and SQL. If you leave, you take everything with you." |

### Complexity and feasibility (VP Eng)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"This sounds complex. We have three data engineers."** | "What are they spending their week on now?" | "That's why it's one platform instead of five tools: managed connectors, managed model serving, managed vector search. The pilot is one notebook, one app and one job. What you're seeing was built in an afternoon on synthetic data." |
| **"Who maintains it after the pilot?"** | | "Your team, with us alongside in the pilot. The run is one nightly job and one app; most of the ongoing work is tuning rules with category managers, not engineering." |
| **"Our team doesn't know Spark."** | "What do they use today?" | "They don't need to: it's SQL and Python, and the compute is managed. Business users ask Genie in plain language." |
| **"How much of the demo is real?"** | | "The data is synthetic; the forecast, the risk calculation, the rules and the quality checks really run; Approve is simulated and sends nothing; without a model endpoint the draft is a template. On your data, the pilot makes it real." |
| **"How long did this take you?"** | | "An afternoon on synthetic data. Production on your data is what the 30 days are for." |

### People and change (Business leader)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"We tried a forecasting tool. Planners ignored it."** | "Why did they ignore it?" | "That's why weeks 2 to 4 run alongside your planners, and why every recommendation says *why* and cites the source. People trust what they can check, and we log every 'no' with the reason." |
| **"Planners will feel replaced."** | "How do they feel about their mornings today?" | "The planner decides; the app takes away the spreadsheet work, not the judgement. In the pilot planners help set the rules, so it's their tool." |
| **"Store managers won't read another message."** | "How do they get changes today?" | "One clear hand-over replaces a few phone calls. It goes through the channel they already use; we'd agree that in week 1." |
| **"Does the works council (ondernemingsraad) need to be involved?"** | | "Possibly, if decisions are logged per planner. The log is about recommendations, not about people, but I'd involve them early rather than late." |

### The pilot itself (Business leader, finance)

| Objection | Ask back | Answer |
| --- | --- | --- |
| **"Can 30 days really prove a waste reduction?"** | | "Not on its own, and I won't pretend it does. That's why we replay last quarter on your data for the \u20ac, run 10 stores against 10 similar ones for the early signal, and measure whether planners trust it. If those three line up, the full-season result follows; if they don't, you stop." |
| **"10 stores is too small."** | "How many would convince you?" | "It's an early signal on purpose, at low risk. The \u20ac comes from the look back across the whole region's history. If you'd rather run more stores, the method stays the same." |
| **"Why not all stores at once?"** | | "Because if it's wrong, it's wrong everywhere. Ten stores, planners still deciding, a decision at day 30: you learn fast for very little risk." |
| **"Why fresh produce and not bakery or meat?"** | "Where does it hurt most for you?" | "Produce has the most volatility and the backup-supplier story. If bakery hurts more, we start there; the method is the same." |
| **"What if the results are inconclusive?"** | | "Then we've learned it cheaply. That's why we agree the scorecard and what 'no' looks like before we start." |
| **"How long until all 110 stores?"** | | "Honestly, it depends on what day 30 shows. Typically: one region in 30 days, all fresh categories in a quarter, then the rest. Each step only goes ahead if it pays for itself." |
| **"Why Databricks?"** | | "Because your problem crosses all four layers: scattered data, forecasting, documents and an app people use. Here they share one copy of the data and one set of permissions, instead of four tools glued together." |

## If something breaks

- **App won't load:** use the screenshots in `slides/` (take them in your gut-check) and keep talking. The story doesn't need the app.
- **A question you can't answer:** "Good question. I don't want to guess. Let me come back to you with the exact answer by tomorrow." Write it down where they can see.
- **Running late:** skip slide 3 (offer it to the engineers afterwards), keep slide 4 to one minute, and never skip slide 5.

## Debrief (15 min, role-play ends)

- **Approach:** started from the business decision ("what should a store manager do at 05:30?") and worked back to the data, not the other way round.
- **Build:** Flask app with a deterministic engine (`app/demos/grocery/engine.py`) shared with the Databricks notebook, so local and lakehouse show the same numbers. A simple, explainable forecaster on purpose, because the story needed trust more than a few points of accuracy. A gradient-boosted model is the obvious next step, and it would have to beat this one on the same held-out days.
- **Trade-offs:** synthetic data; offline copilot composer instead of a live LLM, for reliability in the room; scripted scenarios so the story is the same every run.
- **What I'd do next:** real backtests on customer data, Lakehouse Monitoring on the forecast, an evaluation set for copilot answers (MLflow evaluation), and a Genie space on the Gold tables.

## 30-minute gut check

- [ ] `python -m app.main`, then open `/` and `/story`. Click through all 5 slides and the demo path once.
- [ ] Ask the four suggestion buttons once each.
- [ ] Save screenshots of the copilot, the strawberry draft message and each slide as an offline fallback.
- [ ] Say the one-sentence story out loud without notes.
- [ ] Say the ten questions to know by heart out loud, and pick the three demo check-ins you'll use.
- [ ] Have your answers ready for cost, hallucinations, "we already have X" and "can 30 days prove it?". Practise acknowledge, ask back, answer, check on two of them.
