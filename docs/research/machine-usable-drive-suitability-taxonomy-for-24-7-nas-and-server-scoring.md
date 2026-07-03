---
schema_version: '1.1'
id: machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring
title: Machine-Usable Drive Suitability Taxonomy for 24/7 NAS and Server Scoring
description: A scoring-oriented attribute schema and tier ladder (desktop/NAS/enterprise) for HDDs and SSDs covering CMR vs SMR detection, workload and endurance ratings, power-loss protection, and form factors, plus a model-family-to-tier reference table.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: chris
tags:
- drive-taxonomy
- cmr
- smr
- nas
- enterprise
- dwpd
- tbw
- scoring
aliases: []
related: []
source: []
confidence: high
visibility: private
license: null
---

# Machine-Usable Drive Suitability Taxonomy for 24/7 NAS and Server Scoring

## What your scoring engine should optimize for

For a homelab or small-business buyer who prefers NAS-grade and enterprise drives, the most predictive fields are not raw benchmark throughput. The high-signal fields are market tier, workload rating, warranty, reliability rating, vibration handling, RAID/NAS firmware behavior, recording technology for HDDs, and endurance plus power-loss protection for SSDs. In practical scoring terms, a general-purpose desktop HDD should sit at the bottom of the ladder; NAS and NAS Pro sit in the middle; enterprise and datacenter lines sit at the top. For HDDs, SMR should be treated as a hard reject for normal NAS/RAID use unless the listing is explicitly for archive/sequential-write workloads with SMR-aware software. For SSDs, missing power-loss protection should be a major penalty for write-bearing NAS/server roles, and DRAM-less client SSDs should score below enterprise/NAS SSDs even when headline throughput looks good.

The cleanest implementation is to separate **market tier** from **technical attributes**. A family like WD Red Plus or Seagate IronWolf already encodes a lot of intent, but your engine should still score the specific model’s published claims separately: workload rating, MTBF/AFR, warranty, RV sensors, recording tech, helium/air, PLP, DWPD/TBW, NAND type, and form factor/interface. That protects you from family lines that mix technologies by capacity or revision, which happens most often in desktop lines and occasionally in budget NAS or consumer SSD lines.

## Tier ladder and the concrete spec differences that matter

Across the official product lines reviewed, the tier ladder is real and measurable. Desktop HDDs are positioned for ordinary PC use and shorter warranties. WD Blue 3.5-inch PC HDDs are marketed for “office and web applications” and carry a 2-year limited warranty; the same data sheet also shows that the line mixes CMR and SMR by exact model number. Toshiba’s P300 is likewise positioned for home/office desktop use and carries a 2-year warranty. Neither is sold as a 24/7 NAS platform.

NAS HDDs add continuous-duty positioning, RAID/NAS firmware tuning, and materially higher durability targets. WD Red Plus is explicitly for RAID-optimized NAS systems with up to 8 bays, 180 TB/year workload rating, 1 million hours MTBF, and a 3-year warranty. Seagate IronWolf is rated for 180 TB/year, 1 million hours MTBF, and a 3-year warranty, and Seagate explicitly lists RV sensors on supported models. Toshiba N300 is specified for 24/7 operation, up to 12 bays, 180 TB/year, 1.0 to 1.2 million hours MTTF depending model, RV sensors, and a 3-year warranty, with explicit “error recovery control.”

NAS Pro lines step up again. WD Red Pro is sold for unlimited-bay RAID-optimized NAS systems, 550 TB/year workloads, up to 2.5 million hours MTBF, 5-year warranty, RV sensors, and a multi-axis shock sensor. Seagate IronWolf Pro is similarly called out as all-CMR, 550 TB/year, 2.5 million hours MTBF, 5-year warranty, and RV sensors. These are the best “small-business NAS” defaults when the buyer wants higher confidence without moving fully into datacenter OEM stock.

Enterprise and datacenter HDDs add still more reliability signaling. WD Gold publishes a 5-year warranty, up to 2.5 million hours MTBF, AFR as low as 0.35% on some capacities, dual-sensor rotational-vibration protection, and ArmorCache enterprise power-loss protection on 22 TB and up. Ultrastar DC HC580 publishes 24x7 availability, 2.5 million hours MTBF, 0.35% AFR, 5-year warranty, and ArmorCache enterprise power-loss protection. Toshiba MG Series is explicitly a 24/7 enterprise-capacity line with 550 TB/year workload, 5-year warranty, persistent write cache technology, and rotational-vibration sensors. Current Seagate Exos 24 TB to 32 TB CMR models publish 2.5 million hours MTBF, 0.35% AFR, 5-year warranty, helium sealing, and a published rotational-vibration spec.

For scoring, this leads to a useful normalization rule: **desktop < NAS < NAS Pro < enterprise/datacenter**. Then let the published quantitative fields refine the score inside each bucket. A NAS buyer usually cares more about the platform signals and failure-behavior signals than about a few MB/s of sequential speed. That is why workload rating, warranty length, RV handling, and recovery behavior deserve heavier weights than spindle speed or cache size alone. This weighting is an inference from the vendor positioning and spec differences above.

For SSDs, the same ladder exists but the class split is better modeled as **client/desktop SSD**, **NAS SSD**, and **enterprise/datacenter SSD**, with a second dimension for endurance class. WD Red SA500 is sold specifically for 24/7 NAS arrays. Seagate IronWolf 125 is NAS-optimized and always-on. IronWolf Pro 125 adds explicit power-loss data protection and 1 DWPD. Synology SAT5200 is an enterprise SATA SSD built for mixed 24/7 workloads, with over 10,000 TBW at top capacity, power-loss protection, and 5-year warranty. Micron 7450, Kingston DC600M/DC3000ME, KIOXIA PM/CM families, and Solidigm D7/D5 families are squarely in enterprise/datacenter territory.

## HDD recording and enclosure technologies

The PMR terminology confusion is real, and it matters because many listings misuse the terms. Western Digital’s recording-technology brief says CMR and SMR are recording formats, while ePMR, MAMR, and HAMR are recording technologies layered on top of perpendicular recording. Toshiba’s HDD-specification explainer states it even more clearly: what is now called **CMR** was formerly called **PMR**. So for your taxonomy, do **not** model PMR as the opposite of SMR. The relevant suitability field is **CMR vs SMR**, not “PMR vs SMR.”

For ordinary NAS and RAID use, SMR is the wrong default. Seagate’s current CMR/SMR page says SMR is best suited to sequential or easily sequentialized workloads, and that successful deployment requires architectural control over the storage software stack, SMR-aware filesystems and storage engines, write ordering, buffering, and zone management. QNAP’s official FAQ says SMR-based drives affect RAID rebuild performance. Western Digital’s 2020 WD Red statement says Red Plus was created as the CMR NAS line and explicitly calls it the right choice for write-intensive SMB workloads such as ZFS. That combination is enough for a strong scoring rule: **for broad homelab/small-business NAS/server scoring, device-managed SMR should be treated as disqualifying unless the listing is explicitly archival/sequential and the intended stack is SMR-aware**.

Reliable SMR detection requires an exact **model-number lookup**, not just family recognition. Western Digital’s support article says to determine whether an internal drive uses CMR or SMR by checking the specific data sheet, and WD’s own Blue data sheet maps exact model numbers to CMR or SMR. Seagate publishes a live family/capacity CMR/SMR matrix on its official site. Toshiba’s desktop data sheets also expose mixed CMR/SMR behavior by exact part number or packaging note. The implementation consequence is simple: keep a normalized lookup keyed by an exact model number, not by listing title alone.

A useful vendor-specific rule set falls out of the official docs. **Current WD Red Plus and WD Red Pro are CMR. Current Seagate IronWolf, IronWolf Pro, and Exos CMR lines are also CMR. Current Toshiba N300 and MG are CMR. Desktop lines are where you must not trust the family name alone**: WD Blue mixes CMR and SMR; Seagate BarraCuda mixes CMR and SMR by capacity on Seagate’s own matrix; Toshiba P300 has a mixed line with packaging notes separating 2 TB CMR and 2 TB SMR.

Helium versus air should be treated as a secondary feature, not a primary quality signal. Western Digital says HelioSeal enables more disks, quieter operation, and lower power usage, and older Ultrastar data sheets tie HelioSeal to higher reliability ratings and lower TCO. Seagate describes its helium sealed-drive design as reducing power and weight while its side-sealing weld improves handling robustness and leak protection. Toshiba says helium-sealed N300 models use less power, increase density, and reduce noise. That means helium is a positive signal for high-capacity modern platforms, but **helium itself is not the reason to trust a drive**; the more important predictors remain the drive’s tier, workload rating, warranty, vibration handling, and vendor-published reliability numbers. The final sentence is a scoring recommendation based on the cited vendor claims.

## SSD attributes that actually separate server-grade from consumer-grade

For SSDs, endurance must be represented with both **DWPD** and **TBW** when available. DWPD is easier to compare across capacities, while TBW is the vendor’s absolute write-life figure. Enterprise and NAS SSD vendors usually derive these values from JEDEC enterprise workloads. Kingston DC600M publishes 1 DWPD and capacity-specific TBW values up to 14,016 TB, explicitly tied to JEDEC JESD219A. Micron 7450 publishes total-bytes-written endurance and also summarizes the line as 1 DWPD for PRO and 3 DWPD for MAX in its technical spec. KIOXIA PM7-R publishes 1 DWPD, and KIOXIA’s PM family page distinguishes 3 DWPD mixed-use and 1 DWPD read-intensive variants. Synology SAT5200 publishes TBW values up to over 10,000 TB and is rated for mixed 24/7 workloads.

NAND type is also score-worthy. Micron’s NAND documentation says SLC stores one bit per cell and prioritizes performance and endurance; MLC stores two bits per cell; TLC stores three; QLC stores four. Samsung’s NAND explainer and KIOXIA’s flash-technology page make the same bit-per-cell distinctions. Solidigm’s QLC guidance says TLC is a fit for mixed and write-heavy workloads, while QLC is more cost-effective and capacity-optimized for read-centric workloads. For scoring, that means SLC and MLC are strongest for endurance but uncommon and expensive, TLC is the mainstream “good server default,” and QLC is acceptable only when the listing or family is clearly read-optimized and the endurance numbers still meet the intended workload.

DRAM cache should be modeled separately from NAND type. Kingston DC600M explicitly publishes a DRAM cache and is sold as a latency-consistent enterprise SATA SSD. By contrast, Samsung’s 990 EVO/990 EVO Plus materials describe Host Memory Buffer and a DRAM-less design. For a server or NAS scoring engine, DRAM-backed SSDs should score better for sustained write-heavy or mixed workloads because enterprise vendors pair DRAM with QoS/latency-consistency claims, while DRAM-less client drives are optimized around cost, simplicity, and host memory borrowing. That last sentence is an inference from the cited product architectures and positioning, and it is a good one for scoring even though a few server-boot SSDs complicate the rule.

Power-loss protection is one of the most important SSD fields for 24/7 service. IronWolf Pro 125 explicitly advertises power-loss data protection and 1 DWPD. Synology SAT5200 says its dedicated capacitors flush data-in-flight into NAND on power loss and that the series has power-loss protection. Kingston DC600M publishes hardware-based power-loss protection. Micron 7450 publishes full power-loss protection, including M.2 variants. KIOXIA’s enterprise SSD pages say the enterprise lines feature PLP. On the other side, Seagate’s IronWolf 125 manual explicitly says the drive does **not** provide sudden-power-loss data protection. That makes PLP a strong positive signal and, for write-bearing server roles, the absence of PLP a strong negative.

Form factor and interface should be split into different fields because listings often blur them. Seagate’s SSD explainer says SATA, NVMe, M.2, U.2, and PCIe are different types distinguished by protocol, interface, and form factor. In vendor practice: SATA 2.5-inch is common in NAS and older enterprise systems; SAS 2.5-inch is enterprise-only and often dual-port; M.2 is a card form factor that may be client or enterprise; U.2 and U.3 are enterprise 2.5-inch NVMe form factors for hot-swap environments; and U.3 is commonly backward-compatible with U.2 on enterprise platforms. Micron 6500 ION explicitly says U.3 is backward compatible with U.2. KIOXIA’s PM7-R documents dual-port SAS, and Micron 7450 demonstrates that enterprise M.2 with PLP exists and should not be automatically rejected.

## Scoring-oriented attribute schema

Use `null` for unknown and reserve `false` for an explicit negative. Do not back-compute missing vendor fields unless you want a separate derived layer. In particular, keep vendor-published `mtbf_hours`, `afr_percent`, `workload_tb_year`, `dwpd`, and `tbw_tb` as raw fields.

### Universal fields

| Field name | Type | How to source | Why it matters |
|---|---|---|---|
| `media_type` | `enum["hdd","ssd"]` | Usually parseable from title/description; otherwise family lookup | Branches the scoring path and determines which attributes are applicable. |
| `manufacturer` | `string` | Parse from title; normalize aliases | Required for family/model lookup. |
| `model_family` | `string` | Parse from title/description, then normalize against vendor families | Family is the single strongest prior for intended workload tier. |
| `model_number` | `string` | Parse exact SKU/part number from title/description/spec block; fall back to vendor lookup | Exact model number is mandatory for detecting mixed families, CMR/SMR, exact endurance, warranty, and PLP. |
| `capacity_gb` | `integer` | Parse from title/description or spec table | Capacity affects value, endurance normalization, and whether a drive revision is helium/air or CMR/SMR in mixed families. |
| `market_tier` | `enum["desktop","nas","nas_pro","enterprise","datacenter","mission_critical"]` | Prefer family lookup; do not infer purely from title adjectives | High-level suitability prior. Desktop lines are materially different from NAS and enterprise lines in warranty and duty-cycle positioning. |
| `interface_protocol` | `enum["sata","sas","nvme","unknown"]` | Often parseable from title/spec block | Strong proxy for platform class and compatibility. SAS and enterprise NVMe generally imply higher-end server roles. |
| `form_factor` | `enum["3.5in","2.5in","m.2_2280","m.2_22110","u.2","u.3","e1.s","e1.l","other"]` | Often parseable from title/spec block; sometimes lookup | Matters for hot-swap, thermals, PLP packaging, and chassis compatibility. |
| `warranty_years` | `number` | Spec block or vendor data sheet lookup | Very strong tier signal; desktop 2 years, NAS usually 3, NAS Pro/enterprise often 5. |
| `mtbf_hours` | `integer|null` | Usually requires vendor data sheet | Reliability prior; compare raw vendor claims, not your own conversions. |
| `afr_percent` | `number|null` | Vendor data sheet only | Useful when explicitly published; do not derive if absent. |
| `workload_tb_year` | `integer|null` | Usually data sheet or product brief lookup | One of the clearest “24/7 suitability” fields for HDDs and some NAS/enterprise positioning. |
| `twenty_four_seven_claim` | `boolean|null` | Usually description/product brief | Good top-level suitability signal, though weaker than quantitative fields. |

### HDD-only fields

| Field name | Type | How to source | Why it matters |
|---|---|---|---|
| `recording_tech` | `enum["cmr","smr","unknown"]` | Exact model lookup against vendor data sheet/support matrix | For normal NAS/RAID use, SMR is a hard negative because vendors position it for sequentialized or SMR-aware architectures and QNAP says it impacts RAID rebuilds. |
| `pmr_term_seen` | `boolean|null` | Parse text only; do not score directly | PMR is terminology noise. CMR and SMR are the real suitability dimension. |
| `bay_support_max` | `integer|null` | Product brief/data sheet | NAS lines often publish supported bay counts; more bays usually means stronger vibration design and firmware tuning. |
| `rv_sensors` | `boolean|null` | Usually vendor brief or support page; often not in retail title | Strong NAS/enterprise signal for multi-drive systems. |
| `rv_rating` | `number|null` | Enterprise data sheet only | Useful for top-tier enterprise comparison when published, less useful for retail/NAS lines. |
| `shock_sensor` | `boolean|null` | Vendor data sheet/brief | Additional vibration/shock resilience signal in higher tiers. |
| `error_recovery_control` | `enum["explicit","family_inferred","unknown"]` | Use explicit when data sheet says RAID error recovery control / ERC; otherwise infer from strong NAS families only as a weaker flag | Limited error recovery behavior reduces RAID dropouts during error recovery; WD and Toshiba explicitly call it out in NAS lines. |
| `fill_gas` | `enum["air","helium","unknown"]` | Often exact-model data sheet lookup | Secondary signal; correlated with modern high-capacity NAS/enterprise platforms, lower power, and higher density. |
| `enterprise_write_cache_protection` | `boolean|null` | Only set true on explicit claims like ArmorCache or Persistent Write Cache | Valuable enterprise differentiator; do not assume on NAS drives. |
| `rpm` | `integer|null` | Parse title/spec block; confirm with data sheet when in doubt | Weak total-ordering signal by itself, but still useful for filtering and sanity checks. |

### SSD-only fields

| Field name | Type | How to source | Why it matters |
|---|---|---|---|
| `nandu_type` | `enum["slc","mlc","tlc","qlc","unknown"]` | Usually requires data sheet lookup | TLC is the mainstream strong default; QLC is best treated as read-optimized unless endurance and role say otherwise. |
| `dram_cache_mode` | `enum["dram","dramless_hmb","dramless","unknown"]` | Usually data sheet/spec page lookup | DRAM-backed enterprise SSDs are a better default for mixed and sustained server workloads; DRAM-less HMB is common in client SSDs. |
| `plp` | `enum["yes","no","unknown"]` | Vendors usually state this explicitly; model lookup required | One of the highest-signal SSD fields for NAS/server writes and crash consistency. |
| `end_to_end_data_protection` | `boolean|null` | Vendor enterprise data sheet | Strong enterprise signal; often paired with PLP. |
| `dwpd` | `number|null` | Vendor data sheet lookup | Most portable endurance metric across capacities. |
| `tbw_tb` | `integer|null` | Vendor data sheet lookup | Absolute endurance; keep raw because listing buyers care about the posted number. |
| `ssd_endurance_class` | `enum["read_intensive","standard","mixed_use","write_intensive","unknown"]` | Best sourced from family lookup plus data sheet | Enterprise families often segment by intended write rate; this is a better classifier than NAND alone. |
| `hot_swap_friendly` | `boolean|null` | Infer from U.2/U.3/2.5-inch enterprise platform docs; avoid assuming on M.2 | Matters in servers and NAS serviceability. Micron positions U.3 for standard servers using existing hot-swap capabilities, while M.2 is typically internal and compact. |
| `dual_port` | `boolean|null` | Enterprise SAS/U.2/U.3 vendor specs only | Important for HA storage shelves and enterprise fabrics, usually irrelevant for consumer NAS. |

## Current model-family landscape

These tables reflect the official public product pages and data sheets visible as of early July 2026.

### HDD family to tier reference

| Vendor | Family | Tier | Media | Key published suitability signals | Evidence |
|---|---|---|---|---|---|
| Western Digital | WD Blue 3.5-inch HDD | Desktop | HDD | PC/office positioning, 2-year warranty, family mixes CMR and SMR by exact model | |
| Western Digital | WD Red Plus | NAS | HDD | Up to 8 bays, 180 TB/year, 1M MTBF, 3-year warranty, CMR | |
| Western Digital | WD Red Pro | NAS Pro | HDD | Unlimited bays, 550 TB/year, up to 2.5M MTBF, 5-year warranty, RV sensors, CMR | |
| Western Digital | WD Gold | Enterprise | HDD | 5-year warranty, up to 2.5M MTBF, AFR down to 0.35%, RVS dual sensors, ArmorCache on 22 TB+ | |
| Western Digital | Ultrastar DC HC580 / HC590 | Datacenter | HDD | 24x7, 2.5M MTBF, AFR 0.35%, major cloud/data center positioning, ArmorCache enterprise power-loss protection | |
| Seagate | BarraCuda 3.5 | Desktop | HDD | Consumer desktop line; Seagate’s official CMR/SMR matrix shows mixed CMR and SMR by capacity | |
| Seagate | IronWolf | NAS | HDD | 180 TB/year, 1M MTBF, 3-year warranty, RV sensors, CMR | |
| Seagate | IronWolf Pro | NAS Pro | HDD | 550 TB/year, 2.5M MTBF, 5-year warranty, RV sensors, all-CMR, currently up to 32 TB | |
| Seagate | Exos / Exos M / Exos X | Enterprise / Datacenter | HDD | Enterprise/data center positioning, 2.5M MTBF, 0.35% AFR, 5-year warranty, helium sealing, published rotational vibration spec | |
| Toshiba | P300 | Desktop | HDD | Home/office desktop positioning, 2-year warranty, mixed CMR/SMR behavior by exact part number | |
| Toshiba | N300 | NAS | HDD | 24/7, up to 12 bays, 180 TB/year, RV sensors, error recovery control, 3-year warranty, current public line up to 22 TB | |
| Toshiba | MG Series | Enterprise Capacity | HDD | Enterprise 24/7 nearline/capacity line, 550 TB/year, 5-year warranty, rotational-vibration sensor, persistent write cache | |
| Toshiba | AL Series | Enterprise Performance | HDD | Mission-critical SAS, 24/7, 5-year warranty, 2M MTTF, dual-port SAS, persistent write cache | |

A Toshiba-specific note matters for lookup design: current Toshiba public branding is **N300**, **MG Series**, and **AL Series**, but many Toshiba bulk model numbers begin with prefixes like `MN10...` and `MN11...`. Those should be treated as exact-model identifiers underneath the public family, not as a separate tier by themselves.

### SSD family to tier reference

| Vendor | Family | Tier | Interface / form factor | Key published suitability signals | Evidence |
|---|---|---|---|---|---|
| Western Digital | WD Red SA500 | NAS | SATA, 2.5-inch and M.2 | Designed and tested for 24/7 NAS arrays | |
| Seagate | IronWolf 125 | NAS | SATA 2.5-inch | NAS-optimized, always-on; publishes TLC and TBW, but manual says no sudden-power-loss protection | |
| Seagate | IronWolf Pro 125 | NAS Pro | SATA 2.5-inch | NAS-optimized, power-loss data protection, 1 DWPD, 5-year warranty | |
| Synology | SAT5200 | Enterprise NAS / SMB Enterprise | SATA 2.5-inch | Mixed 24/7 workloads, power-loss protection, end-to-end protection, TBW up to >10,000 TB, 5-year warranty | |
| Kingston | DC600M | Enterprise | SATA 2.5-inch | Mixed-use server workloads, 3D TLC, DRAM cache, hardware PLP, 1 DWPD, 5-year warranty | |
| Kingston | DC3000ME | Enterprise / Datacenter | NVMe U.2 | PCIe 5.0, 3D eTLC, PLP, backward-compatible with PCIe 4.0 servers/backplanes | |
| Micron | 7450 PRO / MAX | Datacenter | NVMe, E1.S and M.2 | 3D TLC, full PLP, end-to-end protection, M.2 and E1.S, 1 DWPD PRO / 3 DWPD MAX-class endurance summary | |
| KIOXIA | PM7-R | Enterprise Read-Intensive | SAS 2.5-inch 15mm | Dual-port SAS, TLC, PLP, 1 DWPD, 5-year warranty | |
| KIOXIA | PM7-V | Enterprise Mixed-Use | SAS 2.5-inch 15mm | Same PM family, but 3 DWPD mixed-use on KIOXIA enterprise page | |
| KIOXIA | CM9-R / CM9-V | Enterprise NVMe | 2.5-inch / E3.S | Dual-port NVMe enterprise family with PLP; read-intensive and mixed-use segmentation | |
| Solidigm | D7-P5520 | Enterprise / Datacenter | NVMe | TLC, standard-endurance / read-intensive positioning | |
| Solidigm | D7-P5620 | Enterprise / Datacenter | NVMe | TLC, mid-endurance mixed-workload positioning | |
| Solidigm | D5-P5336 | Datacenter Read-Optimized | NVMe | QLC, high-density, read-optimized, data-intensive workloads | |
| Solidigm | D5-P5430 | Datacenter Mainstream / Read-Intensive | NVMe | QLC, mainstream and read-intensive workloads, lower-TCO dense storage | |
| Samsung | PM9A3 | Datacenter / OEM Enterprise | NVMe, U.2 / E1.S / M.2 | Enterprise NVMe OEM family with multiple server form factors | |

## What can be parsed from a normal listing and what requires a lookup table

A typical retail or secondary-market listing title can usually give you only the **coarse identity** of the drive: manufacturer, family, capacity, interface, and form factor. Good titles often also expose RPM for HDDs, and sometimes “NAS,” “enterprise,” “datacenter,” “Pro,” or “server.” A richer description or spec block may add cache size, warranty, and sometimes workload, MTBF, TBW, or DWPD. But most of the best scoring fields are either inconsistent in listing text or missing entirely.

The fields that are frequently parseable from title/description are: `manufacturer`, `model_family`, `capacity_gb`, `media_type`, `interface_protocol`, `form_factor`, `rpm`, and coarse `market_tier` keywords such as NAS or enterprise. Sometimes you can also parse `warranty_years`, `tbw_tb`, `dwpd`, and `plp` if the seller copied a vendor spec block verbatim. Listings for enterprise SSDs are more likely to include endurance numbers than HDD listings are to include workload numbers.

The fields that should default to **lookup-table required** are: exact `recording_tech`, `rv_sensors`, `rv_rating`, `error_recovery_control`, `fill_gas`, `enterprise_write_cache_protection`, `mtbf_hours`, `afr_percent`, `workload_tb_year`, `nandu_type`, `dram_cache_mode`, `end_to_end_data_protection`, `dual_port`, and, in mixed families, even the exact `market_tier`. WD Blue and Toshiba P300 show why: one family name covers both CMR and SMR models. Seagate’s live CMR/SMR matrix shows the same problem on BarraCuda by capacity.

So the right architecture is a **two-stage parser**. Stage one does text extraction from title/description and produces a normalized candidate identity. Stage two uses an exact model-number knowledge base and, when possible, vendor datasheet lookups to fill the strong fields. A practical source-precedence rule is: **exact model datasheet > vendor support page > family prior > listing description > listing title**. When the exact model cannot be resolved, record `unknown` for the risky fields rather than guessing. That is especially important for HDD recording technology and SSD PLP/DRAM claims. The source-precedence rule is an implementation recommendation based on the vendor documentation patterns above.

A good scoring engine for this buyer profile can therefore use the following gating logic without much controversy. **Reject or heavily down-rank HDDs with `recording_tech="smr"` for NAS/RAID. Strongly prefer `market_tier` in `{"nas","nas_pro","enterprise","datacenter"}` over `desktop`. Prefer explicit workload rating, longer warranty, and higher MTBF/AFR classes. For SSDs, strongly prefer explicit PLP, enterprise/NAS families, and non-QLC NAND unless the family is clearly read-optimized and the write endurance still fits the target role. Penalize DRAM-less client M.2 SSDs for primary NAS/server storage, but do not auto-reject enterprise M.2 with PLP such as Micron 7450 variants.** The last sentence is a scoring recommendation derived from the vendor documentation above.