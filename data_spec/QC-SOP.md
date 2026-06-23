# QC-SOP — Probe Quality-Control Standard Operating Procedure (synthetic)

> **Synthetic** SOP corpus for RAG. `rag.py` chunks + indexes this; the agent
> cites a clause as `[N]`. Clauses are keyed to parameters/failure modes so a
> detector breach maps to the governing clause, and each disposition rule states
> an explicit **HOLD/RELEASE** action and a **reason** (so a cited rationale is
> grounded, not invented). Thresholds intentionally mirror `detector.py`.

## 1. Scope
This procedure governs disposition of wafer probe lots against parametric QC
limits set by Product Engineering (PE) and customers. It applies to every lot
after probe test and before the next process step.

## 2. Definitions
- **HOLD** — the lot is quarantined pending engineering review; it does not move.
- **RELEASE** — the lot passes QC and proceeds to the next step.
- **Breach** — a parameter violates a rule in §3 (an out-of-limit fraction, a
  mean shift, or a within-lot drift).
- **Disposition** — the recorded HOLD/RELEASE decision plus its cited reason and
  the named approver.

## 3. Parametric disposition rules
**3.1 Vt upper-limit excursion (tail).** If more than **1%** of dies exceed the
Vt upper spec limit (**0.53 V**), **HOLD** the lot for parametric review. A Vt
tail indicates a threshold/implant excursion that risks functional failure at the
customer.

**3.2 Idd uniform shift.** If the lot-mean Idd is shifted from nominal by more
than **0.75σ** (a uniform increase across the lot), **HOLD**. A uniform Idd shift
indicates a power/process excursion affecting the whole lot.

**3.3 Idd within-lot drift.** If the per-wafer mean Idd drifts across the lot
(range of wafer means greater than **1.5σ**), **HOLD** and raise a **tool-drift**
flag to equipment engineering. Drift across the wafer sequence indicates probe
or process tool degradation during the run.

**3.4 Leakage edge pattern.** If more than **1%** of dies exceed the leakage spec
limit (**2.46 nA**), and the excursion concentrates on **edge dies** (radius
r/R > 0.80), **HOLD**. Edge-localized leakage indicates a seal/moisture or
edge-process defect.

**3.5 Multiple breaches.** A lot breaching two or more parameters is **HOLD** and
escalated directly to PE (see §6).

## 4. Release rule
**4.1** A lot with **no breached parameter** under §3 is **RELEASED**. Absence of
a breach is a sufficient basis for release; no further justification is required.

## 5. Approval and override
**5.1** Every disposition requires a **named approver**. The drafted
recommendation is advisory until a human approves it.
**5.2** A human may **override** the drafted recommendation; the override and its
**reason** are recorded in the audit log. An override never bypasses §5.1.

## 6. Escalation
**6.1** A lot that is HOLD on a repeat basis, or that breaches multiple parameters
(§3.5), is escalated to PE for engineering disposition and root-cause review.
