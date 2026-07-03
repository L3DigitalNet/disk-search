# Entity Resolution for Cross-Marketplace Hard Drive and SSD Price Tracking

## Bottom line

For storage drives, the most reliable cross-market identity anchor is usually the **full manufacturer model or orderable part number plus brand**, not a marketplace catalog ID. GTINs are very strong aliases, but they identify a **trade item** and can change with packaging, branding, or other sellable-unit changes; Google also explicitly notes that some products can have **more than one valid unique product identifier**, such as a global GTIN and a distributor-specific GTIN. ASINs and eBay ePIDs are excellent **marketplace-local catalog identifiers**, but they should be stored as aliases, not used as your global canonical key. For your use case, the safest design is a **two-level identity model**: a **physical product key** for the exact hardware variant, and a **sellable-variant key** that adds condition and packaging/channel facets for price analysis.

The practical recommendation is:

- Use a **surrogate internal `canonical_product_id`**.
- Resolve that ID primarily from **brand + exact normalized manufacturer part number** when available.
- Keep **GTIN, ASIN, ePID, merchant SKU, and seller title** as alias/evidence records, not as the canonical identity itself.
- Model **condition separately** from the physical product identity, but include it in a second-level “sellable variant” key so that “new 14TB Exos” and “manufacturer recertified 14TB Exos” can be compared both together and separately. This follows the same conceptual split used by structured-data standards, where **Product** and **Offer** are distinct and condition is an **offer-level property**.

## Which identifiers to trust

**Manufacturer model / part number / MPN** is the best cross-market anchor **if and only if you have the full exact code and the brand**. eBay’s own catalog documentation warns that MPNs may be unique only within a brand and should not be assumed globally unique by themselves. Google Merchant Center likewise says each variant typically has its own MPN and that the correct MPN must distinguish variants. In other words, `brand + full MPN` is strong; `MPN alone` is not; and a truncated family stem is dangerous.

Storage vendors’ own numbering schemes show why exactness matters. Seagate’s Exos X18 datasheet uses distinct model numbers for capacity, interface, and security variants, such as `ST18000NM000J`, `ST18000NM004J`, and `ST18000NM007J`; the same family name contains multiple different physical SKUs. Western Digital’s Ultrastar HC550 documentation explicitly shows how capacity, interface, power-disable-pin behavior, and security mode are encoded in the model number, and then lists separate orderable part numbers for those variants. Samsung’s 870 EVO datasheet separates a capacity-specific base model name such as `MZ-77E1T0` from multiple region/orderable codes such as `MZ-77E1T0BW`, `MZ-77E1T0B/AM`, `MZ-77E1T0B/EU`, and `MZ-77E1T0B/CN`. That is exactly the pattern your system has to survive: family names are reused, stems are shared, and region/orderable suffixes matter.

**GTIN / UPC / EAN** is highly valuable, but it is not a perfect natural key for your database. GS1 defines GTIN as a globally unique identifier for a **trade item**, and the GTIN management rules require new GTINs for many sellable-unit changes, including new products, declared net content changes, dimensional or gross-weight changes, brand changes, and defined assortments. Google’s product-identifier guidance also says each variant should have its own GTIN, but it separately notes that a product can have **more than one valid UPI**, such as a global GTIN and a distributor-specific GTIN. So GTIN is strong evidence that two offers are the same sellable unit, but in practice you should still treat it as an alias that maps into your internal product graph rather than as the sole canonical key.

**Amazon ASIN** is a strong identifier **inside Amazon’s catalog**, not outside it. Amazon’s own documentation and guides describe ASIN as Amazon’s unique identifier for products in the Amazon catalog, including product variations and versions, and Amazon distinguishes real sellable child ASINs from “virtual” parent ASINs used only to connect variation families. That makes ASIN extremely useful for consolidating Amazon offers, but it is still an **Amazon catalog key**, not a manufacturer identity. A single physical drive may have different aliases on other marketplaces that do not preserve the ASIN, and parent/child structures mean you cannot blindly use every ASIN as a physical-product key without understanding whether you are looking at a child listing or a virtual parent.

**eBay ePID** plays the same role on eBay that ASIN plays on Amazon: it is a strong **catalog product identifier within eBay**. eBay states that each catalog product is uniquely identified by an ePID, but it also says catalog coverage exists only for many categories rather than all listings, and that matching by GTIN or Brand+MPN has lower success than directly using an ePID. eBay’s legacy Product API further describes ePID as a fixed catalog reference and notes that one reference ID can be associated with multiple product IDs. In practice, that means ePID is excellent as marketplace evidence and useful when present, but it should not replace your internal physical identity model.

A useful negative lesson is **merchant SKU**: structured-data standards define SKU as a **merchant-specific identifier**. Store SKUs are valuable for within-merchant deduplication, longitudinal seller tracking, and offer history, but not for cross-merchant entity resolution.

## How to parse and normalize listing titles

Retail product titles are noisy because they are short, irregular, and semistructured rather than well-formed language. More’s work on e-commerce title extraction describes the “absence of syntactic structure” in product titles and shows that sequence labeling plus curated normalization can work effectively. Köpcke and colleagues, working specifically on product-offer matching, argue that product matching benefits from preprocessing that **extracts and cleans new attributes usable for matching**, especially product codes embedded in titles and descriptions.

The best practical approach for storage drives is a **hybrid parser**, not a single model.

Start with a **deterministic normalization layer**. Canonicalize Unicode, case, punctuation, quotes, separators, and common marketplace boilerplate; expand storage units into normalized numeric forms; standardize interface tokens (`SATA`, `SAS`, `NVMe`, `PCIe 4.0 x4`), form factors (`3.5"`, `2.5"`, `M.2 2280`, `U.2`, `E1.S`), and condition vocabulary (`new`, `used`, `refurbished`, `renewed`, `manufacturer recertified`, `open box`). For storage specifically, you also want controlled vocabularies for family names and technology facets such as **CMR/SMR**, **512e/4Kn**, and **SED/FIPS** because manufacturers encode those distinctions in exact model families and orderable numbers. Seagate and Western Digital’s documentation shows that interface, capacity, sector format, and security mode are not cosmetic—they are part of the SKU boundary.

Then apply **rule-based extraction for high-precision attributes**. Rule-based extraction is especially good for:
- capacities such as `960GB`, `1TB`, `14TB`, `20TB`;
- form factors and dimensional variants like `M.2 2280`, `2.5-inch`, `3.5-inch`;
- protocol/interface cues like `SATA 6Gb/s`, `SAS 12Gb/s`, `PCIe Gen4`, `NVMe`;
- condition and seller-state cues;
- product-code candidates that combine letters, digits, hyphens, and slashes. Köpcke et al. specifically found that regex-driven product-code extraction is useful because the most discriminative product identifiers often appear only in unstructured titles or descriptions.

After that, use a **sequence-labeling or transformer extraction layer** for the cases rules miss. The older CRF-style approach remains attractive when you care about transparency, labeling cost, and low-latency CPU inference; OpenTag extends that idea by using a BiLSTM-CRF approach for open attribute-value extraction from product profiles and is explicitly motivated by the need to discover values not captured by fixed dictionaries. Wayfair’s 2024 work shows a modern production variation of the same idea: a transformer-based NER model trained with weak labels generated from customer interactions. Those approaches fit your problem well because you have a narrow domain with recurring schemas but messy surface forms.

Use **LLM extraction and normalization as a targeted fallback**, not the first pass. Recent work on WDC-PAVE found that GPT-4 exceeded 90% F1 on product attribute extraction and normalization and outperformed BERT-based baselines by about 10 F1 points, particularly on string wrangling and name expansion. That is compelling, but the literature on LLM-based entity matching also shows prompt sensitivity, cost tradeoffs, and variability across datasets. For a production price-tracking pipeline, the right use is **on uncertain records**, **schema-drift cases**, and **normalization repair**, not on every listing.

My recommended parsed schema for every title is:

`brand, family, full_model_code_candidate, capacity_bytes, interface_bus, protocol, form_factor, recording_tech, sector_format, security_variant, generation, condition, packaging, recertification_flag, merchant_noise_flags, confidence_per_attribute`

That schema is deliberately more opinionated than the average e-commerce parser because storage-drive false merges are dominated by very specific collisions: same family, different capacity; same family and capacity, different interface; same drive family, different sector/security mode; same physical model, different condition or recertification state. The literature and manufacturer docs both point to the same conclusion: those “small” attributes are often exactly what separate one commercial SKU from another.

## Recommended canonical key and matching strategy

The safest design is a **dual identity model**.

The first layer is the **physical product key**: the exact hardware variant you mean when you say “this is the same drive model.” This key should **exclude condition** and marketplace-specific IDs. The second layer is the **sellable variant key**: the unit a shopper actually compares for price, which adds condition and commercial facets such as packaging or recertification channel. That split is consistent with both Google’s `ProductGroup`/variant model and Schema.org’s distinction between `Product` and `Offer`, where `itemCondition` belongs on the offer.

A practical physical key design is:

`physical_signature = hash(brand_norm, model_code_norm, capacity_bytes, interface_norm, protocol_norm, form_factor_norm, recording_tech_norm, sector_format_norm, security_variant_norm, generation_norm)`

Use the **manufacturer’s exact normalized model code** as the primary anchor when present. If you have a validated full code like `ST18000NM000J` or `WUH721818ALE6L4`, that should dominate the resolution decision because manufacturer docs show those codes already encode many of the distinctions you care about. GTIN should be stored as a strong alias and can directly resolve to the same physical signature when all parsed attributes agree. ASIN and ePID should attach as marketplace aliases to the resolved product.

The **sellable-variant key** should be:

`offer_variant_signature = hash(physical_signature, condition_norm, packaging_norm, recertification_norm, warranty_channel_norm)`

That lets you answer both of your real business questions:
- “What is the market price for this exact hardware model?” using `physical_signature`.
- “What is the comparable market price for a buyable equivalent under the same condition/channel?” using `offer_variant_signature`.

For **blocking**, the literature is clear that essentially all serious EM pipelines need it because all-pairs comparison scales quadratically, and blocking is the standard tradeoff between recall and cost. For your domain, use **multi-pass blocking** rather than a single scheme, because storage listings fail in different ways.

A production-safe blocking design is:

1. **Exact-identifier blocks**: exact normalized `brand+MPN`, exact GTIN, exact ASIN, exact ePID. These are your cheapest and highest-precision blocks.  
2. **Product-code blocks**: extracted alphanumeric model-code candidates plus brand. Köpcke et al. show that extracting product codes from titles/descriptions is especially helpful for distinguishing similar variants.  
3. **Attribute blocks**: `brand + capacity + interface/form_factor`, optionally with a family token. This catches listings that omit the exact model number but still describe the same variant.  
4. **Fallback semantic blocks**: ANN/embedding retrieval over normalized titles, but only after filtering by hard attributes like brand and capacity bucket. The point here is recall rescue, not primary identity. That recommendation follows the modern EM literature, but the cost-quality evidence also suggests that smaller fine-tuned models are often more economical than always calling a large model.

Your **match decision flow** should be conservative and asymmetric toward avoiding false merges:

1. **If exact `brand + full MPN` matches**, resolve to the same physical product unless a parsed hard attribute directly contradicts it, such as capacity or interface. Because storage model codes often encode those exact differences, contradictory parsed attributes usually mean extraction error or merchant data error that should be reviewed, not force-merged.  
2. **Else if GTIN matches**, treat it as strong evidence, but still require that parsed capacity/form factor/interface are not contradictory. This matters because GTINs are strong but packaging-sensitive, and real-world UPC data can be wrong. Köpcke et al. explicitly found UPC information in product offers can be error-prone and lead to insufficient match decisions.  
3. **Else if ASIN/ePID matches within one marketplace**, consolidate that marketplace listing family, enrich attributes from the catalog node, and then try to resolve outward to your internal physical key using MPN/GTIN/parsed attributes. Do not equate “same ASIN” or “same ePID” with “globally canonical product” by itself.  
4. **Else require exact agreement on hard attributes**: brand, capacity, interface/protocol, and form factor. For HDDs, add recording tech and sector/security mode when known; for enterprise drives, SATA vs SAS and 512e vs 4Kn are hard boundaries, not soft similarity hints.  
5. **Only after hard-attribute agreement**, use fuzzy title similarity or an ML/LLM matcher on the residual fields such as family, generation, and model stem. This ordering is the simplest way to prevent catastrophic merges like 16TB vs 18TB or SATA vs SAS.  
6. **If a candidate pair disagrees on capacity, interface, or form factor, force a non-match**, unless you have direct manufacturer-code evidence proving the parser was wrong. In your domain, these are not clerical differences; they are almost always different products. That is an implementation inference from manufacturer docs and marketplace variant rules, and it is the correct bias if price time series quality matters more than squeezing out a few extra merges.  

## How condition should be modeled

For your specific question—whether “recertified 14TB Exos” and “new 14TB Exos” should share a key—the best answer is **yes at the physical-product layer, no at the sellable-variant layer**. Condition is modeled as an **offer property** in Schema.org, not as the core product identity, and Google likewise treats condition as a variant attribute in marketplace feeds. That supports a design where both listings roll up to the same exact hardware product, while still remaining distinct for price analytics, warranty expectations, and buyer intent.

That means:

- **Same physical key**: same brand, exact model code, capacity, interface, form factor, and technical variant.
- **Different offer-variant key**: `new`, `manufacturer recertified`, `seller refurbished`, `used`, `open box`, and similar states should be separate.

This is also supported indirectly by GTIN guidance. Google says used and vintage products may still have the manufacturer-assigned GTIN and should provide it if possible. In other words, the manufacturer identifier can remain the same while condition changes, which is exactly why condition should not live inside your physical identity key.

The one nuance is **packaging/channel differences**. Because GTIN rules can change with packaging hierarchy or bundle composition, and because vendors often publish separate orderable or regional model codes, you should treat **bare drive vs retail kit vs bundle vs recertified channel packaging** as separate **sellable variants** even when the physical drive is the same. That gives you cleaner price histories and avoids averaging together incomparable commercial units.

## Tools, datasets, and literature worth using

For the core ER pipeline, the strongest open-source starting points are **Splink**, **dedupe**, **py_entitymatching / Magellan**, **DeepMatcher / Ditto**, **pyJedAI**, and the **Python Record Linkage Toolkit**. Splink is the most practical probabilistic-linkage option if you want transparency, scalability, and diagnostics; it is explicitly positioned as probabilistic record linkage/entity resolution for datasets without unique identifiers. dedupe is a pragmatic active-learning fuzzy-matching library for structured data. py_entitymatching and Magellan remain useful as an end-to-end classical EM framework with explicit blocking and matching stages. DeepMatcher and Ditto are the most relevant research-grade neural matchers; Ditto showed major benchmark gains from pretrained language models. pyJedAI is a broad ER framework, and the Python Record Linkage Toolkit is still a solid prototyping library, though its own docs emphasize experimentation more than highest performance.

For string features and cheap comparators, **py_stringmatching** and **jellyfish** are worth using. py_stringmatching gives you a large library of tokenizers and similarity measures, including edit distance, Jaccard, and TF/IDF-style measures; jellyfish gives you fast approximate and phonetic matching primitives. Those are useful both in blocking and in hand-built explainable match features.

For datasets, use **WDC Products** as the most modern public benchmark for product matching; it is specifically designed to test corner cases, unseen entities, and development-set size, and it includes pairwise and multiclass formulations. If blocking is a research concern, **WDC Block** is directly relevant and was released for comparing blocking methods at very large candidate scales. For attribute extraction and normalization, **WDC-PAVE** is the best current benchmark to look at; it includes a **Computers & Accessories** subset and, importantly, focuses not just on extraction but also on normalization tasks such as unit conversion and string wrangling. The older **Abt-Buy** and **Amazon-Google Products** datasets are still useful for smoke tests and regression tests, but they are easier and less representative than WDC Products.

The literature most directly relevant to your problem is:
- **Köpcke et al.** for product-offer matching, attribute extraction, and the warning that UPC-only matching is brittle.
- **Papadakis et al.** for blocking strategy and the efficiency/recall tradeoff.
- **More**, **OpenTag**, and **Wayfair 2024** for title/query attribute extraction approaches ranging from CRF to transformer NER.
- **DeepMatcher**, **Ditto**, and later **LLM entity-matching studies** for when you want a learned pair matcher after blocking. The recent cross-dataset evidence is especially important because it shows small fine-tuned models can often match the quality of prompted large models at much lower cost.

In short: build your storage-drive resolver around **full manufacturer codes plus strong parsed hard attributes**, not around marketplace IDs; parse titles with a **hybrid rules + sequence model + LLM fallback** stack; use a **dual key** for physical product versus sellable variant; and keep your matcher **conservative on capacity, interface, form factor, and technical mode** so you reduce false merges before you optimize recall. That is the design most consistent with both the storage-vendor numbering reality and the entity-resolution literature.