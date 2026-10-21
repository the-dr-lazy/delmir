# What Dr. Smith's ECG Blog can provide as a test set

Research for [the-dr-lazy/delmir#13](https://github.com/the-dr-lazy/delmir/issues/13), carried out 2026-10-21. The sample is 50 posts, coded by hand from their full text, plus metadata for every post and full-text search counts. Every claim links to its source. Estimates are marked as estimates, with how they were computed. Licensing is not a constraint: permission is held for every source.

## Answer

**The blog can provide a blog test set of roughly 600 posts (350–940) whose angiography gives a derivable culprit vessel, plus a few hundred Not-OMIs labelled clinically. Culprit location is usually reported. Pre-PCI TIMI flow and dominance almost never are. Most cases show several ECGs, so each label has to be tied to one ECG by hand.**

Headline numbers (the random stratum is 30 posts drawn in proportion to the years; see [Sampling](#sampling)):

| Fact | Random stratum (n = 30) | Estimate over 1,828 archive posts | Whole sample (n = 50) |
|---|---|---|---|
| Post is a patient case with a 12-lead ECG image | 23 (77%) | ≈1,400 [1,080–1,610] | 42 |
| Angiography reported | 14 (47%) | ≈850 [550–1,170] | 30 |
| Culprit artery named (incl. left main, graft, uncertain) | 12 (40%) | ≈730 [450–1,050] | 27 |
| Culprit vessel derivable by the #4 rule (one native system) | 10 (33%) | ≈610 [350–940] | 23 cases |
| Culprit segment given (proximal / mid / distal or branch) | 8 (27%) | ≈490 [260–810] | 20 |
| Pre-PCI TIMI flow stated as a number | 4 (13%) | ≈240 [100–540] | 6 |
| Troponin reported (all but one with numbers) | 12 (40%) | ≈730 [450–1,050] | 31 |
| Dominance stated | 0 | under ≈200 | 1 |
| Prior or serial ECGs in the post | 13 (43%; 57% of case posts) | ≈790 | 30 (71% of case posts) |
| Not-OMI with a clinical final diagnosis, adult, readable | 6 (20%) | ≈370 [170–680] | 9 |

Brackets are 95% Wilson intervals scaled to the 1,828 posts in the Blogger archive. Full-text search over the 2,052 posts on the current site agrees in direction: "troponin" appears in 1,198 posts, "angiogram" in 693, "culprit" in 449, "TIMI" in 429, and "TIMI 0" in 95 ([WordPress search](#full-text-search-counts)).

- **Image quality and format.** Sampled ECG images are mostly clean screenshots or exports from the hospital's ECG system, 1,000–3,700 px wide (most 1,600–3,100), standard 3×4 with or without a lead II rhythm strip, and a calibration pulse. A minority are phone photos of paper or of a monitor, with glare, moiré, skew and cropped edges. Headers with patient data are cropped away, so paper speed and gain are almost never printed; 25 mm/s and 10 mm/mV are implied by the calibration pulse and the grid ([Images](#image-types-and-quality)).
- **Enumeration.** The blog moved in mid-2025 from Blogger (`hqmeded-ecg.blogspot.com`, now a redirect) to WordPress (`drsmithsecgblog.com`). The WordPress REST API lists all 2,052 posts in 21 pages of 100, with tags and full HTML content. The Blogger JSON feed still serves the 1,828-post archive (2008-11-07 to 2025-06-15), with richer labels ([Enumeration](#enumerating-and-fetching-posts-politely)).
- **Recommendation.** Enumerate metadata from the WordPress API, filter by full-text terms to about 700–900 candidate posts, and hand-label each candidate's ECGs with the [#4](https://github.com/the-dr-lazy/delmir/issues/4) follow-up fields plus which ECG the follow-up belongs to. Expect the blog test set to be LAD-heavy and hard by design. Treat its Not-OMIs as clinically labelled rather than angiography-confirmed. Fetch images only for the cases that make it in.

## What a post looks like

A case post opens with a short history and the first ECG, often posed as a question ("What do you think?"). The interpretation follows, then the course: repeat ECGs, troponins, the cath lab decision, angiography, and post-PCI ECGs. It ends with teaching points and often a long comment by Ken Grauer. Example: [Persistent Chest Pain, an Elevated Troponin, and a Normal ECG](https://hqmeded-ecg.blogspot.com/2016/12/persistent-chest-pain-elevated-troponin.html) gives the history, a normal ECG, troponin I 4.1 → 6.2 → 99.9 ng/mL, "an acute 100% occlusion of the circumflex proximal to 2 obtuse marginal branches", a post-cath ECG and an echo.

Follow-up is free prose. Its precision varies:

- **Full report, rare.** One post in 50 quotes a structured cath report with dominance, every vessel, and TIMI flow ([Hyperkalemia: is it the cause of this AV Block…](https://hqmeded-ecg.blogspot.com/2021/10/hyperkalemia-is-it-cause-of-this-av.html): "RCA: dominant … thrombotically occluded in the proximal segment").
- **Artery and segment, common.** "100% occluded proximal Right coronary artery" ([Inferior STEMI without inferior ST elevation](https://hqmeded-ecg.blogspot.com/2013/08/chest-pain-in-61-year-old-male-inferior.html)); "100% occlusion of her Mid LAD just after the takeoff of D1" ([Subtle Dynamic T-waves](https://hqmeded-ecg.blogspot.com/2017/03/subtle-dynamic-t-waves-followed-by-lad.html)).
- **Artery only.** "acute culprit lesion of the LCX 99% stenosis and TIMI 3 flow" ([A man his 50s with chest pain… morphine](https://hqmeded-ecg.blogspot.com/2021/12/a-man-his-50s-with-chest-pain-could-you.html)).
- **Vague.** "a coronary occlusion related to an anomalous coronary artery … the contributor could not remember the exact details" ([A 16 year old girl has syncope](https://hqmeded-ecg.blogspot.com/2014/05/a-16-year-old-girl-has-syncope-while.html)).

Pre-PCI TIMI flow is usually missing. Five sampled posts say so outright: "unknown initial TIMI flow" ([A woman in her 70s](https://hqmeded-ecg.blogspot.com/2023/08/a-woman-in-her-70s-with-chest-pain.html)), "no TIMI flow listed" ([A man in his 50s… Cath lab cancelled](https://hqmeded-ecg.blogspot.com/2022/09/a-man-in-his-50s-with-acute-chest-pain.html)), "no TIMI flows documented" ([A man in his 30s with 12 hours of chest pain](https://hqmeded-ecg.blogspot.com/2019/11/a-man-in-his-30s-with-chest-pain.html)), "pre-intervention TIMI flow not listed" ([Quiz post: high lateral OMI](https://hqmeded-ecg.blogspot.com/2023/01/quiz-post-do-either-or-both-of-these.html)), "TIMI flow not reported" ([Chest Pain in a Male in his 20's](https://hqmeded-ecg.blogspot.com/2013/07/chest-pain-in-male-in-his-20s-inferior.html)). Six more posts report a "100%" or "total" occlusion, which implies TIMI 0 but does not state it.

Troponin is reported with numbers, assay and units in almost every post that mentions it. Units vary over the years: ng/mL for the older contemporary assays, ng/L for high-sensitivity troponin I or T. Peak troponin is stated in 15 of 50 posts. Example: "Initial hs troponin T … 9 ng/L … Troponin T peaked at 2,923 ng/L" ([60 yo with chest pain: why the abnormal QRS](https://hqmeded-ecg.blogspot.com/2024/08/60-yo-with-chest-pain-why-abnormal-qrs.html)).

### Edge cases the #4 rule must handle

[#4](https://github.com/the-dr-lazy/delmir/issues/4) derives a culprit vessel from the follow-up, or gives a named reason. The 30 angiography posts of the sample hold 31 cases:

- **Single native system (vessel derivable):** 23 cases: LAD 13, RCA 7, LCx 3. One is a branch counted to its system: a 99% second diagonal goes to LAD ([Wait until after the ECG to give Nitroglycerine](https://hqmeded-ecg.blogspot.com/2011/07/wait-until-after-ecg-to-give.html)).
- **Left main:** 1 ([A deadly alcohol binge](https://hqmeded-ecg.blogspot.com/2021/10/a-deadly-alcohol-binge-man-in-his-30s.html), 100% LMCA, labelled "TIMI-0").
- **Multiple systems:** 2 (co-culprit LCx + RCA in [Is this ECG diagnostic of coronary occlusion?](https://hqmeded-ecg.blogspot.com/2018/01/is-this-ecg-diagnostic-of-coronary.html) and in [Acute MI, pain onset 24-48 hours ago](https://hqmeded-ecg.blogspot.com/2019/07/acute-mi-pain-onset-24-48-hours-ago.html)).
- **Graft:** 1 (occluded SVG to OM1, TIMI 0, in [A dialysis patient with … pseudonormalization](https://hqmeded-ecg.blogspot.com/2018/09/a-dialysis-patient-with-nonspecific.html)).
- **Uncertain or not named:** 3 (RCA "probable ruptured plaque, but not certain" in [LVH with expected repolarization abnormalities, or acute OMI?](https://hqmeded-ecg.blogspot.com/2019/05/lvh-with-expected-repolarization.html); "severe subtotal LAD disease and 70% left main", then CABG, in [Male in his 40's with chest pain](https://hqmeded-ecg.blogspot.com/2013/01/male-in-his-40s-with-chest-pain.html); the anomalous coronary above).
- **No culprit:** 1 (no significant coronary disease, takotsubo, in [How a pause can cause cardiac arrest](https://hqmeded-ecg.blogspot.com/2024/09/how-pause-can-cause-cardiac-arrest.html)).

Dominance appears once in 50 posts. Site-wide, the phrases "dominant RCA", "right dominant" and "left dominant" appear in 7, 6 and 7 posts ([search counts](#full-text-search-counts)). So the derivation must accept unknown dominance; for blog cases, posterior-wall territory cannot be mapped to a system by dominance.

Several posts call a reperfused lesion with TIMI 3 an OMI. Examples are the Wellens' cases ([Chest pain, resolved](https://hqmeded-ecg.blogspot.com/2024/04/chest-pain-resolved-does-it-need.html): mid-LAD 80–90%, "TIMI-3 flow on initial angiography", tagged "Transient OMI") and spontaneous reperfusion of the LCx above. So the blog's OMI call cannot be recomputed from TIMI flow alone. Whether such cases count as OMI is for DELMIR's operational definition ([#20](https://github.com/the-dr-lazy/delmir/issues/20)) to decide.

### Labels

The Blogger archive has 875 distinct labels; 1,435 of 1,828 posts carry at least one ([Blogger feed](https://hqmeded-ecg.blogspot.com/feeds/posts/summary?alt=json)). Labels are free-form and inconsistent ("LBBB" 52 and "left bundle branch block" 16; "Wide complex tachycardia" 40 and "wide_complex_tachycardia" 23). Counts for the labels that matter here:

| Label | Posts | | Label | Posts |
|---|---|---|---|---|
| OMI | 142 | | false positive cath lab activation | 43 |
| LAD occlusion | 101 | | LAD occlusion vs. benign early repolarization | 42 |
| hyperacute T-waves | 74 | | LVH | 40 |
| Subtle LAD Occlusion | 53 | | LV aneurysm | 35 |
| Subtle LAD | 49 | | PseudoSTEMI | 34 |
| posterior OMI | 42 | | pericarditis | 25 |
| Wellens' syndrome | 31 | | pseudoinfarction | 23 |
| Inferior MI subtle | 31 | | early repolarization | 22 |
| posterior STEMI | 26 | | takotsubo | 20 |
| missed OMI | 26 | | False positive ECG | 20 |
| de Winter's T-waves | 24 | | Myocarditis | 19 |
| left main | 22 | | hyperkalemia | 62 |
| RV MI | 19 | | serial ECG | 34 |
| PM Cardio Queen of Hearts | 57 | | Normal ECG by computer algorithm | 54 |

Grouped by regular expression over labels: 399 posts carry an OMI or occlusion label, 277 an LAD-related label, 153 an RCA, inferior or RV label, 153 an LCx, posterior or lateral label, and 451 a mimic-type label (early repolarization, LVH, pericarditis, hyperkalaemia, aneurysm, takotsubo, pseudo-, false positive, Brugada). The same labels came across as WordPress tags, with slightly higher counts that include posts since June 2025 (OMI 151, LAD occlusion 114; [WordPress tags](https://drsmithsecgblog.com/wp-json/wp/v2/tags?per_page=100&orderby=count&order=desc)). There is no label for "angiography reported", and labels describe ECG patterns more often than outcomes. Labels are useful for stratifying candidates, not for labelling cases.

WordPress categories are editorial workflow ("KG- Done!", "Published Post — in 2026"), not clinical ([categories](https://drsmithsecgblog.com/wp-json/wp/v2/categories?per_page=100)).

## Prior and serial ECGs

71% of sampled case posts carry more than one ECG: a prehospital ECG, a prior baseline, repeat ECGs or post-PCI ECGs. The follow-up belongs to the episode, not to one ECG, and the ECGs within a post can disagree:

- In [Subtle Dynamic T-waves, Followed by LAD Occlusion and Arrest](https://hqmeded-ecg.blogspot.com/2017/03/subtle-dynamic-t-waves-followed-by-lad.html), the first two ECGs show "Unstable Angina". The artery occluded hours later, before the third ECG and the cath.
- In [Quiz post: high lateral OMI](https://hqmeded-ecg.blogspot.com/2023/01/quiz-post-do-either-or-both-of-these.html), an OMI reperfuses and then re-occludes across the serial ECGs.
- In [See this "NSTEMI" go unrecognized](https://hqmeded-ecg.blogspot.com/2023/11/see-this-nstemi-go-unrecognized-for.html), the third ECG shows LBBB, which DELMIR declines ([#5](https://github.com/the-dr-lazy/delmir/issues/5)), while the earlier ones are readable.
- Post-PCI ECGs show reperfusion, not OMI, though they sit in the same post.

So a blog case must name its ECG (the image), its time relative to the angiogram, and whether the post describes the artery as occluded at that moment. The first ED ECG is the natural default. Several posts state that the first ECG was taken before the occlusion, and those cases need care.

## Image types and quality

Images are embedded in post HTML. All 279 images in the 50 sampled posts were hosted on `blogger.googleusercontent.com`; the 42 case posts average 6.2 images each (range 1–16), counting ECGs, rhythm strips, angiogram stills, echo frames and figures together. The blog shows a downscaled copy (`/s640/`, `=w640-h272`); replacing the size segment with `s0` returns the original upload.

Eight original images were fetched one at a time to read their size, and seven were viewed:

| Post | Original size | Kind |
|---|---|---|
| [2012 pericarditis](https://hqmeded-ecg.blogspot.com/2012/06/chest-pain-and-st-segment-elevation.html) | 1765 × 1089 PNG | (size only) |
| [2013 inferior STEMI](https://hqmeded-ecg.blogspot.com/2013/08/chest-pain-in-61-year-old-male-inferior.html) | 2592 × 668 JPEG | phone photo of paper, 3×4 without rhythm strip, edges cropped, partial header |
| [2011 nitroglycerine](https://hqmeded-ecg.blogspot.com/2011/07/wait-until-after-ecg-to-give.html) | 1593 × 547 JPEG | clean screenshot, 3×4, no rhythm strip |
| [2017 subtle dynamic T-waves](https://hqmeded-ecg.blogspot.com/2017/03/subtle-dynamic-t-waves-followed-by-lad.html) | 1000 × 370 JPEG | photo of a screen, 3×4 + II, small |
| [2021 morphine](https://hqmeded-ecg.blogspot.com/2021/12/a-man-his-50s-with-chest-pain-could-you.html) | 2722 × 1155 PNG | clean export, 3×4 + II, calibration pulse |
| [2023 woman in her 70s](https://hqmeded-ecg.blogspot.com/2023/08/a-woman-in-her-70s-with-chest-pain.html) | 3669 × 1809 JPEG | phone photo of a monitor, moiré and glare, 3×4 + II |
| [2023 quiz post](https://hqmeded-ecg.blogspot.com/2023/01/quiz-post-do-either-or-both-of-these.html) | 3120 × 1427 PNG | clean export, 3×4 + II, calibration pulse |
| [2024 WPW + de Winter](https://hqmeded-ecg.blogspot.com/2024/08/60-yo-with-chest-pain-why-abnormal-qrs.html) | 2236 × 629 PNG | clean export, 3×4, rhythm strip cropped |

In every image viewed, patient identifiers and the device header (speed, gain, filters) are cropped away. The calibration pulse, where present, is two large boxes tall (10 mm/mV), and the layout implies 25 mm/s. The text almost never states speed or gain. Some ECGs carry arrows or circles added for teaching. Posts on the current site re-host images under `drsmithsecgblog.com/wp-content/uploads/`, with the original as the largest `srcset` entry (1365 px wide in [a 2026 post](https://drsmithsecgblog.com/wp-json/wp/v2/posts/28230?_fields=content)).

For DELMIR this is a fair test of the digitizer on real-world images: mostly clean renderings, plus a tail of phone photos close to what DELMIR's users will take. It is not a test of phone photos of printed ECGs specifically ([#38](https://github.com/the-dr-lazy/delmir/issues/38)).

## Yields by category

Estimated from the 30-post random stratum (counts are small; read as orders of magnitude):

- **OMI with a derivable culprit vessel:** 10 of 30 posts (≈610 posts). LAD 8, RCA 1, LCx 1. Across the 23 such cases in all 50 posts: LAD 13, RCA 7, LCx 3, with RCA and LCx boosted by the label strata. Labels point the same way: 277 LAD-related, 153 RCA/inferior, 153 LCx/posterior/lateral. Expect LAD to dominate, LCx to be scarce, and many OMIs to be STEMI-negative OMIs, because the blog's theme is OMIs missed by STEMI criteria (labels "missed OMI", "Subtle LAD Occlusion", "Normal ECG by computer algorithm").
- **OMI with a named reason instead of a vessel** (left main, multiple systems, graft, uncertain): 7 of 31 angiography cases, about 1 in 4, three of them uncertain.
- **Not-OMI with a final clinical diagnosis:** 6 of 30 adult, readable posts (≈370): hypokalaemia, pericarditis, fever-induced Brugada, lead misplacement with LVH and hyperkalaemia, takotsubo. Only takotsubo had angiography; the others rest on troponin, echo and the authors' diagnosis. Mimic labels suggest a pool of 400+ candidate posts.
- **Out of DELMIR's intended use:** in the sample, paced ([Paced rhythm](https://hqmeded-ecg.blogspot.com/2015/03/paced-rhythm-is-there-ischemic-st.html)), WPW (two posts, one an OMI), under-18s (two posts), and LBBB ECGs within otherwise readable cases. These would be declined and leave the OMI evaluation, per [#5](https://github.com/the-dr-lazy/delmir/issues/5). The label "modified sgarbossa criteria" (33 posts) and "paced rhythm" (24) mark more.
- **Non-case posts:** 7 of 30 (lectures, commentary, formulas, compilations).

## Enumerating and fetching posts politely

**Where the blog lives.** The Blogger home page now redirects to `https://drsmithsecgblog.com/` with a meta refresh and JavaScript. Old post URLs also redirect to the new home page (their meta refresh points at a malformed URL), not to the matching post ([Blogger post page](https://hqmeded-ecg.blogspot.com/2016/12/persistent-chest-pain-elevated-troponin.html)). WordPress slugs differ from Blogger paths (e.g. `/this-patient-presented-with-alcohol_07/`), so a Blogger URL maps to a WordPress post by date and title only.

**WordPress REST API (primary).**

- `GET https://drsmithsecgblog.com/wp-json/wp/v2/posts?per_page=100&page=N&_fields=id,date,link,title,tags,categories` lists posts; `X-WP-Total: 2052`, `X-WP-TotalPages: 21`. The oldest post is dated 2008-11-07, so the archive is complete ([oldest posts](https://drsmithsecgblog.com/wp-json/wp/v2/posts?per_page=3&order=asc&_fields=id,date,link,title)).
- `GET /wp-json/wp/v2/posts/<id>?_fields=id,date,link,title,content` returns one post's HTML.
- `GET /wp-json/wp/v2/tags?per_page=100&page=N` returns 955 tags with counts (10 pages); `?tags=<id>` filters posts.
- `?search=<terms>` runs full-text search; quoted phrases work. `X-WP-Total` on `per_page=1` gives a count in one cheap request.
- [robots.txt](https://drsmithsecgblog.com/robots.txt) disallows nothing; [sitemap_index.xml](https://drsmithsecgblog.com/sitemap_index.xml) lists three post sitemaps. The API sends `X-Robots-Tag: noindex`, which governs search engines, not API use. No rate-limit headers were seen. The host is Hostinger behind its CDN.

**Blogger feed (archive to 2025-06-15).** `GET https://hqmeded-ecg.blogspot.com/feeds/posts/summary?alt=json&orderby=published&start-index=N&max-results=150` still answers, with `openSearch$totalResults` = 1828. Each page returns only about 54 entries whatever `max-results` says, so page by `start-index` (≈34 pages). `/feeds/posts/default/<postId>?alt=json` returns one post's full content. The feed carries the Blogger labels and is the only source of the original Blogger image URLs, whose `s0` originals may be larger than the WordPress copies (not checked).

**Polite plan.**

1. Metadata first: 21 API pages plus 10 tag pages, sequential, 2 s apart, with a User-Agent naming DELMIR and a contact address, cached under `$DELMIR_DATA/blog/` and refreshed incrementally with `after=<last date>`.
2. Narrow with full-text search and tags to candidates that mention angiography (`angiogram`, `cath`, `culprit`) or carry mimic tags: about 700–900 posts.
3. Fetch each candidate's content once, sequentially, 2 s apart, with retry and backoff (the API was reliable; the Blogger feed and image host dropped TLS connections a few times), and cache it.
4. Fetch images only for cases chosen by hand, at original size, once.

At 2 s per request the whole candidate pass takes under an hour.

## Risks and open questions

- **Selection bias.** The blog selects instructive and hard cases: subtle OMIs, missed OMIs, mimics and false-positive cath lab activations. Its prevalence and difficulty are not those of a consecutive ED population. Sensitivity and specificity measured on it are not clinical estimates. That suits a hard test set, but it should be reported as such ([#24](https://github.com/the-dr-lazy/delmir/issues/24)).
- **The authors' OMI call is not neutral.** The OMI label often rests on the authors' reading of the ECG plus a reperfused (TIMI 3) lesion and troponin. The Queen of Hearts AI, which the blog's authors helped develop, is a label on 57 posts. A model that agrees with the blog agrees with its authors' paradigm.
- **Not-OMI labels are thin.** Most Not-OMIs have no angiography, and some have no troponin. They are clinically labelled, so sensitivity can be measured against angiography-confirmed labels while specificity cannot.
- **Duplicates.** The same ECG reappears in compilations ("Ten (10) Examples of Hyperacute T-waves", [2016](https://hqmeded-ecg.blogspot.com/2016/04/ten-10-examples-of-hyperacute-t-waves.html)) and reposts (the "To Be Published as Re-Post!" category). Case identity needs de-duplication by image hash and history.
- **Prose extraction.** Facts must be read by a physician. A text-mining pass can propose candidates and fields, but phrasings like "100% occlusion" (TIMI 0 implied) or "co-culprits" need judgment.
- **Image provenance after migration.** Whether the WordPress copies of old posts are the same resolution as the Blogger originals was not checked.

## Sampling

- **Frame.** All 1,828 Blogger posts, enumerated from the summary feed on 2026-10-21. One "insert for Queen" post was excluded.
- **Random stratum (posts 1–30).** Seeded random draws (`random.seed(13)`) by era: 6 from 2008–2013, 10 from 2014–2018, 8 from 2019–2022, 6 from 2023–2025. That is 20/33/27/20%, close to the archive's 19/32/28/20%. Estimates above use only this stratum.
- **Label strata (posts 31–50).** 5 posts each whose labels match LAD (`LAD|wellens|de winter|wraparound|diagonal`), RCA/inferior (`RCA|right coronary|RV MI|inferior (MI|OMI|STEMI)|…`), LCx/posterior (`circumflex|obtuse|high lateral|posterior (OMI|STEMI)`), and mimic (`early repol|normal variant|LVH|pericard|hyperkal|aneurysm|takotsubo|…|brugada`). They enrich for OMIs and mimics and are used for edge cases, not for rates.
- **Coding.** Each post's full content came from `/feeds/posts/default/<postId>?alt=json`. It was converted to text and read for the fields below. "Case" means a patient case with at least one 12-lead ECG image. "Angiography" means the post reports coronary angiography findings. "Pre-PCI TIMI" counts only a stated number, not "100% occlusion". "Troponin" means any troponin result.
- **Not checked.** Posts after 2025-06-15 (156 posts on WordPress only) were not sampled.

### Full-text search counts

Posts on `drsmithsecgblog.com` matching each search, from `X-WP-Total` of `/wp-json/wp/v2/posts?per_page=1&search=<q>`, 2026-10-21, out of 2,052 posts. A match is any mention, including commentary.

| Search | Posts | | Search | Posts |
|---|---|---|---|---|
| troponin | 1,198 | | "proximal LAD" | 277 |
| "cath lab" | 995 | | "mid LAD" | 109 |
| angiogram | 693 | | "left main" | 164 |
| angiography | 345 | | "obtuse marginal" | 72 |
| culprit | 449 | | "TIMI 0" | 95 |
| TIMI | 429 | | "TIMI 3" | 85 |
| "TIMI flow" | 52 | | "normal coronar" | 50 |
| "no culprit" | 26 | | MINOCA | 19 |
| "dominant RCA" | 7 | | "right dominant" / "left dominant" | 6 / 7 |

## Appendix: the coded sample

"–" means not applicable; "n" means not reported. Strata as above.

| # | Post | Stratum | Images | Case | Prior or serial ECG | Angiography | Culprit as reported | Segment | Pre-PCI TIMI | Troponin | Category | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [2012-09-15](https://hqmeded-ecg.blogspot.com/2012/09/prehospital-ventricular-fibrillation-in.html) | era 2008-2013 | 4 | y | n | n | – | – | – | n | Not-OMI (hypokalaemia, VF) |  |
| 2 | [2012-06-25](https://hqmeded-ecg.blogspot.com/2012/06/chest-pain-and-st-segment-elevation.html) | era 2008-2013 | 1 | y | n | n | – | – | – | serial | Not-OMI mimic (pericarditis; echo normal) |  |
| 3 | [2008-11-10](https://hqmeded-ecg.blogspot.com/2008/11/st-elevation-mi-in-setting-of-paced.html) | era 2008-2013 | 0 | n | – | – | – | – | – | – | no case (text stub, no image) |  |
| 4 | [2013-03-16](https://hqmeded-ecg.blogspot.com/2013/03/massive-precordial-st-elevation-what-is.html) | era 2008-2013 | 1 | y | n | y | RCA, subtotal | proximal | n | n | OMI |  |
| 5 | [2009-10-12](https://hqmeded-ecg.blogspot.com/2009/10/comment-on-posterior-stemi.html) | era 2008-2013 | 0 | n | – | – | – | – | – | – | no case (commentary) |  |
| 6 | [2012-11-26](https://hqmeded-ecg.blogspot.com/2012/11/full-text-of-left-bundle-branch-block.html) | era 2008-2013 | 0 | n | – | – | – | – | – | – | no case (article link) |  |
| 7 | [2017-11-24](https://hqmeded-ecg.blogspot.com/2017/11/qt-correction-formulas-compared-to-rule.html) | era 2014-2018 | 8 | n | – | – | – | – | – | – | no case (QT teaching) |  |
| 8 | [2017-03-09](https://hqmeded-ecg.blogspot.com/2017/03/subtle-dynamic-t-waves-followed-by-lad.html) | era 2014-2018 | 4 | y | y | y | LAD, 100% | mid, after D1 | n (100%) | serial | OMI | occluded after the first ECGs, which show unstable angina |
| 9 | [2017-07-15](https://hqmeded-ecg.blogspot.com/2017/07/an-elderly-woman-with-dyspnea-asystolic.html) | era 2014-2018 | 5 | y | y | n | – | – | – | n | unlabelled (arrest before cath) |  |
| 10 | [2018-01-12](https://hqmeded-ecg.blogspot.com/2018/01/lecture-updated-subtle-ecg-findings-of.html) | era 2014-2018 | 0 | n | – | – | – | – | – | – | no case (lecture video) |  |
| 11 | [2018-06-24](https://hqmeded-ecg.blogspot.com/2018/06/insuline-overdose-does-this-ecg-help-to.html) | era 2014-2018 | 3 | y | n | n | – | – | – | n | Not-OMI (hypokalaemia) |  |
| 12 | [2014-05-06](https://hqmeded-ecg.blogspot.com/2014/05/a-16-year-old-girl-has-syncope-while.html) | era 2014-2018 | 1 | y | n | y | anomalous coronary, artery not given | – | n | n | OMI, vessel unknown | under 18 |
| 13 | [2017-04-08](https://hqmeded-ecg.blogspot.com/2017/04/8-year-old-with-report-of-syncope-and.html) | era 2014-2018 | 8 | y | n | n | – | – | – | n | Not-OMI (normal variant) | under 18 |
| 14 | [2016-04-23](https://hqmeded-ecg.blogspot.com/2016/04/ten-10-examples-of-hyperacute-t-waves.html) | era 2014-2018 | 12 | n | – | – | – | – | – | – | no case (compilation of 10 linked cases) |  |
| 15 | [2018-10-09](https://hqmeded-ecg.blogspot.com/2018/10/another-inadequate-paper-published-on.html) | era 2014-2018 | 4 | y | n | y | LAD, 100% | proximal | n (100%) | n | OMI |  |
| 16 | [2015-03-18](https://hqmeded-ecg.blogspot.com/2015/03/paced-rhythm-is-there-ischemic-st.html) | era 2014-2018 | 2 | y | prior | n | – | – | – | peak | Not-OMI (heart failure; no WMA) | paced: declined |
| 17 | [2021-12-17](https://hqmeded-ecg.blogspot.com/2021/12/a-man-his-50s-with-chest-pain-could-you.html) | era 2019-2022 | 5 | y | y | y | LCx, 99% | – | TIMI 3 | serial | OMI (spontaneously reperfused) |  |
| 18 | [2022-11-19](https://hqmeded-ecg.blogspot.com/2022/11/what-do-you-think-of-this-ventricular.html) | era 2019-2022 | 7 | y | prior | n | – | – | – | n | Not-OMI (WPW) | WPW: declined |
| 19 | [2020-09-21](https://hqmeded-ecg.blogspot.com/2020/08/implementation-of-abbott-architect-high.html) | era 2019-2022 | 0 | n | – | – | – | – | – | – | no case (troponin pathway) |  |
| 20 | [2021-10-29](https://hqmeded-ecg.blogspot.com/2021/10/a-deadly-alcohol-binge-man-in-his-30s.html) | era 2019-2022 | 5 | y | n | y | left main, 100% | left main | TIMI 0 (label) | initial | OMI, named reason: left main |  |
| 21 | [2022-04-17](https://hqmeded-ecg.blogspot.com/2022/04/what-is-this-st-elevation.html) | era 2019-2022 | 6 | y | y | n | – | – | – | n | Not-OMI (lead misplacement, LVH, K 6.1) | first ECG misplaced: declined |
| 22 | [2020-10-23](https://hqmeded-ecg.blogspot.com/2020/10/a-40-something-male-complains-of.html) | era 2019-2022 | 5 | y | y | y | LAD, 100% | – | n (100%) | initial + peak | OMI |  |
| 23 | [2019-05-19](https://hqmeded-ecg.blogspot.com/2019/05/lvh-with-expected-repolarization.html) | era 2019-2022 | 10 | y | y | y | RCA, "probable ruptured plaque, but not certain" | – | TIMI 3 | serial | MI, culprit uncertain |  |
| 24 | [2019-06-22](https://hqmeded-ecg.blogspot.com/2019/06/st-segment-concavity-is-just-one-small.html) | era 2019-2022 | 6 | y | n | y | LAD (case 2 of 2) | proximal | n | n | OMI (case 1: no outcome) | 2 cases in one post |
| 25 | [2025-01-13](https://hqmeded-ecg.blogspot.com/2025/01/a-50-something-man-with-chest-pain-at.html) | era 2023-2025 | 8 | y | y | n | – | – | – | initial | Not-OMI mimic (fever-induced Brugada) |  |
| 26 | [2024-08-16](https://hqmeded-ecg.blogspot.com/2024/08/60-yo-with-chest-pain-why-abnormal-qrs.html) | era 2023-2025 | 6 | y | y | y | LAD, total | mid | n (total) | initial + peak | OMI | WPW: declined |
| 27 | [2024-04-22](https://hqmeded-ecg.blogspot.com/2024/04/chest-pain-resolved-does-it-need.html) | era 2023-2025 | 7 | y | prior + serial | y | LAD, 80–90% | mid | TIMI 3 | initial + peak | OMI (transient, Wellens') |  |
| 28 | [2024-09-16](https://hqmeded-ecg.blogspot.com/2024/09/how-pause-can-cause-cardiac-arrest.html) | era 2023-2025 | 7 | y | n | y | no significant CAD | – | – | n | Not-OMI mimic (takotsubo) | angiography-confirmed Not-OMI |
| 29 | [2023-11-03](https://hqmeded-ecg.blogspot.com/2023/11/see-this-nstemi-go-unrecognized-for.html) | era 2023-2025 | 12 | y | prior + serial | y | LAD, thrombotic occlusion | – | n (post-PCI TIMI 3 only) | serial | OMI | third ECG has LBBB: declined |
| 30 | [2023-08-30](https://hqmeded-ecg.blogspot.com/2023/08/a-woman-in-her-70s-with-chest-pain.html) | era 2023-2025 | 11 | y | y | y | LAD | proximal | "unknown initial TIMI flow" | initial | OMI |  |
| 31 | [2013-03-09](https://hqmeded-ecg.blogspot.com/2013/03/first-ed-ecg-is-wellens-pain-free-what.html) | label LAD | 4 | y | prehospital + serial | y | LAD, 95% | – | TIMI 3 | peak | OMI (transient, Wellens') |  |
| 32 | [2017-05-03](https://hqmeded-ecg.blogspot.com/2017/05/is-it-important-to-recognize-lvh-pseudo.html) | label LAD | 4 | y | n | n | – | – | – | initial | Not-OMI mimic (LVH; aortic dissection) |  |
| 33 | [2013-01-16](https://hqmeded-ecg.blogspot.com/2013/01/male-in-his-40s-with-chest-pain.html) | label LAD | 3 | y | y | y | "severe subtotal LAD disease and 70% left main"; CABG | – | n | serial | OMI, culprit not named |  |
| 34 | [2018-01-28](https://hqmeded-ecg.blogspot.com/2018/01/is-this-ecg-diagnostic-of-coronary.html) | label LAD | 10 | y | prior + prehospital | y | co-culprits LCx 99% + RCA 95% | – | n | peak | OMI, named reason: multiple systems |  |
| 35 | [2022-09-22](https://hqmeded-ecg.blogspot.com/2022/09/a-man-in-his-50s-with-acute-chest-pain.html) | label LAD | 7 | y | y | y | LAD, 99% | proximal | "no TIMI flow listed" | initial + peak | OMI |  |
| 36 | [2019-11-20](https://hqmeded-ecg.blogspot.com/2019/11/a-man-in-his-30s-with-chest-pain.html) | label RCA/inferior | 12 | y | y | y | RCA, two 95% culprits | mid + distal | "no TIMI flows documented" | serial | OMI |  |
| 37 | [2014-10-30](https://hqmeded-ecg.blogspot.com/2014/10/what-happened-after-pci.html) | label RCA/inferior | 7 | y | prior + serial | y | RCA acute-on-chronic occlusion; prior CABG | – | n | serial + peak | OMI | grafts in the anatomy |
| 38 | [2013-08-21](https://hqmeded-ecg.blogspot.com/2013/08/chest-pain-in-61-year-old-male-inferior.html) | label RCA/inferior | 4 | y | y | y | RCA, 100% | proximal | n (100%) | peak | OMI |  |
| 39 | [2021-10-08](https://hqmeded-ecg.blogspot.com/2021/10/hyperkalemia-is-it-cause-of-this-av.html) | label RCA/inferior | 11 | y | y | y | RCA, thrombotic occlusion; RCA dominant | proximal | n (non-culprit OM: TIMI III) | initial | OMI | the only post stating dominance |
| 40 | [2012-04-02](https://hqmeded-ecg.blogspot.com/2012/04/intermittent-third-degree-heart-block.html) | label RCA/inferior | 4 | y | y | y | RCA, occlusion | mid | n | initial + peak | OMI |  |
| 41 | [2019-07-05](https://hqmeded-ecg.blogspot.com/2019/07/acute-mi-pain-onset-24-48-hours-ago.html) | label LCx/posterior | 8 | y | y | y | case 1 co-culprits RCA + LCx/OM2; case 2 LCx 100% | mid RCA, ostial RPDA, distal LCx, OM2; mid LCx | n | initial + peak | OMI ×2 (one multiple systems) | 2 cases in one post |
| 42 | [2018-03-24](https://hqmeded-ecg.blogspot.com/2018/03/you-have-two-hours-to-save-this.html) | label LCx/posterior | 4 | y | y | n | – | – | – | initial (qualitative) | unlabelled (died before cath) |  |
| 43 | [2016-12-14](https://hqmeded-ecg.blogspot.com/2016/12/persistent-chest-pain-elevated-troponin.html) | label LCx/posterior | 5 | y | n | y | LCx, 100% | proximal to 2 OMs | n (100%) | serial | OMI (normal ECG) |  |
| 44 | [2011-07-10](https://hqmeded-ecg.blogspot.com/2011/07/wait-until-after-ecg-to-give.html) | label LCx/posterior | 6 | y | prehospital + serial | y | D2, 99% | 2nd diagonal | n | initial (qual.) + peak | OMI (LAD system via branch) |  |
| 45 | [2023-01-12](https://hqmeded-ecg.blogspot.com/2023/01/quiz-post-do-either-or-both-of-these.html) | label LCx/posterior | 16 | y | y | y | case 1 LAD, 99%; case 2 no cath | mid | "pre-intervention TIMI flow not listed" | serial | OMI + Not-OMI (serial hs-TnT 9 ng/L) | 2 cases in one post |
| 46 | [2018-09-29](https://hqmeded-ecg.blogspot.com/2018/09/a-dialysis-patient-with-nonspecific.html) | label mimic | 11 | y | prior + serial | y | SVG to OM1, 100% | graft anastomosis | TIMI 0 | serial + peak | OMI, named reason: graft |  |
| 47 | [2013-07-31](https://hqmeded-ecg.blogspot.com/2013/07/chest-pain-in-male-in-his-20s-inferior.html) | label mimic | 8 | y | y | y | RCA, 99%; coronary aneurysm | proximal to posterolateral branch | "TIMI flow not reported" | serial + peak | OMI |  |
| 48 | [2012-08-24](https://hqmeded-ecg.blogspot.com/2012/08/pericarditis-or-anterior-stemi-qrs.html) | label mimic | 2 | y | y | y | LAD, 80%, wraparound | mid | n | peak | OMI |  |
| 49 | [2018-08-16](https://hqmeded-ecg.blogspot.com/2018/08/a-simplified-formula-discriminating.html) | label mimic | 0 | n | – | – | – | – | – | – | no case (formula) |  |
| 50 | [2017-06-04](https://hqmeded-ecg.blogspot.com/2017/06/huge-st-elevation-in-v2-and-v3-what-is.html) | label mimic | 6 | y | y | n | – | – | – | serial (all undetectable) | Not-OMI mimic (pseudo-STEMI, tachycardia) |  |
