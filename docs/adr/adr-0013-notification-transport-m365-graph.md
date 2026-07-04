---
schema_version: '1.1'
id: 'adr-0013-hw-radar-notification-transport-m365-graph'
title: 'ADR 0013: Notification transport — reuse the existing M365 Graph send path'
description: 'Send v1 alert email through the homelab''s existing Microsoft Graph → Microsoft 365 path (branded l3digital.net sender, zero marginal cost, credentials already at OpenBao secret/apps/microsoft365), with AgentMail free as an independent fallback; Postmark-primary/SES-fallback is retained only as the documented paid-upgrade path.'
doc_type: 'adr'
status: 'active'
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'email'
  - 'notifications'
  - 'deliverability'
  - 'microsoft-graph'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/resolved-questions.md'
  - 'docs/research/free-outbound-email-path-for-low-volume-alerts.md'
  - 'docs/research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'public'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0013: Notification transport — reuse the existing M365 Graph send path

MADR status: **accepted**.

## Context and Problem Statement

Deal alerts are the product's payload; they **must not spam-folder**. The spec standardized on **AgentMail**, and earlier research ([`choosing-an-outbound-email-path`](../research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md)) recommended a paid transactional provider (Postmark primary, SES fallback). But the owner set a hard constraint: **no paid email service right now** — the v1 transport must be free. Two facts frame the choice: the deploy host (Hetzner) **blocks outbound ports 25/465**, so self-hosted SMTP is out; and hosted free tiers have proven **volatile** (SendGrid killed its free plan in 2025; MailerSend cut its free allowance 83% in Oct 2025). Volume is tiny: well under 100 emails/day to effectively one recipient.

Research [`free-outbound-email-path-for-low-volume-alerts`](../research/free-outbound-email-path-for-low-volume-alerts.md) surveyed the free options (resolved-questions.md OQ13).

## Considered Options

- **Option 1 — Reuse the existing Microsoft Graph → Microsoft 365 send path** already used for other homelab service alerts. (chosen)
- **Option 2 — AgentMail free tier** (`@agentmail.to`, unbranded; 100/day, 3,000/mo).
- **Option 3 — A hosted transactional provider** (Postmark primary / SES fallback).
- **Option 4 — A different hosted free tier** (Brevo, MailerSend, SMTP2GO, Resend, …).

## Decision Outcome

Chosen option: **Option 1**, with **Option 2 (AgentMail free) as an independent fallback channel.**

The M365 Graph path is the strongest *free* option because it is infrastructure the owner **already pays for and already operates**: alerts send via Microsoft Graph `sendMail` through the existing M365 tenant, from a **branded `@l3digital.net` sender**, with credentials already provisioned at OpenBao `secret/apps/microsoft365`. It gives **zero marginal cost**, **branded custom-domain** sending (SPF/DKIM/DMARC already aligned for the domain), **high, established deliverability** (the M365 recipient limits dwarf this workload), and — decisively — **no dependence on any third-party free-tier policy** that could be cut or retired.

**AgentMail free** is retained as a decoupled fallback: unbranded `@agentmail.to`, no custom-domain setup, caps (100/day · 3,000/mo) 30–100× this workload. Useful if the Graph path is unavailable.

Option 3 (Postmark/SES) was rejected **for v1 only** on the no-cost constraint — it is **retained as the documented paid-upgrade path** if deliverability ever proves a problem. Option 4 was rejected: adopting a *new* volatile free tier trades away the very reliability that makes Option 1 attractive, for a service the owner does not already run.

### Consequences

- **Good** — free, branded, high-deliverability, and reuses an operated system; nothing new to sign up for or keep patched.
- **Good** — the alert-logic layer (dedup/debounce/digest, hysteresis, the post-alert state machine) is transport-agnostic and already settled; this ADR only fixes the send mechanism.
- **Bad (accepted)** — couples alerting to the M365 tenant's availability and policy; the AgentMail fallback mitigates a total outage.
- **Operational** — keep the gap-#6 **email-delivery confirmation** (an operator-side signal that a send actually left the box) regardless of provider. Graph credentials are M365-only and referenced, never committed.
- **Deferred** — if branded transactional deliverability ever needs a dedicated provider, the paid path (Postmark/SES) is pre-researched and one ADR away.

### Confirmation

Implementation confirmation (MS-4): a single qualifying price drop sends **exactly one** email via the Graph path from the branded sender; a send failure is **detectably surfaced** (delivery-confirmation signal); the AgentMail fallback can be exercised on demand.

## More Information

- **Supersedes** the spec's AgentMail-primary lean and the earlier Postmark-primary research recommendation **for the free v1 case** (both retained as fallback/upgrade paths, not deleted).
- **M365 Graph reference:** `~/projects/agent-configs/global/claude/context/m365-graph.md` (read when wiring mail); credentials at OpenBao `secret/apps/microsoft365`.
- **Findings:** resolved-questions.md **OQ13**; research [`free-outbound-email-path`](../research/free-outbound-email-path-for-low-volume-alerts.md) + [`choosing-an-outbound-email-path`](../research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md).
