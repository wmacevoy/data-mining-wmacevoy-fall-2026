# Data Science

What this course thinks the discipline is, and why the rest of the repository is shaped the way it
is.

| Document                    | Answers                                          |
| --------------------------- | ------------------------------------------------ |
| `DATA-SCIENCE.md`           | why we work this way                             |
| `README.md`                 | how to run anything here                         |
| `colorado_river/README.md`  | what the reference project is, and what is deliberately wrong with it |

Nothing in this file is checkable by continuous integration. That is exactly why it has to be
written down: the parts of the discipline that no tool enforces are the parts that get lost, and
then rediscovered at full price.

This document is a rewrite of `SOFTWARE-ENGINEERING.md` from the companion course, and the
parallels are deliberate. Software engineering asks *does the thing work*; data science asks *is the claim true*.
Mostly the same discipline pointed at a different noun — and this document is about the places
where it isn't.

---

## What data scientists are for

**Data scientists produce claims that are worth acting on, on time, within the data and compute
they actually have, in a way that manages discomfort for the team, the client, and the people in
the data.**

Four constraints that trade against each other, and a fifth — the question — that is usually the
honest one to move. Narrowing the question is not failure; it is the most common form of success.

Note that *worth acting on* is not *accurate*. Accuracy is a property of a model measured against a
held-out sample. Worth acting on is a property of a claim that must survive a world containing
selection bias, drifting definitions, revised measurements, labels that are proxies for what you
care about, and people who behave differently once the model is watching. **A model is correct
about a dataset. A claim is true about a world.** The gap between those two sentences is where most
of the work is.

The characteristic failure of this field is not a crash. It is a number that is confidently,
plausibly, reproducibly wrong, produced by code that ran without error.

### Discomfort is a first-class variable

| Whose                  | What it looks like                                     | What reduces it                              |
| ---------------------- | ------------------------------------------------------ | -------------------------------------------- |
| The client             | surprise; a number that moved and nobody can say why     | frequent, honest, boring status — including nulls |
| The team               | fear, thrash, heroics, re-running everything at 2am      | slack, small steps, one command back to raw   |
| The people in the data | being measured, misclassified, or surprised by a decision they cannot see | minimization, aggregation, recourse |

The third row does not appear in the software engineering version of this table, and it is the one
that matters most. In software the user and the affected person are usually the same; in data
science they routinely are not. The person whose row you are modeling did not agree to the
question and will never see the output — only its consequences.

Discomfort is a leading indicator. When someone stops wanting to re-run the pipeline, that is
information about the pipeline.

---

## Most of practice is being less nervous

Version control. Seeds. Baselines. A held-out set. Data profiling. Code review. Short iterations.
Showing a domain expert the plot. Each is normally taught as a rule to follow. Each is better
understood as a way of retiring one specific fear, and you should be able to name which.

| Practice                              | The fear it retires                                       |
| ------------------------------------- | --------------------------------------------------------- |
| Version control                        | "I can't get back to when it worked."                      |
| A pinned environment                   | "It solved differently on their machine."                  |
| Recorded seeds                         | "The result was luck."                                     |
| One command back to raw                | "I can't reproduce the number in the slide."               |
| A dumb baseline                        | "I don't know if my model beats the mean."                 |
| A held-out set, touched once           | "I fit the thing I was measuring with."                    |
| Grouped / time-ordered splits          | "My folds shared a subject, a site, or a future."          |
| Data profiling and schema checks       | "The input changed and nothing said so."                   |
| Row-count assertions across a join     | "I silently multiplied my dataset by three."               |
| Unit tests on transform code           | "I don't know if I just broke a feature."                  |
| Writing the analysis plan first        | "I found this by looking forty times."                     |
| Showing a domain expert the plot       | "That gauge was under construction that year."             |
| Continuous integration                 | "It works in my notebook."                                 |
| Code review                            | "Only one person understands this."                        |

Two consequences follow, and both are load-bearing:

- **A practice that reduces no one's anxiety will be abandoned under pressure.** Ceremony that
  costs time and returns no relief gets dropped in week ten, and it should be. If you cannot name
  the fear a practice retires, either find it or stop doing it.
- **A practice that reduces anxiety without reducing risk is worse than nothing.** A train/test
  split that leaks. A cross-validation whose folds share a patient. A 99% accuracy on a 99%-negative
  class. A dashboard tracking a proxy that stopped correlating with the thing last quarter. A
  reproducibility badge on a pipeline nobody has re-run from cold. These are the most dangerous
  artifacts in the field, because they spend the alarm and leave the danger in place — and unlike
  in software, there is often no later moment when reality forces the issue. A wrong bridge falls
  down. A wrong number just gets used.

---

## The taxonomy of unknowing

| #      | Category              | What it is                                                            |
| ------ | --------------------- | ---------------------------------------------------------------------- |
| **K0** | The known             | Things you know, that are true.                                         |
| **K1** | The known unknown     | Things you know you don't know.                                         |
| **K2** | The unknown unknown   | Things you didn't know you didn't know.                                 |
| **K3** | Erroneous certainty   | What feels like K0 and is false.                                        |
| **K4** | True falsehoods       | Things we hold as true, knowing they aren't, because they're useful.    |

**K0 through K3 are in order of expense.** Checking the units is cheap. Investigating a question
you have already framed is more. Being surprised costs a re-analysis. Being confidently wrong costs
whatever decision was made on top of the belief, discovered — if you are lucky — at the worst
possible moment, and if you are unlucky, never. K4 is not on that ladder at all; it is a choice,
and a good one.

**Doing data science is the act of discovering, in the right order and at the right price, which
category each part of a dataset and each step of a method belongs to.** Every practice in this
repository is a way of moving something down the ladder before it charges full price.

| From   | To     | How                                                                                                     |
| ------ | ------ | ------------------------------------------------------------------------------------------------------- |
| K0     | stays  | Write it down where it will complain when it goes stale: an assertion in the pipeline beats a sentence in a README, and both beat a fact in your head. |
| K1     | K0     | Look. Profile the column, plot the distribution, read the data dictionary, ask the person who collected it. The only category you can simply decide to spend money on. |
| K2     | K1     | Exposure to reality, early and repeatedly: run end to end on real data, plot the residuals, show a domain expert, score on a period you did not develop on. You cannot search for these; you can only arrange to be surprised sooner and more cheaply. |
| K3     | K0     | Evidence: a check that could have failed, a plot you actually looked at, a baseline that could have won, a second person who does not share your assumption. |
| K4     | chosen | Name the falsehood, write down where it is load-bearing, know what breaks when it comes due.             |

### K3 is the one to be afraid of

K1 and K2 are honest. K3 is expensive precisely because it costs you nothing at the time — no
question is asked, no check is written, no ticket is filed. You are not looking, because as far as
you know there is nothing to look for.

Data work is unusually good at manufacturing K3, for a structural reason: **the failure mode is a
returned value, not an exception.** A join that silently duplicates rows returns a DataFrame. A
timezone that is off by six hours returns timestamps. A `dropna()` that removes exactly the
interesting cases returns a smaller, cleaner, entirely misleading table. Software that is wrong
tends to stop; analysis that is wrong tends to continue and produce a chart.

The canonical K3 here is **leakage** — a feature that encodes the answer, a split with the same
subject on both sides, a normalization computed before the split, a "time of admission" column that
is really the time of discharge. Leakage does not feel like a mistake; it feels like a good result.
Cross-validation agrees with you and the metric improves. Everything you would normally use to
catch an error is the thing being fooled, which is why leakage is found by reading provenance, not
by reading the score.

Only two things find K3: reality, and someone who does not share your assumption. That is the whole
justification for scoring on a period you did not develop on, for plotting instead of summarizing,
for having a second person review the *data handling* rather than the model code, and for the rule
that **a result too good for the problem is a bug report until proven otherwise.** "The AUC is
0.97" is K3 until you have traced one prediction back to the rows that produced it.

### K4: the falsehoods we keep on purpose

Every model is a chosen falsehood. George Box wrote the definitive sentence about K4 in 1976 —
*all models are wrong, some are useful* — and the half that gets repeated is not the operative one.
The operative half is: **wrong in a specific, nameable direction, and you should be able to say
which.**

A short catalogue, every entry false and every entry in use:

- The rows are independent. (They share a sensor, a day, a household, an author.)
- The sample represents the population. (It represents whoever was easy to measure.)
- The past distribution is the future distribution. (Stationarity is a hope with a p-value.)
- The label is the truth. (The label is what a tired person clicked, under instructions from 2019.)
- Missing is missing at random. (A river gauge is most likely to fail during a flood.)
- Time is a line of equal-length days. (Two days a year are 23 and 25 hours long — see below.)
- De-identified means anonymous. (It means nobody has bothered yet.)

The work is not avoiding these — you cannot analyze anything without them. It is choosing them
deliberately, writing them down, and knowing the blast radius when one comes due. An assumption
leaks exactly where it was load-bearing: i.i.d. fails and your intervals are too narrow;
stationarity fails and your backtest was fiction. **A K4 you have chosen is an asset; the same
falsehood held unknowingly is K3** — and the distance between them is one written sentence.

---

## The search is part of the result

This is the section with no counterpart in software engineering, and it is the one that makes data
science its own discipline rather than a domain of programming.

In software, searching is free. Try forty implementations, keep the one that passes the tests, and
you have forty dead branches and one correct program. The search left no residue.

In data analysis, searching contaminates. Try forty features, forty model classes, forty subgroups,
or forty outlier rules, keep the one that looked best, and *the thing you kept was selected for
looking good* — some of which was noise. You have not found an effect; you have run a tournament
and crowned the luckiest contestant. A result is real to the degree it would have survived being
the only thing you tried.

**Your hyperparameter search is an adversary you hired.** It is tireless, it has no stake in the
truth, and it is optimizing against precisely the measurement you intend to trust. Give it enough
freedom and it will find your leakage for you and hand it back as a win.

Three practical consequences:

- **Write the question and the analysis plan down before you look at the outcome.** Not as
  ceremony — as a record of how many degrees of freedom you actually had. The plan need not be
  right; it needs to exist and be dated. Departing from it is normal. Departing from it silently
  is the problem.
- **Count your looks, and say the number.** "We tried one model" and "we tried sixty" are different
  claims about the same coefficient, and the second one is almost never reported.
- **An analysis that changes no decision is a hobby**, and should be budgeted as one. Before
  running it, ask what you would do differently if the answer came out the opposite way. If the
  answer is "nothing," you have learned something valuable for free.

### A point estimate is half a result

A number without an interval is not more certain than one with an interval; it is equally uncertain
and less honest. The variance did not go away because you failed to compute it.

This matters most where it is least often done: on the metric in the slide. A model that scores
0.84 against one that scores 0.82 is not better if the difference is inside the noise of a
1,200-row test set. Reporting the two digits without the spread is how a coin flip becomes a
roadmap.

And **big *n* does not rescue a biased sample; it disguises it.** As the sample grows, variance
shrinks and bias does not, so a large biased sample converges confidently on the wrong number. The
error bar gets tighter around a value that was never right. This is the single most counterintuitive
fact in applied statistics and the reason "we have millions of rows" is not an answer to "who is
missing from the rows?"

### The holdout is a consumable

You cannot un-see the test set. There is no `git checkout` for your own memory.

Each time you evaluate on the holdout and then change something in response, a little of its value
transfers into your model by way of your judgment. Do that twenty times and you have a validation
set wearing a test set's name. The set is not corrupted by being touched — it is corrupted by being
touched and *reacted to*.

This is data science's mask set and wind tunnel: a test with a real, spendable cost in a field
where nearly every other test is free, spent by a mechanism — your own updated beliefs — that
leaves no trace in git.

---

## Time

Tie a string to a rat that has learned one side of the cage is electrified, and measure how hard it
pulls away as it is drawn toward that side. The pull is not linear. It is nearly flat far out and
rises steeply as the distance closes — an *avoidance gradient*, roughly `1/x` in shape.

Deadlines do this to people. The month before the presentation feels like nothing; the last week is
unbearable. The exact curve is a metaphor, not a measurement, but the shape is the part that
matters, and it has a vicious property: **the spike arrives exactly when the project can least
afford the behavior it produces.** In data work that behavior is specific and recognizable: one
more peek at the test set, one more subgroup where the effect is significant, one more outlier rule
that helps, the sanity plot skipped, the null quietly not mentioned. The pressure to *find
something* is this field's characteristic deadline pathology, and it never feels like cheating
while it is happening. It feels like trying harder.

The response is not willpower. It is to change the terrain.

- **Remove the danger.** If re-running the whole analysis from raw data is one command and a few
  minutes, "don't touch it, it works" stops being the safe move. A pipeline nobody dares re-run has
  already failed; you just don't know when.
- **Build the bridge.** A thin end-to-end slice — fetch one gauge, derive one feature, compare
  against a constant baseline, produce the actual chart someone will look at — built on day one and
  then thickened. The alternative, "clean all the data first, then model," is a horizontal layer,
  and horizontal layers all finish at the same time: never.
- **Put small fences along the way.** A baseline actually beaten. A plot a domain expert actually
  objected to. A pipeline run from a cold cache that exited zero. A demo of the current answer,
  however bad. A status meeting is not a fence — it discharges no fear, because nothing was proved.
  Neither is a notebook cell that ran.
- **Keep slack.** K2 in data work is not a risk, it is a certainty, and it usually arrives as a
  sentence: *that column means something different before 2019*. A plan at full utilization has no
  budget line for that sentence.
- **Estimate the category, not the task.** "Two days to clean this dataset" is a K0 statement about
  work that is K2 by construction — you cannot estimate the time to discover things you don't know
  are there. Cleaning gets time-boxed, not estimated. Modeling from a known-good feature table
  estimates fine. Say which kind you are handing over.
- **Bad news early is a gift; bad news late is a betrayal.** "The effect isn't there" in week two is
  a finding, and a cheap one. The same sentence in week eleven is a crisis, and the pressure of that
  crisis is what turns an honest null into a tortured positive. Report nulls the same week you find
  them, with the same tone you'd use for a win.

---

## The cost of a test changes everything

Software engineering's founding economic fact is that its tests can be free. Data science inherits
that for its *code* and emphatically does not inherit it for its *evidence*. Both regimes live in
the same afternoon:

| Practically free                        | Expensive                          | One-way                                   |
| --------------------------------------- | ---------------------------------- | ------------------------------------------ |
| Re-run a transform on 1,000 rows         | A full training run                | Looking at the holdout                     |
| Plot a distribution                      | A labeling campaign                | Publishing a number someone acts on        |
| Swap a model class                       | Six weeks of A/B traffic           | Deploying a model that changes its own inputs |
| Try another feature                      | An hour of a domain expert's time  | A survey you can field once                |

Three things follow that are usually left out.

**1. It is per decision, not per project.** Run waterfall around the expensive and irreversible
ones — think it through, review it, get it right the first time. The metric definition, the split
strategy, the labeling scheme, the unit of analysis, the question itself: these are cheap to decide
carefully now and cost a re-analysis to change later. Run agile around the cheap ones — feature
code, model class, plot styling, anything you can undo by re-running. Methodology is a function of
the cost of being wrong once, and that cost can change twice in an afternoon.

**2. The cost of a test is designed, not given.** Lowering it is ordinary work with a known toolkit:
pure functions over frames instead of one long stateful notebook; a tiny fixture dataset committed
with answers worked out by hand; seeds that are fixed *and recorded*; one command back to raw;
assertions on the invariants that joins and filters break — row counts, key uniqueness, monotone
index, units, plausible ranges; and caching that records *when* and *from where*, so it is a
speedup rather than a time machine. **Lowering the cost of checking a result is often the
highest-leverage work available, because it multiplies against every future question.** The inverse
is diagnostic: *if a result is hard to check, that is information about the analysis, not about
checking.*

**3. Checking is one feedback loop among several.** Each has a cost, a latency, and a fidelity, and
they catch different classes of error:

| Loop                              | Latency   | Catches                                                     |
| --------------------------------- | --------- | ------------------------------------------------------------ |
| Look at the data — head, describe, plot | seconds   | wrong units, impossible values, the file didn't parse         |
| Unit test on transform code       | seconds   | broken logic, an off-by-one in a window                       |
| Fixture pipeline, end to end      | minutes   | wrong assumptions between stages                              |
| Baseline comparison               | minutes   | "my model is worse than the column mean"                      |
| Held-out evaluation               | spendable | overfitting to the validation set                             |
| Human review of the *claim*       | hours     | the metric does not measure the decision                      |
| A domain expert looking at output | days      | "that gauge was under construction in 2018"                   |
| Prospective use                   | live      | drift, feedback loops, and everything you didn't imagine — at the worst possible price |

Push each class of error down to the cheapest, fastest loop that can catch it. But notice that some
errors are only catchable by an expensive loop: no test suite detects "we measured the wrong
thing," and no metric detects "this dataset does not contain the people we care about." Only a
person who knows the domain does.

Two properties of a loop matter more than its coverage:

- **A check that cannot fail proves nothing.** `tests/test_eda.py` asserts that the output is
  non-empty, that a column name starts with `discharge_cfs_`, and that the row count survived. It
  would pass on numerically garbage output. Worse: its 96-sample fixture spans exactly one day, so
  `daily_features` returns **one row**, and the `rolling_anoms` call it then makes produces
  z-scores that are all `NaN` — the assertion `anoms.shape[0] == feats.shape[0]` compares 1 to 1
  and the estimator under test is never actually exercised. And nothing calls `summarize_gaps` at
  all, which is why that function has been returning a negative missing-data percentage on perfect
  input this whole time (see below). Watch a check fail before you trust it.
- **A loop you do not trust is worse than none.** Unseeded randomness trains a team to shrug at a
  moved number, and after that the run that would have caught the real regression has been
  disarmed. So does a cache with no expiry: `load_or_fetch_*` in `usgs.py` returns a Parquet file
  forever, so a pipeline that "ran green this morning" may not have contacted reality in a month.
  That is not a stale-data bug, it is a feedback loop that quietly stopped being one.

---

## Data is an input that lies

Most analyses describe the happy path of a dataset and inherit the rest by accident — whatever
pandas happens to do with a missing value becomes the method, chosen by nobody.

For every input an analysis depends on, four cases need a stated answer: **absent, late, wrong, and
lying.**

**Absent.** Nulls, missing rows, a gauge that stopped reporting. Never ask "how do I fill this"
before "why is it missing," because **missingness is data.** A gap in a river gauge during a flood
is not a random gap; it is the flood. `dropna()` there deletes the event you are studying and hands
you a clean table about ordinary days. Drop, impute, or model the indicator — but on purpose, and
write down which.

**Late.** The row that arrives after your snapshot; the value that gets revised. USGS serves recent
measurements as *provisional and subject to revision*, so a Parquet file cached today pins a number
the official record may contradict next month, and nothing here will ever notice. The general form
is the worst bug in applied machine learning: **train on data as it looks now, score on the past,
and you have used the future.** The defense is knowing, per column, *when its value became
knowable* — a fact about the data-generating process that is almost never in the file.

**Wrong.** Units changed. A sensor drifted. `-999` is a sentinel, not a measurement. The decimal
moved. The timezone is not what the column name says. These are the cheap ones — a range check and
a plot find most of them, which is exactly why the survivors are the ones nobody plotted.

**Lying.** Syntactically perfect and semantically false. A zero meaning "no reading" in a column of
zeros meaning "no flow." An imputed value now indistinguishable from a measured one because someone
filled it three steps upstream. A self-reported field. A default that looks like an observation.
This is the case that gets you, because it passes every schema check you can write; the only thing
that finds it is provenance.

A method that only works when its data behaves is not finished. And the adversary is a special case
of this, not a separate topic: **an adversary is just the unknown that optimizes.** Here it is
rarely a hostile party — it is your own search, your model in production changing the behavior it
measures, or the people being scored learning what the score rewards. Same shape each time:
something is optimizing against your measurement, and your measurement was not built to survive
that.

---

## Reversibility, published numbers, and the installed base

- **Spend deliberation in proportion to reversibility, not to how interesting the decision is.**
  Retraining a model is cheap; another feature is cheap. A number in a deck that someone acted on is
  not — it has an installed base of at least one decision. Most arguments in this field run at the
  wrong intensity for their reversibility: hours on the model class, minutes on the definition of
  the outcome variable.
- **A metric a team has tracked for a year is a promise.** Changing it destroys the comparability
  that was the point of tracking it. You may change it; you may not change it silently. The
  mechanism is ordinary versioning — name the new one, run both a while, say when the old one dies.
- **A model in production changes the data it will be trained on next.** You can roll back the
  model; you cannot roll back the data it generated or the behavior it taught people. Recommenders
  train on clicks they caused; risk scores produce the outcomes they predict by changing who gets
  the loan, the interview, the patrol car. A one-way door that does not look like one at deploy
  time, and is visible only in the next training set.
- The property being engineered is **the cost of the next question**. Anyone can answer the first.
  The design proves itself on the obvious follow-up — which is also when nobody remembers why the
  first answer was shaped that way, so write that down while you still know.

---

## Provenance

Every number in an analysis has an author, and the question that runs through this entire
repository is: **where did this come from, and can I check it later without asking anyone?**

**A number with no lineage is a rumor.** To be checkable it needs: which source, pulled when, at
which revision, through which filters, with which rows dropped and why, under which seed, code
version, and environment. That is not bureaucracy — it is the difference between "the flow was
unusual in March" and "I can show you."

It is the same question at every layer, and noticing that is the point:

- **A value** — measured, imputed, or defaulted? Once all three live in one column they are the
  same value forever.
- **A dataset** — collected by whom, of whom, under what consent, and what was excluded before it
  reached you? The exclusions are invisible in the file and usually the most important thing in it.
- **A label** — **a label is an opinion with a timestamp.** Applied by whom, under what
  instructions, and how often did two labelers disagree? A model is bounded by the agreement rate
  of the labels it learned from, and that number is usually not measured.
- **A result** — which commit, which seed, which environment. This is the layer people skip, and
  it is why a number that reproduced in September stops reproducing in March.

Provenance is the mechanical answer to K3. "I'm sure this is right" is a feeling. "Here is the
command that regenerates it from raw data, and here it is producing the same number" is evidence.

The reference project fails this instructively: `data/*.parquet` records the values and nothing
else — no URL, no fetch time, no revision status. The cache is a set of numbers with their origin
removed, and staleness is only the most visible symptom of that.

---

## Ethics, law, and security are requirements

They are permanent members of the requirement set, and they are the easiest to postpone: no
stakeholder files a ticket for them, they compete against visible results, and their absence looks
exactly like their presence right up until it doesn't.

Two properties make deferring them a mistake rather than a trade-off:

- **Their deadline is set by someone else** — a complaint, an audit, a regulator, a journalist, a
  person who noticed. You do not get to schedule it into next sprint.
- **Violations are the irreversible kind.** Data that leaked cannot be unleaked. A dataset that has
  been re-identified cannot be de-re-identified. A person denied a loan by a model in 2024 is not
  made whole by a better model in 2026.

In practice:

- **Ethics.** The people affected who are not in the room. Data about a river is not data about
  people, and this course's reference project is deliberately the easy case — but the transition is
  invisible in code: `df.groupby("id")` looks the same either way. When rows are people, three
  questions become mandatory. Who is *missing* from this dataset, and what does the model do to
  them? Is the label a proxy for what I care about, or for who has been treated a certain way in
  the past? Can the person scored see or contest the score? Data minimization is the cheapest
  protection that exists — **the safest record is the one you never kept**, and the second safest
  is the aggregate you kept instead of the row.
- **Law.** Mostly about data: what you may collect, what you may use it *for* (the purpose you
  collected it for is often the only purpose you may use it for), how long you may keep it, whom
  you must notify. Also the license of a dataset, the terms of service of an API, and — newly — the
  provenance of training data, including for a model you merely fine-tuned. USGS Water Services is
  public-domain and requires no key, which is exactly why nobody will learn any of this from it
  unless told.
- **Security.** The threat model of a data system is not the threat model of a web app. A trained
  model can leak its training data — membership inference tells an attacker whether a specific
  person was in the training set, which is a disclosure even when no row is returned. Training data
  can be poisoned by anyone who can write to your inputs. And re-identification is the standing
  refutation of the most popular K4 in the field: Sweeney's classic result is that ZIP code, birth
  date, and sex alone uniquely identify the large majority of the US population. "We removed the
  names" is a sentence about names.

**The cheapest moment to satisfy all three is while the question is still soft.** After that you are
not adding a requirement, you are re-running everything.

---

## People are part of the system

- **The deliverable is not the notebook.** It is the claim, plus the ability of someone else to
  reproduce it, challenge it, and update it next quarter. "It ran in a kernel I have since
  restarted" is a claim about a kernel. A notebook is an excellent instrument and a terrible
  artifact: it records the cells, not the order you ran them in, and the order is the program.
- **The analysis will resemble the organization that produced it**, including its metric
  definitions. Whoever owns the pipeline owns the definition, and whoever owns the definition owns
  the conclusion. If that is going to happen anyway, choose the structure on purpose.
- **Coordination cost grows faster than the team**, with a data-specific accelerant: two people
  cleaning the same dataset produce three datasets.
- **Write down what you tried that did not work.** The cheapest documentation in a data project and
  the one nobody writes. Without it the next person — often you, in March — re-runs the same dead
  end, and the count of things tried, which is part of the result, is lost with it.
- **Maintenance is most of the total cost.** A model is a perishable good with no expiry date
  printed on it: the world moves, columns change meaning, and nothing announces it. Someone has to
  own the question of whether last year's model is still true, and that job is invisible until it
  isn't.
- **Distribute discomfort deliberately and visibly** — on-call, review load, the tedious labeling,
  the meeting where you report the null. Burnout is a systems failure with a schedule, and it shows
  up as attrition, which in data work is the uncontrolled deletion of the only copy of why the
  column is filtered that way.

---

## Working with agents

An agent is an extremely fast analyst with no stake in the outcome. It moves the economics of this
discipline in exactly one direction: **the cost of producing an analysis has fallen much faster than
the cost of knowing that the analysis is right.** Everything scarce therefore migrates to the second
half — the question, the data's provenance, the checks, the review, the ownership.

In the taxonomy, an agent is a K3 factory, and data work is the worst possible place to install
one. Fluent, confident, plausible, and occasionally wrong is the precise shape of erroneous
certainty — and here the wrongness does not raise. It returns a DataFrame. **Code that throws is
safe. Code that returns a number is not.** An agent will merge on the wrong key, silently triple
your rows, and report an improved metric, and every artifact you would use to notice looks normal.

That is not an argument against using agents. It is an argument about where to spend what they
save.

- **Spend the speed on lowering the cost of checking** — fixtures with hand-computed answers, row
  count and uniqueness assertions around every join, range checks, a golden-output test on a frozen
  sample, the boring second test case. That work multiplies. More models do not.
- **Ask for the diff in the numbers, not just the diff in the code.** A refactor that "shouldn't
  change anything" is a hypothesis, testable in ten seconds against a fixture.
- **Point review capacity at the data handling** — joins, filters, splits, fills — not at the model
  code. That is where the K3 lives, and where reading is slowest.
- **Never let confidence substitute for a look at the data.** "This should work" is K3 by
  construction, and so is a summary statistic offered in place of a plot.
- **Delegation is not abdication.** You present it, so you own it — and if you cannot explain why
  the number is what it is, you cannot defend it, update it next quarter, or notice when it goes
  wrong. An analysis you cannot explain is a liability regardless of the metric.

---

## Where this shows up in `colorado_river/`

The reference project is a small, real, end-to-end pipeline — remote API to local cache to features
to dashboard — and it contains genuine instances of most of the above, left in place deliberately.
Each row below was verified by running the code, not by reading it.

| Idea                              | Where it is concrete                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| The failure mode is a return value | 17 `except Exception:` blocks across `app.py`, `px.py`, `usgs.py`; four of them (`app.py:63, 70, 90, 103`) swallow silently. A USGS outage is currently indistinguishable from a quiet day. |
| K4 in a comment                   | `eda.py:50` — *"Normalize to naive UTC for delta math (ignore DST complexities here)"*. A named, chosen falsehood. This is the good case. |
| The same K4 held unknowingly (K3) | `app.py:155,159` calls `to_local()` first, so `summarize_gaps` receives tz-*naive* Denver time and the guard on `eda.py:51` never fires. Across the spring-forward boundary a perfect 15-minute series reports `max_gap_sec = 4500` — a 75-minute outage that did not happen. Across fall-back, one step is **negative**. |
| Two definitions of "day"          | `daily_features` (`app.py:298`) resamples the *UTC* frame, while the IV chart shows Denver wall clock. The dashboard's "daily" boxes start at 17:00 or 18:00 the previous evening. Both are on screen at once. |
| A check that cannot fail          | `tests/test_eda.py` asserts non-emptiness and shape. Nothing calls `summarize_gaps`, so `pct_missing_vs_15min` has been returning **−1.05% on gapless input** (an off-by-one: `n` samples span `n−1` intervals). A percentage that can be negative is a check nobody ran. |
| An estimator that cannot fail     | `rolling_anoms` computes `z = (x − mean)/std` over a window that **includes x**. A spike therefore inflates its own baseline. With the app's default `window=30`, the score is mathematically capped at `29/√30 ≈ 5.295`: a 2× spike and a 10⁹× spike both score 5.2947. The anomaly detector's output is a constant. |
| Late data, pinned                 | `load_or_fetch_*` in `usgs.py` caches forever with no TTL and no refresh. USGS values are provisional and get revised; the Parquet file will never learn. |
| Provenance removed                | `data/*.parquet` stores values with no source URL, no fetch time, no revision status. |
| Wrong clock, recorded             | `app.py:86,97` stamp debug snapshots with naive `datetime.now()` while the data inside are UTC. Two snapshots across a DST boundary sort wrongly. Ruff's `DTZ` rules catch this and are documented as off in `ruff.toml`. |
| Fences, not heroics               | `pixi run test`, `pixi run lint`, `pixi run clean` — one command back to a known state. |

Every one of those is a lesson rather than an oversight, and the order they are listed in is roughly
the order of how much they would cost you if you did not know.

---

## If you want the longer arguments

- George Box, "Science and Statistics" (1976) — where *all models are wrong, some are useful* comes
  from, and it is an essay about K4, not a slogan.
- John Tukey, "The Future of Data Analysis" (1962) — the case that data analysis is a science rather
  than a branch of mathematics, sixty years before it was fashionable.
- Andrew Gelman and Eric Loken, "The Garden of Forking Paths" — the search is part of the result,
  even when you only ran one analysis.
- Xiao-Li Meng, "Statistical Paradises and Paradoxes in Big Data" (2018) — why a tiny selection bias
  beats an enormous sample, with the arithmetic.
- Sayash Kapoor and Arvind Narayanan, "Leakage and the Reproducibility Crisis in ML-based Science" —
  a survey of how routinely the canonical K3 gets through peer review.
- D. Sculley et al., "Hidden Technical Debt in Machine Learning Systems" (2015) — the diagram where
  the ML code is the small box.
- Timnit Gebru et al., "Datasheets for Datasets," and Margaret Mitchell et al., "Model Cards for
  Model Reporting" — provenance, made into a form you can fill out.
- Cathy O'Neil, *Weapons of Math Destruction* — feedback loops and the people not in the room.
- Richard Cook, "How Complex Systems Fail" — eighteen paragraphs, and still the best return per page
  in either course.
