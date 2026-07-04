---
schema_version: '1.1'
id: free-outbound-email-path-for-low-volume-alerts
title: Free Outbound-Email Path for a Low-Volume Alerting System
description: Free-tier-only follow-up on outbound email for hw-radar's alert channel — recommends reusing the existing Microsoft Graph API / M365 tenant send path as primary, AgentMail's free @agentmail.to tier as an independent fallback, and documents Postmark/SES as the future paid upgrade path.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- email-deliverability
- transactional-email
- free-tier
- microsoft-graph
- agentmail
- dkim
- spf-dmarc
- alerting
aliases: []
related:
- choosing-an-outbound-email-path-for-a-low-volume-alerting-system
source: []
confidence: high
visibility: private
license: null
---

# Free Outbound-Email Path for a Low-Volume Alerting System

## Bottom line

**Recommendation:** send hw-radar's alerts through the **existing Microsoft Graph API / Microsoft 365 tenant path** the owner already operates for other homelab alerting (the `graph-sendmail` pattern) — **not** a new hosted email vendor at all. It is the only option on this list with **zero marginal cost, zero new signup, zero new DNS/authentication work, and an already-proven delivery track record on an already-authenticated business domain**. Every hosted "free tier" evaluated below is free only up to a cap that has proven volatile in the last 12 months (SendGrid's free tier was killed outright in 2025; MailerSend's was cut 83% in October 2025), which is a real risk for a "must-not-miss" channel that is otherwise free forever.

**Runner-up (independent fallback):** **AgentMail's free tier** (`@agentmail.to`, unbranded sender). It is the cleanest hosted fallback because it requires **no custom-domain DNS work at all** (a hard requirement satisfied trivially, since the task explicitly allows an unbranded sender), its 100 emails/day and 3,000 emails/month caps are roughly **30-100x** this workload's volume, and it was already vetted for API/webhook fit in the prior (paid-tier) report. Use it only as a secondary channel that fires if the Graph API path is unavailable, not as the primary.

This report **supersedes the prior report's recommendation only for the free-tier v1 case** — Postmark-primary/SES-fallback remains the documented **paid upgrade path** once the owner is willing to spend money on email (see [`choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md`](choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md)).

## ⚠ Existing solution

> **Microsoft Graph API send path via the owner's existing paid M365 tenant** — the homelab already sends automated alerts for other services through this exact mechanism (`graph-sendmail` on the Hetzner host, sending as `automail@l3digital.net`, credentials at OpenBao `secret/apps/microsoft365`). This is not a new build; hw-radar can plug into the same pattern rather than integrating a new third-party vendor. Review this before adding any new email dependency.

## Why the existing M365/Graph path wins

The task's own constraints point directly at this option once it is weighed seriously rather than as an afterthought:

- **Zero marginal cost.** The tenant is already paid for and used for mail today; adding one more low-volume automated sender costs nothing extra. Every other option on this list is "free" only up to a cap the provider can (and recently has) changed.
- **Already production, not sandboxed.** Unlike Amazon SES, which starts every new account in a **sandbox limited to verified recipients and 200 messages/24h** until AWS grants production access (approval is not automatic and can take days, with reports of rejection for accounts with limited AWS usage history) `[official]` (<https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html>), the M365 tenant is already a fully live, unrestricted sender.
- **Volume headroom is enormous relative to need.** Exchange Online's per-mailbox limits are **10,000 recipients per 24 hours**, 30 messages/minute via SMTP AUTH `[blog]` (<https://prospeo.io/s/office-365-sending-limits>), and Microsoft Graph's application-level throttling is **10,000 requests per 10 minutes per app** `[official]` (<https://learn.microsoft.com/en-us/graph/throttling-limits>). A tenant-wide external-recipient cap (TERRL) was proposed for 2026 but was **cancelled in January 2026** after customer pushback `[official]` (<https://techcommunity.microsoft.com/blog/exchange/exchange-online-to-introduce-external-recipient-rate-limit/4114733>), so there is no looming tenant-level ceiling to worry about at "well under 100/day, effectively one recipient."
- **Best deliverability evidence of any option here.** The sending domain(s) (`l3digital.net` / `luminous3d.com`) already have a working, multi-service send history and existing DNS presence through the tenant — this is precisely the kind of "reputable traffic history" that Gmail, Yahoo, and Microsoft's own anti-spam guidance treats as a trust signal, and it is a much stronger starting position than any brand-new signup on a hosted free tier.
- **No new attack surface or vendor risk.** No new API key to manage, no new provider ToS to track for policy changes, no new free-tier volume ceiling to monitor.

The only real cost is integration effort: wiring hw-radar's alert stage to call the existing Graph `sendMail` mechanism (new alias such as `alerts@` or reuse of `automail@`, routed into the existing `Monitoring/` mailbox structure) rather than a new library. That is a one-time, low-effort task, not a recurring cost.

## Summary

| Angle          | Sources | Strongest finding |
| -------------- | ------- | ------------------ |
| Official Docs  | 9       | Every hosted provider publishes an explicit free-tier volume cap; M365/Graph limits (10K recipients/day, 10K Graph requests/10min) dwarf this workload. |
| Best Practices | 4       | Shared IP is correct at this volume for any provider; if a custom domain is ever used, start DMARC at `p=none` and tighten later. |
| Footguns       | 6       | Free-tier terms are volatile — SendGrid killed its free plan in 2025 and MailerSend cut its free allowance 83% in Oct 2025 — a real risk for a "must-not-miss" channel. |
| Existing Tools | 8       | AgentMail free (100/day, 3,000/mo, no domain needed) is the cleanest hosted fallback; Brevo free (300/day) is the best hosted option if a branded fallback is ever wanted without paying. |
| Security       | 5       | SES sandbox blocks unverified recipients until approval; Gmail/Workspace SMTP is not intended for automated/transactional sending and risks account suspension. |
| Recent Changes | 4       | SendGrid free tier retired May–Jul 2025; MailerSend free tier cut Oct 2025; Exchange Online's proposed external-recipient cap (TERRL) was cancelled Jan 2026. |

**Queries:** 12 (standard depth, plus 4 targeted cross-checks) · **Results parsed:** ~70 · **Deep reads:** 0 (Tavily extract unavailable this session; sufficient signal from search snippets across official + independent sources) · **Follow-up pass:** no (all six angles cleared the 2-source bar on the first sweep)

## Official Documentation

- **Microsoft Graph throttling limits**: general application limit is 10,000 requests per 10 minutes; per-user/per-mailbox limits vary by operation `[official]` (<https://learn.microsoft.com/en-us/graph/throttling-limits>).
- **AgentMail pricing**: Free tier = 3 inboxes, 3,000 emails/month, 100 emails/day, `@agentmail.to` sender only; custom domains require the Developer plan ($20/mo) or above `[official]` (<https://www.agentmail.to/pricing>; rate limits detail at <https://www.agentmail.to/docs/knowledge-base/rate-limits>). This reconfirms the prior report's figures as still current on 2026-07-04.
- **Resend account quotas**: Free tier = 100 emails/day, 3,000/month, **1 verified domain included** (unlike AgentMail, Resend's free tier does allow a custom-domain identity) `[official]` (<https://resend.com/docs/knowledge-base/account-quotas-and-limits>; free-tier history at <https://resend.com/blog/new-free-tier>).
- **Brevo free plan**: 300 emails/day, no expiry, full transactional API/SMTP/webhooks included, domain authentication (SPF/DKIM/DMARC) configurable `[official]` (<https://help.brevo.com/hc/en-us/articles/208580669>, <https://help.brevo.com/hc/en-us/articles/208589409>).
- **MailerSend pricing**: Free tier is **500 emails/month, 100/day, 1 domain** — reduced from 3,000/month in October 2025 `[official]` (<https://www.mailersend.com/pricing>, <https://www.mailersend.com/help/plans-features-and-limits>).
- **SMTP2GO free plan**: 1,000 emails/month, 200/day, 25/hour (hourly cap lifted once a sender domain is verified), no time limit `[official]` (<https://support.smtp2go.com/hc/en-gb/articles/223087947-Free-Plan>).
- **Mailjet free plan**: 6,000 emails/month, 200/day `[official]` (<https://documentation.mailjet.com/hc/en-us/articles/8625025643803>, <https://documentation.mailjet.com/hc/en-us/articles/360043048393>).
- **Amazon SES pricing/quotas**: sandbox default is 200 msgs/24h to verified recipients only; the free-tier allowance is 3,000 message charges/month for the **first 12 months only**, after which normal $0.10/1,000 billing applies `[official]` (<https://aws.amazon.com/ses/pricing/>, <https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html>).
- **Google Workspace Gmail sending limits**: free Gmail = 500 recipients/day; Google Workspace = 2,000/day (10,000/day via SMTP relay with admin config) `[official]` (<https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace>).

## Best Practices

- **Shared IP is correct at this volume for any provider.** This holds for Brevo, SES, Postmark, and AgentMail alike (per the prior report); nothing about the free-tier decision changes that guidance — dedicated IPs need sustained volume this workload will never reach `[community]` (captaindns technical guide, <https://www.captaindns.com/en/blog/brevo-transactional-email-technical-guide>).
- **If a custom domain is ever used (now or on a future paid tier), start DMARC at `p=none`** with aggregate reporting, then tighten to `quarantine`/`reject` once SPF/DKIM alignment is confirmed — the same guidance from the prior report `[official/community, carried over]`.
- **Prefer official over community pricing pages for volume figures.** Third-party "pricing 2026" review sites frequently lag or misstate current free-tier numbers (e.g., several blog posts still cite AgentMail or MailerSend figures that were superseded); always confirm against the provider's own pricing/docs page before relying on a number, as done here.
- **Treat free-tier caps as fragile, not durable.** Community and official sources both show 2025-2026 free-tier terms shrinking industry-wide (SendGrid, MailerSend, Mailchimp) — plan the alerting integration so swapping the sender path later requires touching one function, not the whole pipeline.

## Footguns and Gotchas

- **Free-tier terms are actively shrinking industry-wide.** SendGrid retired its free plan entirely (announced, then enforced starting **May 27, 2025**, with existing users cut off by **July 26, 2025**) — corroborated by Twilio's own changelog and multiple independent reports `[official]` (<https://www.twilio.com/en-us/changelog/sendgrid-free-plan>) and `[community]` (Reddit r/SendGrid, <https://www.reddit.com/r/SendGrid/comments/1kwpxde/>).
- **MailerSend cut its free allowance 83% (3,000 → 500 emails/month) in October 2025** — corroborated across the official pricing page and two independent trackers `[official]` (<https://www.mailersend.com/pricing>) and `[blog]` (<https://blog.groupmail.io/mailerlite-free-plan-limits/>, <https://www.emailtooltester.com/en/blog/free-smtp-servers/>). This is the single strongest argument against betting v1 on any hosted free tier without a fallback plan.
- **Amazon SES's free tier is not free forever and not frictionless.** New accounts start in a sandbox limited to verified recipients only, production-access approval takes 1-3 business days and is not guaranteed, and the free allowance (3,000 messages/month) expires after 12 months `[official]` (<https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html>) — corroborated by two independent cost breakdowns `[blog]` (<https://www.saaspricepulse.com/tools/amazon-ses>, <https://www.mailblast.io/blog/ses/amazon-ses-pricing>).
- **Gmail/Google Workspace SMTP is not intended for automated/transactional sending and risks account suspension** if treated as such, independent of whether the daily cap (500/2,000) is technically sufficient — corroborated across three independent guides `[blog]` (<https://mailflowauthority.com/email-infrastructure/gmail-smtp-server-settings>, <https://serversmtp.com/limits-of-gmail-smtp-server/>, <https://prospeo.io/s/gmail-smtp-limits>).
- **AgentMail's free tier does not support a custom domain** — the Developer plan ($20/mo) is required for that; free tier is `@agentmail.to` only `[official]` (<https://www.agentmail.to/pricing>), corroborated by an independent review `[blog]` (<https://www.eesel.ai/blog/agentmail-pricing>). This is fine for hw-radar's stated constraint (unbranded sender acceptable) but must not be assumed to be upgradeable for free later.
- **Some free-tier providers reject overage rather than queue it.** SMTP2GO explicitly states that once the monthly free cap is hit, further sends are **rejected, not queued** `[official]` (<https://support.smtp2go.com/hc/en-gb/articles/223087947-Free-Plan>) — a silent-failure risk if a burst of listings triggers more alerts than expected in a given day/month.

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| ---- | ----------- | ---- | ----------------- |
| **Microsoft Graph API / existing M365 tenant** (`graph-sendmail`) | Actively maintained in-house, already in production for other alerts | internal (`~/projects/homelab/scripts/graph-inbox.py` + sibling `graph-sendmail`) | **Best fit** — zero cost, zero new setup, proven track record |
| AgentMail (free) | Active, well-funded (YC S25, $6M seed Mar 2026) | <https://www.agentmail.to/pricing> | Good fallback — no domain needed, ample headroom, but thinner public deliverability track record for pure transactional alerts |
| Brevo (free) | Long-established (formerly Sendinblue) | <https://www.brevo.com/pricing/> | Good fallback if a branded/custom-domain free option is ever wanted; 300/day cap, full transactional API + SPF/DKIM/DMARC on free |
| Resend (free) | Active, developer-focused | <https://resend.com/pricing> | Viable; free tier includes 1 custom domain, but 100/day cap and single-domain limit are tighter than Brevo |
| Mailjet (free) | Long-established | <https://www.mailjet.com/pricing/> | Viable; 200/day, 6,000/month is generous, but weaker developer-experience reputation than Resend/Brevo |
| MailerSend (free) | Active, but free tier shrunk 83% in Oct 2025 | <https://www.mailersend.com/pricing> | Workable at 500/month, 100/day, but the recent cut signals policy instability |
| SMTP2GO (free) | Active, "free forever" positioning | <https://www.smtp2go.com/pricing/> | Workable (1,000/mo, 200/day) but rejects (does not queue) overage |
| Amazon SES | AWS-maintained | <https://aws.amazon.com/ses/pricing/> | Not the best free fit — sandbox approval friction, 12-month-only free allowance; better as the **paid** fallback (per prior report) |
| Gmail / Google Workspace SMTP | Google-maintained | <https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace> | Not recommended — not built for automated/transactional sending, suspension risk |

## Security and Compatibility

- **Hetzner blocks outbound ports 25/465** on cloud VMs (per the prior report, unchanged) — confirms direct/self-hosted SMTP remains out of scope; all viable paths here go through an API/HTTPS or authenticated submission endpoint (Graph API's HTTPS `sendMail`, or a provider's REST/SMTP-submission service), never raw port-25 delivery.
- **SES sandbox is a hard gate**, not a soft default — new accounts cannot send to unverified recipients at all until AWS grants production access `[official]` (<https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html>).
- **Exchange Online's proposed tenant-wide external-recipient limit (TERRL) was cancelled in January 2026** after being announced for phased 2026 rollout — Microsoft confirmed no mailbox-level external-recipient cap will be enforced `[official]` (<https://techcommunity.microsoft.com/blog/exchange/exchange-online-to-introduce-external-recipient-rate-limit/4114733>), corroborated by independent IT press `[community]` (<https://office365itpros.com/2026/01/08/mailbox-external-recipient-rate/>). This removes what would have been the only real ceiling risk for the recommended Graph API path.
- **General deliverability mechanics apply regardless of provider**: SPF, DKIM, and DMARC alignment plus valid reverse DNS are what mailbox providers (Gmail, Yahoo, Microsoft) actually check — carried over unchanged from the prior report, and already satisfied for the M365 tenant's existing domains.

## Recent Changes

- **SendGrid retired its free Email API/Marketing Campaigns plan** (announced ~May 2025, enforced by July 26, 2025) `[official]` (<https://www.twilio.com/en-us/changelog/sendgrid-free-plan>) — the clearest recent signal that hosted free tiers are not a durable long-term bet.
- **MailerSend cut its free tier from 3,000 to 500 emails/month in October 2025** `[official]` (<https://www.mailersend.com/pricing>, corroborated <https://www.emailtooltester.com/en/blog/free-smtp-servers/>).
- **Exchange Online's proposed External Recipient Rate Limit (TERRL/ERR) was announced for 2026 rollout, then cancelled in January 2026** `[official]` (<https://techcommunity.microsoft.com/blog/exchange/exchange-online-to-introduce-external-recipient-rate-limit/4114733>).
- **AWS SES's free tier has been 3,000 messages/month (first 12 months only) since August 2023**, not the older, widely-repeated 62,000/month EC2-hosted figure — several current review sites still cite the outdated number, so always verify against AWS's own pricing page `[official]` (<https://aws.amazon.com/ses/pricing/>).

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Should hw-radar send alerts as a new `alerts@` alias on the tenant, or reuse the existing `automail@l3digital.net` sender used by other homelab services? | Depends on whether the owner wants hw-radar alerts visually distinguishable in the `Monitoring/` mailbox structure; a product/inbox-routing decision, not a research question. |
| 2 | Does the existing app registration's `Mail.ReadWrite` scope cover `sendMail`, or does hw-radar need an additional `Mail.Send` application permission grant? | Not verified in this pass; requires checking the Azure AD app registration's current permission set (a config check, not a search-engine question). |
| 3 | If AgentMail is wired up as the fallback channel, should it be exercised periodically (e.g., a weekly canary alert) to confirm it still works, given it will rarely fire in practice? | An operational/testing-policy decision for hw-radar's alerting design, not something this research settles. |

## Handoff

Persisted at `docs/research/free-outbound-email-path-for-low-volume-alerts.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the Open Questions (alias choice, app-registration scope, fallback-canary policy) into a design conversation.
- `feature-dev:feature-dev` — implement the alert-send stage against the existing Graph API path, with AgentMail free tier as the coded fallback.

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://www.agentmail.to/pricing | Pricing \| AgentMail | 2026 | official |
| https://www.agentmail.to/docs/knowledge-base/rate-limits | What are the rate limits? \| AgentMail | 2026 | official |
| https://www.eesel.ai/blog/agentmail-pricing | AgentMail pricing explained | 2026 | community |
| https://lobstermail.ai/blog/agentmail-pricing-review-2026 | agentmail pricing 2026 review | 2026 | blog |
| https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan | FAQs - Free plan limits | Brevo | 2026 | official |
| https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans | About Brevo's pricing plans | 2026 | official |
| https://www.captaindns.com/en/blog/brevo-transactional-email-technical-guide | Brevo: Technical Guide for Transactional Email and DKIM | 2026 | community |
| https://www.mailersend.com/help/plans-features-and-limits | MailerSend Plans and Limits | 2026 | official |
| https://www.mailersend.com/pricing | MailerSend Pricing | 2026 | official |
| https://blog.groupmail.io/mailerlite-free-plan-limits/ | MailerLite Free Plan 2026 | 2026 | blog |
| https://www.emailtooltester.com/en/blog/free-smtp-servers/ | 12 Best Free SMTP Servers 2026 | 2026 | blog |
| https://support.smtp2go.com/hc/en-gb/articles/223087947-Free-Plan | Free Plan – SMTP2GO Support | 2026 | official |
| https://www.smtp2go.com/pricing/ | SMTP2GO Pricing | 2026 | official |
| https://www.smtp2go.com/blog/sendgrid-has-ended-its-free-plan-we-have-got-you-covered/ | SendGrid Alternative With Free Plan | 2026 | official |
| https://resend.com/docs/knowledge-base/account-quotas-and-limits | Resend account quotas and limits | 2026 | official |
| https://resend.com/blog/new-free-tier | New Free Tier · Resend | 2026 | official |
| https://automationatlas.io/answers/resend-free-tier-explained-2026/ | Resend Free Tier Explained | 2026 | blog |
| https://documentation.mailjet.com/hc/en-us/articles/8625025643803-Mailjet-Subscription-Management | Mailjet Subscription Management | 2026 | official |
| https://documentation.mailjet.com/hc/en-us/articles/360043048393-What-is-this-200-emails-per-day-limit-on-free-accounts | What is this 200/day limit? | Mailjet | 2026 | official |
| https://aws.amazon.com/ses/pricing/ | Amazon SES Pricing | 2026 | official |
| https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html | Managing your Amazon SES sending limits | 2026 | official |
| https://www.saaspricepulse.com/tools/amazon-ses | Amazon SES Pricing 2026: Free Tier Catches | 2026 | blog |
| https://www.mailblast.io/blog/ses/amazon-ses-pricing | Amazon SES Pricing Explained 2026 | 2026 | blog |
| https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace | Gmail sending limits in Google Workspace | 2026 | official |
| https://serversmtp.com/limits-of-gmail-smtp-server/ | Gmail SMTP 2026: Sending Limits | 2026 | blog |
| https://prospeo.io/s/gmail-smtp-limits | Gmail SMTP Limits in 2026 | 2026 | blog |
| https://mailflowauthority.com/email-infrastructure/gmail-smtp-server-settings | Gmail SMTP Server Settings | 2026 | blog |
| https://learn.microsoft.com/en-us/graph/throttling-limits | Microsoft Graph service-specific throttling limits | 2026 | official |
| https://www.unipile.com/microsoft-graph-api-email-integration-guide/ | Microsoft Graph API Email guide | 2026 | community |
| https://techcommunity.microsoft.com/blog/exchange/exchange-online-to-introduce-external-recipient-rate-limit/4114733 | Exchange Online to introduce External Recipient Rate Limit | 2026 | official |
| https://office365itpros.com/2026/01/08/mailbox-external-recipient-rate/ | Exchange Mailbox External Recipient Rate Limit Cancelled | 2026 | community |
| https://prospeo.io/s/office-365-sending-limits | Office 365 Sending Limits in 2026 | 2026 | blog |
| https://www.twilio.com/en-us/changelog/sendgrid-free-plan | Changes coming to SendGrid's Free Plan | 2025 | official |
| https://www.reddit.com/r/SendGrid/comments/1kwpxde/your_free_use_of_sendgrid_ends_on_july_26th_2025/ | Your free use of SendGrid ends | 2025 | community |
| https://dreamlit.ai/blog/best-sendgrid-alternatives | SendGrid Alternatives 2026 | 2026 | blog |
