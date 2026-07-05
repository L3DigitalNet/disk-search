---
schema_version: '1.1'
id: 2026-07-05-ms1c-catalog-seed-inputs
title: MS-1c Catalog Seed Inputs
description: Live-source input ledger for the MS-1c manufacturer catalog seed: top recert HDD families, merchant inventory evidence, first-party datasheets/manuals, catalog-row field mapping, and carry-forward checks from the MS-1b matching review.
doc_type: research
status: active
created: '2026-07-05'
updated: '2026-07-05'
reviewed: null
owner: chris
tags:
- ms-1c
- catalog-seed
- manufacturer-reference
- product-alias
- recertified
- seagate
- western-digital
- ultrastar
- ironwolf-pro
- toshiba
aliases:
- MS-1c seed inputs
- catalog seed ledger
related:
- ../superpowers/specs/2026-07-05-ms1-ingestion-design.md
- ../adr/adr-0018-manufacturer-spec-catalog.md
- ../adr/adr-0019-listing-catalog-matching-layer.md
- 2026-07-04-ssd-vendor-part-number-decoding-and-spec-catalog-bootstrap-datasets
- programmatic-identity-and-warranty-verification-for-used-enterprise-hdd-listings
source: []
confidence: medium
visibility: public
license: null
---

# MS-1c Catalog Seed Inputs

## Bottom line

MS-1c should start HDD-first with six practical seed lanes: five initial
Seagate/WD lanes, plus Toshiba MG as the first expansion candidate once the
seed shape is proven.

| Priority | Seed family | Why this belongs in the first slice | Status |
| --- | --- | --- | --- |
| 1 | Seagate Exos recertified / Exos X-series | Present across ServerPartDeals, goHardDrive, and eBay; Seagate publishes a recertified Exos datasheet with current `ST...NM...C` rows through 28TB. | Ready for seed-plan rows |
| 2 | Seagate IronWolf Pro | Present across ServerPartDeals and goHardDrive; Seagate's IronWolf Pro datasheet carries dense model/capacity/workload rows. | Ready for seed-plan rows |
| 3 | Western Digital Ultrastar DC HC550 | Present across ServerPartDeals and eBay; WD publishes datasheet plus SATA/SAS OEM manuals with part-number/model-number matrices. | Ready for seed-plan rows |
| 4 | Western Digital Ultrastar DC HC560/HC570 | Present in ServerPartDeals/eBay inventory; first-party datasheets are available. | Seed after HC550 pattern is implemented |
| 5 | WD Gold / WD Red Pro | WD Gold is present in ServerPartDeals recert inventory; WD Red Pro is a design-expected NAS family with current first-party datasheet. | Candidate; verify live merchant inventory before enabling |
| 6 | Toshiba MG07/MG08/MG09 | Present across ServerPartDeals and goHardDrive recert inventory; Toshiba publishes model-family documentation for the MG lines. | Expansion candidate after Seagate/WD importer path is stable |

Treat this as an input ledger, not the MS-1c implementation plan. The plan still needs to define parser scope, fixtures, migrations, and import commands.

## Existing contract to honor

MS-1c implements ADR-0018's reference-data path: `fetch -> parse -> normalize -> persist`, writing `product_family`, `product_model`, `drive_spec`, and `product_alias` only. It must not write listing observations, scores, alerts, or heartbeat rows.

Catalog aliases must pass through `matching.normalize.normalize_alias_text`. That is the same join key listing candidates use in MS-1b, and the parity invariant is already called out in `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md`.

Every reference row uses `retention_class = manufacturer_reference` and `expires_at = NULL`. Discontinued models are retained.

## Live inventory evidence

| Source | Evidence | Seed implication |
| --- | --- | --- |
| ServerPartDeals manufacturer-recertified collection | `https://serverpartdeals.com/collections/manufacturer-recertified-drives` lists manufacturer-recertified drives and exposes filters for Seagate, Western Digital/HGST, Toshiba, SAS, SATA, and capacity bands. | Use as broad inventory confirmation for the recert target market. |
| ServerPartDeals recertified Seagate collection | `https://serverpartdeals.com/collections/recertified-seagate-exos` describes factory-recertified Seagate drives. Search results and extracted content expose Seagate recertified inventory. | Seed Seagate Exos first. |
| ServerPartDeals IronWolf Pro product | `https://serverpartdeals.com/products/seagate-ironwolf-pro-st20000ne000-20tb-7-2k-rpm-sata-6gb-s-512e-3-5-recertified-hard-drive` exposes `ST20000NE000`, 20TB, SATA, 3.5in, 7.2K RPM, 512e, manufacturer recertified, and datasheet label `Seagate IronWolf Pro`. | Good fixture for an exact rung-1 alias hit and `DriveSpec` inheritance. |
| goHardDrive Seagate factory-recertified category | `https://www.goharddrive.com/category-s/308.htm` exposes Seagate factory-recertified/renewed inventory including `ST12000NM0127`, `ST14000NM005G-FR`, `ST16000NE000`, and `ST18000NM003D`. | Confirms Exos plus IronWolf Pro appear outside ServerPartDeals. |
| goHardDrive Exos X16 product | `https://www.goharddrive.com/Seagate-Exos-X16-ST14000NM001G-14TB-3-5-HDD-p/g01-1451-cr.htm` exposes `ST14000NM001G`, 14TB, SATA 6Gb/s, 7200 rpm, 256MB cache, factory recertified. | Good second-merchant fixture for Exos X16. |
| eBay Seagate Exos results | Search results include manufacturer-recertified Exos listings such as `ST16000NM001G`, `ST22000NM001C`, `ST24000NM000C`, `ST28000NM001C`, and `ST20000NM002C`. | The eBay corpus should contribute validation titles, not catalog authority. |
| eBay WD Ultrastar results | Search results include manufacturer-recertified WD Ultrastar HC550/HC530/HC520 listings, including `WUH721818ALE6L4`, `WUH721818AL5201`, and `WUH721816ALE604`. | Use for corpus coverage and unknown-model backfill triggers after first seed. |
| ServerPartDeals WD Ultrastar/Gold results | Search results include WD Ultrastar HC550/HC560/HC570 and WD Gold `WD220EDGZ` recertified products. | Seed HC550 first; queue HC560/HC570 and WD Gold after the import shape is proven. |
| WD direct OCC search | `https://api.westerndigital.com/wdwebservices/v2/us/products/search?query=Ultrastar%20recertified...` returns recertified Ultrastar base pages for HC530, HC520, HC330, and HC580, all out of stock at the base rollup during this pass. General `query=recertified` mostly returns consumer/external drives plus `WD Red Plus Internal NAS HDD 3.5" - Recertified`. | Confirms direct-store recertified WD family pages exist, but do not treat the base-product stock rollup as inventory truth. |
| Seagate direct Exos recertified page | `https://www.seagate.com/products/seagate-recertified/exos-recertified/` currently exposes `ST16000NM002C`, `ST20000NM002C`, `ST22000NM000C`, `ST24000NM000C`, `ST26000NM000C`, and `ST28000NM000C`; page metadata reports capacities 16/20/22/24/26/28TB and `stock_status = IN_STOCK`. | Highest-confidence first direct-source seed path: one family page yields the current Exos recertified SKU ladder. |
| ServerPartDeals Toshiba results | Search results expose Toshiba MG07/MG08/MG09 recertified rows such as `MG07ACA14TE`, `MG08ACA16TE`, `MG09ACA18TE`, plus 4Kn variants `MG07ACA14TA` and `MG09ACA18TA`. | Candidate expansion family after Seagate/WD seed shape is proven. |
| goHardDrive Toshiba results | Search results expose Toshiba MG08/MG09/MG07 certified-refurbished rows including `MG08ACA16TA`, `MG08ACA16TE`, `MG09ACA18TA`, and `MG07ACA14TA`. | Confirms Toshiba MG appears across at least two specialty resellers. |

## Expanded model inventory

This table lists concrete aliases to carry into the MS-1c plan. It is not yet a fixture; each row still needs first-party spec extraction and alias-normalization tests.

| Family bucket | Candidate model / MPN | Capacity | Interface / format | Evidence source | Seed readiness |
| --- | --- | --- | --- | --- | --- |
| Seagate Exos recertified | `ST16000NM002C` | 16TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; Seagate recertified Exos datasheet | Ready |
| Seagate Exos recertified | `ST20000NM002C` | 20TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; ServerPartDeals product; Seagate recertified Exos datasheet | Ready |
| Seagate Exos recertified | `ST22000NM000C` | 22TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; ServerPartDeals/eBay search results; Seagate recertified Exos datasheet | Ready |
| Seagate Exos recertified | `ST24000NM000C` | 24TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; ServerPartDeals/eBay search results; Seagate recertified Exos datasheet | Ready |
| Seagate Exos recertified | `ST26000NM000C` | 26TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; ServerPartDeals product; Seagate recertified Exos datasheet | Ready |
| Seagate Exos recertified | `ST28000NM000C` | 28TB | SATA 6Gb/s, 512e | Seagate direct Exos recert page; ServerPartDeals/eBay search results; Seagate recertified Exos datasheet | Ready |
| Seagate Exos X16 | `ST14000NM001G` | 14TB | SATA 6Gb/s | goHardDrive product; ServerPartDeals/eBay search results | Ready after matching datasheet row selected |
| Seagate Exos X16 | `ST14000NM002G` | 14TB | SAS 12Gb/s | ServerPartDeals product result | Ready after matching datasheet row selected |
| Seagate Exos X18 | `ST16000NM000J` | 16TB | SATA 6Gb/s, 512e | ServerPartDeals product result | Candidate; verify first-party X18 row |
| Seagate Exos X20 | `ST18000NM003D` | 18TB | SATA 6Gb/s | goHardDrive category; ServerPartDeals product result | Candidate; verify first-party X20 row |
| Seagate Exos X20 | `ST20000NM007D` | 20TB | SATA 6Gb/s | ServerPartDeals product result | Candidate; verify first-party X20 row |
| Seagate Exos X24 | `ST16000NM000H` | 16TB | SATA 6Gb/s, 512e | ServerPartDeals product result | Candidate; verify first-party X24 row |
| Seagate Exos X26Z | `ST25000NM000E` | 25TB | SATA 6Gb/s, 512e, host-managed SMR | ServerPartDeals product result | Candidate but scoring-risky; must preserve HM-SMR veto fields |
| Seagate Exos M | `ST32000NM003K` | 32TB | SATA 6Gb/s, 512e | ServerPartDeals product result | Candidate; outside initial recertified datasheet |
| Seagate IronWolf Pro | `ST20000NE000` | 20TB | SATA 6Gb/s, 512e | ServerPartDeals product; Seagate IronWolf Pro datasheet | Ready |
| Seagate IronWolf Pro | `ST18000NE000` | 18TB | SATA 6Gb/s, 512e | ServerPartDeals product; Seagate IronWolf Pro datasheet | Ready |
| Seagate IronWolf Pro | `ST16000NE000` | 16TB | SATA 6Gb/s, 512e | ServerPartDeals/goHardDrive search results; Seagate IronWolf Pro datasheet | Ready |
| Seagate IronWolf Pro | `ST14000NE0008` | 14TB | SATA 6Gb/s, 512e | goHardDrive search result; Seagate IronWolf Pro datasheet | Ready |
| Seagate IronWolf Pro | `ST12000NE0008` | 12TB | SATA 6Gb/s, 512e | ServerPartDeals search result; Seagate IronWolf Pro datasheet | Ready |
| WD Ultrastar DC HC550 | `WUH721818ALE6L4` / `0F38459` | 18TB | SATA 6Gb/s, 512e | WD HC550 datasheet/manual; eBay result | Ready |
| WD Ultrastar DC HC550 | `WUH721818AL5201` / `0F38352` | 18TB | SAS 12Gb/s, 512e | WD HC550 datasheet/manual; eBay result | Ready |
| WD Ultrastar DC HC550 | `WUH721816ALE6L4` | 16TB | SATA 6Gb/s | goHardDrive product; WD HC550 manual | Ready |
| WD Ultrastar DC HC550 | `WUH721816ALE604` | 16TB | SATA 6Gb/s | eBay result; ServerPartDeals result names HC550 | Ready after resolving `604` vs `6L4` suffix semantics |
| WD Ultrastar DC HC570 | `WUH722222ALE6L1` / `0F48154` | 22TB | SATA 6Gb/s, 512e | ServerPartDeals product result; WD HC570 datasheet | Candidate after HC550 importer |
| WD Ultrastar DC HC560 | `WUH722020ALE604` / `0F38752` | 20TB | SATA 6Gb/s, 512e | ServerPartDeals product result; WD HC560 datasheet | Candidate after HC550 importer |
| WD Ultrastar DC HC530 | `WUH721414ALE601` | 14TB | SATA 6Gb/s | goHardDrive product; WD direct OCC recertified page exists | Candidate; older recert core |
| WD Ultrastar DC HC520 | `HUH721212AL4204` / `0F29579` | 12TB | SAS 12Gb/s, 4Kn | ServerPartDeals product result | Candidate; older recert core |
| WD Gold | `WD220EDGZ` | 22TB | SATA 6Gb/s, 512e | ServerPartDeals product result; WD Gold datasheet | Candidate; verify direct/store recert availability |
| Toshiba MG07 | `MG07ACA14TE` | 14TB | SATA 6Gb/s, 512e | ServerPartDeals product; Toshiba MG07/MG-series docs | Candidate expansion |
| Toshiba MG07 | `MG07ACA14TA` | 14TB | SATA 6Gb/s, 4Kn | ServerPartDeals/goHardDrive products; Toshiba MG07/MG-series docs | Candidate expansion |
| Toshiba MG08 | `MG08ACA16TE` | 16TB | SATA 6Gb/s, 512e | ServerPartDeals/goHardDrive products; Toshiba MG08 docs | Candidate expansion |
| Toshiba MG08 | `MG08ACA16TA` | 16TB | SATA 6Gb/s, 4Kn | goHardDrive product; Toshiba MG08 docs | Candidate expansion |
| Toshiba MG09 | `MG09ACA18TE` | 18TB | SATA 6Gb/s, 512e | ServerPartDeals product; Toshiba MG09 docs | Candidate expansion |
| Toshiba MG09 | `MG09ACA18TA` | 18TB | SATA 6Gb/s, 4Kn | ServerPartDeals/goHardDrive products; Toshiba MG09 docs | Candidate expansion |

## Source readiness by connector

| Source | Inventory role for MS-1c | Current finding | Plan impact |
| --- | --- | --- | --- |
| Seagate direct recert | Authoritative inventory signal for Exos recertified SKUs | Robots-allowed category page exposes six in-stock Exos SKUs and current prices. | Start here for direct-source inventory confirmation. |
| WD direct recert | Direct source for WD recertified family pages | OCC search confirms recertified Ultrastar base pages exist, but base rollups are out-of-stock and the general recert search skews consumer. | Use for discovery and connector work, but let specialty resellers drive first WD seed priorities. |
| ServerPartDeals | Richest public recert inventory surface | Exposes Seagate Exos, IronWolf Pro, WD Ultrastar, WD Gold, and Toshiba MG rows with model-rich titles. | Primary merchant corpus for seed prioritization and MS-1e labels. |
| goHardDrive | Cross-check for specialty-recert families | Confirms Seagate Exos/IronWolf Pro, WD Ultrastar, and Toshiba MG across independent product pages. | Use as second-source evidence for seed priority. |
| eBay Browse/search | Broad live market corpus | Search results expose high-volume Exos and WD Ultrastar recertified listings. | Use for validation corpus and backfill triggers, not catalog authority. |

## First-party catalog sources

| Vendor | Source | Useful fields |
| --- | --- | --- |
| Seagate | `https://www.seagate.com/content/dam/seagate/en/content-fragments/products/datasheets/exos-recertified-drive/exos-recertified-drive-DS2045-2-2010US-October-2020-en_US.pdf` | Exos recertified rows for 16TB, 20TB, 22TB, 24TB, 26TB, and 28TB; model numbers; CMR; 512e; cache; MTBF; workload; warranty. |
| Seagate | `https://www.seagate.com/files/www-content/datasheets/pdfs/ironwolf-pro-20tb-DS1914-21-2206US-en_US.pdf` | IronWolf Pro rows for `ST20000NT001`, `ST20000NE000`, `ST18000NT001`, `ST18000NE000`, `ST16000NT001`, `ST16000NE000`, `ST14000NT001`, `ST14000NE0008`, `ST12000NT001`, `ST12000NE0008`, and 10TB models; CMR; 512e; workload; MTBF; cache. |
| Seagate | `https://www.seagate.com/products/seagate-recertified/` | Recertified process and warranty posture; useful as provenance for recert condition, not detailed `DriveSpec`. |
| WD | `https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/data-sheet-ultrastar-dc-hc550.pdf` | HC550 part numbers and model numbers; SATA/SAS; 14/16/18TB; 512e/4Kn; 512MB cache; 7200 rpm; 550TB/year; 5-year limited warranty; SE/SED/FIPS part-number distinctions. |
| WD | `https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc550-sata-oem-spec.pdf` | HC550 SATA OEM model matrix and model-number decoding: generation, interface, sector format, power-disable pin, security mode. |
| WD | `https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc550-sas-oem-spec.pdf` | HC550 SAS model matrix, including SAS security variants. |
| WD | `https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/internal-drives/wd-red-pro-hdd/data-sheet-wd-red-pro-hdd.pdf` | WD Red Pro model table from 2TB to 26TB; CMR; SATA; 3.5in; cache; workload; MTBF; 5-year warranty. |
| WD | `https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/internal-drives/wd-gold/data-sheet-wd-gold-hdd.pdf` | WD Gold enterprise SATA HDD capacities up to 26TB; workload/rating/warranty posture. |
| Toshiba | `https://storage.toshiba.com/enterprise-hdd/cloud-scale-capacity/mg09-series` | MG09 overview page; confirms 18TB CMR family posture. |
| Toshiba | `https://storage.toshiba.com/docs/enterprise-hdd-documents/p_l_mg09aca16tay_210202072836_1_0_0e.pdf` | MG09 product overview with 18TB CMR, 3.5in, 7200 rpm, SATA/SAS model rows. |
| Toshiba | `https://toshiba.semicon-storage.com/content/dam/toshiba-ss-v3/master/en/storage/product/data-center-enterprise/ehdd_mg08_product-manual_rev.3.pdf` | MG08 product manual / spec source for 14/16TB model rows. |
| Toshiba | `https://toshiba.semicon-storage.com/content/dam/toshiba-ss-v3/master/en/storage/product-archive/eHDD-MG07ACA-Product_Overview_rev3s_EOL.pdf` | MG07 product overview / archived source for 12/14TB model rows. |

## Seed row mapping

The first import should produce rows at these grains:

| Row type | Required input | Notes |
| --- | --- | --- |
| `Manufacturer` | `Seagate`, `Western Digital`, `Toshiba`; normalized keys `seagate`, `western_digital`, `toshiba` | Keep SanDisk out of the first HDD seed except for the explicit alias-verification check below. |
| `ProductFamily` | Examples: `Exos`, `Exos X16`, `Exos X20`, `Exos X24`, `IronWolf Pro`, `Ultrastar DC HC550`, `Ultrastar DC HC560`, `Ultrastar DC HC570`, `WD Red Pro`, `WD Gold`, `MG07`, `MG08`, `MG09` | MS-1b may have provisional families such as `exos`; MS-1c must reconcile them to authoritative names. |
| `ProductModel` | Manufacturer model number, e.g. `ST20000NE000`, `ST14000NM001G`, `WUH721818ALE6L4`, `WUH721818AL5201`, `WD220EDGZ` | Normalize with `normalize_alias_text`; set `retention_class = manufacturer_reference`. |
| `DriveSpec` | Media type, interface, form factor, capacity, RPM, cache, recording tech, sector format, SED, workload, market tier, model family | Use typed fields where present; keep raw datasheet row context in `spec_json`. |
| `ProductAlias` | MPN/orderable part numbers, retail/region/security part numbers, WD `0F...` part numbers where first-party docs list them | Grain-address aliases: base model codes to `ProductModel`; security/orderable SKUs to `ProductVariant` only when variant semantics are explicit. |
| `ProductVariant` | Only when condition-free model plus explicit sellable/security/packaging/warranty channel is known | Do not over-create variants from seller condition; reference catalog should not encode marketplace condition. |

## MS-1b carry-forward checks

| Follow-up | MS-1c handling |
| --- | --- |
| Rung-1 hit aggregation | Import should report duplicate normalized alias hits by target and by source document. If two aliases normalize to the same key and point at different targets, fail the import into review rather than selecting one. |
| `unchanged_miss` evidence freshness | Catalog refresh should re-run rungs 1-2 over queued misses and record freshness evidence even when the verdict remains unresolved. A long-lived miss should not look newly examined unless a catalog refresh actually reconsidered it. |
| SanDisk to WD alias verification | Keep `sandisk -> western_digital` as an MS-1b matcher brand-key rule for now, but MS-1c must verify it against seeded catalog aliases before any SSD family seed. If SanDisk-native and WD/SanDisk-rebranded MPNs collide in harmful ways, split the key before SSD ingest. |
| Provisional family reconciliation | Before importing authoritative families, scan existing `ProductFamily.normalized_name` values created by rung 2. Merge or supersede provisional names such as broad `exos` into the specific authoritative family only when the alias/spec evidence supports it. |

## Open inputs for the MS-1c plan

- Confirm current WD/SanDisk direct recert store inventory. Search found warranty/store pages and first-party docs, but not a clean direct recert product listing surface for WD HDDs.
- Decide whether the first seed imports only first-party datasheet PDFs or also merchant product pages as `merchant_fact` corroboration. ADR-0018 says first-party data is authoritative; merchant pages are still useful for choosing which families to seed first.
- Choose whether the first Exos family key is broad `Exos` or split into `Exos X16/X20/X24` plus generic recertified `ST...NM...C` capacity families. The matching layer's rung-2 family materialization should drive this: prefer the narrowest family that reduces false positives without fragmenting obvious same-line rows.
- Define the exact import fixture format. A narrow JSON/YAML fixture checked into tests can cover the first family without committing scraped datasheet bodies.
