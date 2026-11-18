# Lotline: architecture and dataset research prompt (v3.1, 17 Nov 2026)

## Revision v3.1 — reconciliation, 17 November 2026 (not part of the prompt text below)

This file holds decisions, rationale and evidence rules. Business rules are owned by the PRD (`PRD_v0_3.md`, section 9), the schema and workflows by the System Design (`SYSTEM_DESIGN_v1_2.md`), roles, privileges and isolation by Security (`security-v0_4.md`). Decision log: `LOTLINE_DECISION_LOG.md`. Changes from v3:

| # | Change | Finding |
|---|---|---|
| 1 | D2 extended by one service: a **DB-less `Vision` container**; the InferenceWorker has no table privileges and uses SECURITY DEFINER functions. Owner-approved 17 Nov 2026 (Option A). | LL-01 |
| 2 | R3: version 1 requires `Re = Ac + 1` for every class (was "Re greater than Ac"), matching Security BR-05 and System Design 8.2. | LL-06 |
| 3 | R6: the override policy of Security 0.3 (only an ACCEPT or REJECT decision; HOLD and ESCALATE never; Admin cannot; second supervisor for a high-risk override). | LL-03 |
| 4 | R13: `critical_nonvisual_status` gains `failed`, which gives REJECT (confirmed by the owner 17 Nov 2026). Set only by a Supervisor. | LL-05 |
| 5 | Section H order: the REJECT tier now also covers the failed critical non-visual check; the ESCALATE tier gains E4; the HOLD tier gains H4 to H6. The "counts only grow" argument was re-checked and corrected. The order itself is **confirmed** by the owner. | LL-02 |
| 6 | Manual mode: an inference job never blocks a view that already has a human review. | LL-10 |
| 7 | New evidence note on RF-DETR checkpoint loading (a lead, not verified for the pinned version). | LL-01 |

Open items: DP-OQ-1 (evaluate ESCALATE before REJECT in a `highest_class_only` corner), OV-10 (a decision rejected for a failed critical non-visual check is not overridable). Both are PROPOSED or PENDING APPROVAL in the decision log.

---

# Lotline: architecture and dataset research prompt (v3.1)

Copy everything below the line into the model. Do not add application code to the request.

---

You are a senior computer-vision engineer, a senior software architect, and a garment QC lead who has applied ISO 2859-1 on a knitwear floor. Produce a research-backed architecture for Lotline. Be independent: where a fixed decision in section D conflicts with something you verify, say so and show the evidence. Do not silently change a decision, and do not simply agree. Do not write the application.

## A. How you must work

A1. **Capability check first.** Open your reply by stating whether you can (a) open web pages, (b) run code or shell commands, (c) download files. If you cannot open pages, do not fill the dataset table from memory. Output a verification checklist instead (record, URL to open, fields to read) and say that you did so.

A2. **Tags.** Every claim of substance carries one tag:
- [V] verified on a page you opened in this session. Give the URL. Paraphrase the page; quote at most a few words.
- [L] lead: seen in a search snippet, a listing, or in section C below, but not opened by you.
- [A] assumption. [R] recommendation. [NS] not stated on the page you opened. [C] arithmetic you computed; show the formula.

Search snippets are leads, never evidence. Never tag a number [V] unless you read it on the page. An untagged claim is an error. Do not invent dataset statistics, licenses, sampling numbers, clause numbers, benchmark results, or compliance claims.

A3. **Leads.** Section C lists records pre-checked on 15 Nov 2026. "Opened" means the full page was read; "snippet" means a search result only. Re-open each one. If the page now differs (Mendeley records are versioned), the page wins; say what changed and pin the version you used.

A4. **Two messages.** Message 1 delivers answer sections 1 and 2 (see section L), then stops with the words READY FOR PART B. Message 2, after I reply "continue", delivers sections 3 to 13. If space runs short, drop prose, never tags or caveats. If you cannot finish, stop at a section boundary and list the sections not delivered.

A5. **Diagrams.** Valid Mermaid only (flowchart, sequenceDiagram, erDiagram, stateDiagram-v2). Quote labels that contain parentheses or punctuation. Use the canonical component names in section K in every diagram.

A6. **Example numbers.** Every (n, Ac, Re) in any example, test, or payload is a placeholder labelled "DEMO PLAN, not from any standard". Do not present sampling values recalled from memory.

## B. Product and context

**Product.** Lotline helps a knitwear QC lead decide a buyer sample. It is not a fabric-scanning machine, not smart glasses, and not a factory ERP.

The lead photographs sampled garments on a phone. A detector proposes visible defects. A person confirms, edits, or rejects each proposal and can add a miss. Confirmed results become counts of defective garments. A deterministic sampling engine compares those counts with the plan's accept and reject numbers.

**Outcomes.**
- ACCEPT or REJECT: only when the sample is complete, every required view of every sampled unit has a human-confirmed result, and the sampling rule is met or broken.
- HOLD: the sampling rule cannot be applied yet.
- ESCALATE: a person must decide because the case is outside the system's competence.

**Version 1 scope.** One knit family (tee or polo), phone photos, table or hanging, ambient light, one organization. Out of scope: line-scan, worker surveillance, all garment types, native apps, multi-factory SaaS, microservices, Kubernetes.

**Detector scope [R].** The detector is trained for surface defects on the body panels of plain-colour knit garments. Seam and hem defects (for example skipped stitch) and shade band are entered by a human reviewer in version 1. Reason: no open finished-garment dataset with boxes has been found (section C7), so the public data cover fabric surfaces only.

**Sample unit and views [A].** One sample unit is one garment. Each unit has required views: front and back, configurable, plus optional detail shots. A view is *reviewed* only after a human sets one of two states: `confirmed_clean` (the reviewer explicitly marks the view clean) or `confirmed_defects` (one or more confirmed defects). A view with zero model proposals is `pending`, not clean. A unit is *complete* when every required view is reviewed.

**Competition context.** The target is the International AI Builders Congress 2026 (CloudCamp Bangladesh). Per a third-party listing [L], it runs Saturday 26 Dec 2026 at Daffodil International University (Savar, Dhaka); the Idea to Unicorn track is for teams of 3 to 5. The official page, https://cloudcampbd.com/ai-builders-congress, is client-rendered and could not be read. Open it. If you cannot read it either, say so. Do not invent a judging rubric. Goal: finish in the top two. Team: 4 people. Today is 15 Nov 2026, so 41 days remain [A: confirm the date on the official page]. Every recommendation must fit that budget, and you must say what you cut.

## C. Leads (not claims)

**C1. BDFD9 (opened).** https://data.mendeley.com/datasets/z49cc7zvfc/1, DOI 10.17632/z49cc7zvfc.1. The page states: published 18 Aug 2026, version 1; 1,088 *knit and woven fabric photographs* captured on production lines at 4 Bangladeshi garment factories with a Google Pixel 6 and an iPhone 14 Pro Max under ambient factory light; YOLOv8 format; nine classes (DropStitch, Hole, Horizontal Mark, Knot, Oil Spot, Setup, Slub, Vertical LineMark, Yarn Dust); split train 775, valid 208, test 105; organized by class folder with images/ and labels/ per class; images with several defect types are duplicated across the relevant class folders; dataset_metadata.csv lists split, classes, and box count; CC BY 4.0; American International University-Bangladesh; five contributors. Not captured: file list and sizes, resolution, per-image knit-versus-woven flag, garment id, lot id, any paper. The subject is fabric on production lines, not finished garments. Open questions: how many images are duplicated, whether 1,088 counts duplicates or unique photos, and whether any physical photo sits in two splits.

**C2. AITEX AFID (opened).** https://www.aitex.es/afid/. The page states: 245 images of 7 fabrics; 140 defect-free (20 per fabric); 105 defective; 4096x256 pixels; one mask per defective image; 12 named defect codes; .7z download links; a note that links become available after the paper's publication; citation requested: Silvestre-Blanes et al., AFID, AUTEX Research Journal No. 4, 2019. Not stated: license, woven versus knit (defect names such as broken pick and cut selvage suggest woven), capture setup. The paper is not yet opened.

**C3. MVTec AD 2 (snippets).** Paper: Heckler-Kram et al., IJCV 134(4), 2026, DOI 10.1007/s11263-026-02743-0; arXiv 2503.21622. Eight scenarios, more than 8,000 images. The dataset page https://www.mvtec.com/company/research/datasets/mvtec-ad-2 says commercial use is not allowed. The test ground truth sits behind an evaluation server. To check: exact license name, whether any scenario is textile, which labels are public. The original MVTec AD is a separate record; open its page separately.

**C4. DAGM 2007 (snippets).** Zenodo record https://zenodo.org/record/8086136 (about 2.9 GB, ten archives, "newer version available" banner). The Heidelberg page https://hci.iwr.uni-heidelberg.de/node/3616 says CC BY 4.0, synthetic textured surfaces, 8-bit grayscale PNG; its request form is closed and points to Zenodo. Labels are weak (ellipse regions). To check: which Zenodo version is current; the license shown on Zenodo.

**C5. TILDA (snippets).** https://lmb.informatik.uni-freiburg.de/resources/datasets/tilda.en.html: 3,200 grayscale TIF images (768x512), 8 textile kinds, 7 error classes plus a no-error class, 50 images per class, one ASCII file per image describing the error (no boxes), version 1.0 from 1996. License not seen. Derived record TILDA-OBB, Mendeley DOI 10.17632/8y46pm2m6y.1: 1,562 images, 5 defect classes, oriented boxes; license not seen; its terms depend on the upstream terms.

**C6. RAW-FABRID (opened: Mendeley page and data paper).** Mendeley https://data.mendeley.com/datasets/db6g85xsyg, DOI 10.17632/db6g85xsyg.1, published 1 Apr 2026, Universitat Politecnica de Valencia, CC BY 4.0. 709 grayscale 1792x1024 PNG images (505 defect-free, 204 defective, per the paper); 204 masks; 256x256 patches in MVTec layout (train/good 14,196; test/good 4,969; test/defect 687); COCO JSON with boxes and polygons. Data paper: Data (MDPI) 11(5), article 116, 12 May 2026, https://www.mdpi.com/2306-5729/11/5/116; it describes a **woven** 100% cotton plain-weave base, Basler line-scan camera, controlled LED light. Peer-review status [NS]. Same author group as AFID, so the two are not independent evidence. Domain: woven, line-scan; use as a negative control only.

**C7. Knit-specific and Bangladeshi candidates.**
- **ISL-Knit (paper opened).** Das Gupta et al., Heliyon, Sep 2024, https://pmc.ncbi.nlm.nih.gov/articles/PMC11639326/. Paper states: 3,375 images (3,018 faulty, 357 defect-free); seven classes (Loop Mark, Needle Mark, Set Up, Oil Spot, Hole, Contamination, Yarn Missing); grey and dyed knit *fabric*, mostly single jersey, from knit dyeing industries in Bangladesh; smartphone captures (average about 3970x3143 pixels); YOLO TXT labels from LabelImg; three annotators plus verification; hosted on Kaggle. **Dataset license [NS]** (the article is CC BY-NC 4.0; that is not the dataset's license). The Kaggle page has not been opened. Best match so far on knit, phone, and YOLO labels, but fabric in knitting and finishing sections, not finished garments.
- **FabriD (Mendeley page opened).** https://data.mendeley.com/datasets/vncdwps24r, now version 3 (1 Nov 2026), DOI 10.17632/vncdwps24r.3; version 2 was seen earlier, so pin the version. University of Information Technology and Sciences, Dhaka; CC BY 4.0. 2,407 images: Needle Mark 467, Hole 459, Stains 407, Missing Yarn 454, Defect-free 620 (version 2 said 624). Version 3 text lists class labels, polygons, and masks (version 2 also named boxes). "Cotton fabrics". Not stated: capture device, garment versus swatch, knit versus woven, file list, annotation file formats. Class names match Lotline's type list most closely.
- **FabricSpotDefect (article opened).** https://pmc.ncbi.nlm.nih.gov/articles/PMC11648198/, Mendeley DOI 10.17632/6574nhzm8x.1. 1,014 original images split 643/219/152; one class, "Spot" (stains, discoloration, oil marks); three Samsung phones; COCO labels for originals, YOLOv8 and COCO for the augmented set; augmentation applied after splitting and only to training data (1,929 training images after augmentation), per the authors. The article is CC BY 4.0; the dataset license on the Mendeley page was not read. The authors' own counts are internally inconsistent in places.
- **FabDetector (README opened).** https://github.com/sumaiyahoque90/Automated-Fabric-Defect-Detection. Images from APT Sweater Limited, Gazipur; 1,887 box instances; five classes (Defect-Free, Spot, Hole, Knot Slub, Yarn). The README says the dataset is not in the repository and gives no release link; no license stated. Not usable as stated; the authors could be asked [A].
- **Edge-detection preprint (opened).** https://arxiv.org/pdf/2608.14727. Reports its own results: a 1,195-image in-house set (195 real captures from a Bangladesh garment factory, 1,000 synthetic images), a Roboflow aggregate "dfab" (4,188 images, four classes, labelled Public Domain while stating that it incorporates ISL-Knit and other subsets under their own licences), YOLOv5n mAP@0.5 of 0.742, and an autoencoder screening stage that falsely flagged 113 of 229 normal images. Treat these as the authors' claims, not as verified performance. The dfab label is a mirror trap (see below).
- **Snippet only.** "Fabric Defect" (United International University), DOI 10.17632/y62b4pfyz2.1: 2,468 images, six classes, boxes, contact the authors for access (not an open download). StitchingNet, DOI 10.17632/6tdthsjgfc: 14,565 sewing-stitch images, lab sewing setup, ten defective classes including skipped stitch; large domain gap. Mendeley DOI 10.17632/663j22s43c.3 repackages AITEX and Kaggle sets.
- **Mirror traps.** A mirror's license label never overrides the original authors' terms. Always record the original source's license.
- **Finished garments.** No open dataset of finished knit garments with box labels has been found so far. Keep searching; if you find none, write "none found" and list the queries you ran.

**C8. Standards, practice, tooling, platform.**
- ISO 2859-1 has a third edition dated 2026-01. The ANSI preview (https://webstore.ansi.org/preview-pages/ISO/preview_ISO+2859-1-2026.pdf) was opened: it shows the contents list only, including "Classification of nonconformities" (4.2), "Classes of nonconformities or nonconforming items" (7.4), and "Special reservation for critical classes of nonconformities" (7.5), and no clause text. Clause numbers differ between editions. Record the edition and clause behind every procedural statement. Do not quote the standard.
- Mixed AQLs (Qarma support article, opened): one common reading follows each AQL's arrow without moving the sample size; a strict reading moves to a larger code letter and may not settle; the article says the combining clause (cited as 10.3 in an earlier edition) does not resolve the case and calls its own compromise inconsistent with the statistics. Secondary source.
- Isolated lots (qualityinspection.org, opened): AQL schemes were designed for a continuing series of lots; ISO 2859-2 covers isolated lots with a limiting quality (LQ) approach; applying AQL to an isolated lot can let a poor lot through. Secondary source.
- Garment practice (apparel quality chapter, opened; secondary): critical means hazard or legal breach; a garment with two or more major defects counts as one major defect; severity of the same defect can change with its zone on the garment (zones I to III). Global Sources (opened; secondary): one sample is checked for all defect classes, each class has its own accept and reject points, and a pass is a statistical inference, not a guarantee that every unit is defect-free.
- Ultralytics license page https://ultralytics.com/license [L]: using YOLO code, models, or trained models requires AGPL-3.0 compliance (publish the whole project's source, including when used over a network) or an Enterprise License, even when training from scratch or for internal use.
- RF-DETR licensing (Roboflow page opened, https://roboflow.com/model-licenses/rf-detr): detection sizes Nano, Small, Medium, Large are Apache 2.0; Atto, Femto, Pico, XL, 2XL fall under a Platform Model License that needs a Roboflow plan. Training format support and accuracy on this domain are not verified.
- Next.js static export (docs opened): the App Router export does not support cookies, rewrites, redirects, headers, proxy (middleware), or Server Actions.
- CVE-2025-55182 (CERT-EU advisory opened, https://cert.europa.eu/publications/security-advisories/2025-041/): CVSS 10, unauthenticated remote code execution in React Server Components packages (versions 19.0 to 19.2.0; fixed in 19.0.1, 19.1.2, 19.2.1); Next.js App Router is among the affected frameworks.
- getUserMedia (MDN opened): available only in secure contexts (HTTPS, localhost, file); in insecure contexts the media-devices object is undefined.
- OWASP Password Storage Cheat Sheet (opened): Argon2id first choice, minimum 19 MiB memory, 2 iterations, parallelism 1; bcrypt only for legacy cases, work factor at least 10, 72-byte input limit.
- PyTorch serialization docs (opened): from version 2.6 `torch.load` defaults to `weights_only=True`, which narrows but does not eliminate risk; do not load untrusted checkpoints; save and load state dicts.

## D. Decisions already made after review (fixed unless you cite a verified finding)

D1. **Frontend: React + TypeScript + Vite single-page app; no Next.js.** FastAPI is the only backend. [R, with these grounds]
- The product is a login-gated tool with no SEO or server-rendering need [A].
- With Next.js, the only variant that keeps FastAPI authoritative without a second server runtime is static export, and that variant drops cookies, rewrites, redirects, headers, proxy, and Server Actions [V]. That leaves a Vite-equivalent app with extra constraints.
- A Next.js server runtime next to FastAPI gives two places that could enforce authorization and a larger attack surface; a critical, unauthenticated RCE in React Server Components affected the Next.js App Router in 2025 [V]. It was patched; the point is surface area for a four-person team, not a ban.
- Serve the built static files and proxy `/api` to FastAPI behind one reverse proxy (Caddy or nginx [A]). One origin means cookie sessions with no CORS.
- Phone camera streams need HTTPS or localhost [V]. A plain file input with the capture attribute is the fallback [A]. Terminate HTTPS at the proxy.
- Reconsider Next.js only if a server-rendered public page becomes a requirement.

D2. **Backend and runtime.** FastAPI, SQLAlchemy, and Alembic migrations [A]. Compose services: Proxy, API, InferenceWorker, **Vision**, Postgres, plus an image volume (ImageStore). No message bus. Inference jobs live in a Postgres table; the InferenceWorker claims them with `SELECT ... FOR UPDATE SKIP LOCKED` **inside a SECURITY DEFINER database function** (the worker's login role holds no table privilege) [A]. `Vision` is a separate container with no database access that the worker calls over an isolated internal network; the API has no route to it. The API stays up when the worker is down; job status is visible in the UI. [v3.1: Vision added by the owner-approved Option A, 17 Nov 2026.]

D3. **Detector.** A closed-set object detector whose classes are limited to those backed by labels in hand: hole, oil_stain, needle_line, dropped_stitch [R]. Skipped stitch, shade band, and other are human-entered in version 1. Shipped model must be license-clean: default RF-DETR Small or Medium (Apache 2.0 [V]); convert YOLO or polygon labels to the format the library needs [A]. Fallback if RF-DETR fails to train within 3 working days [R]: Ultralytics YOLO, with the whole repository published under AGPL-3.0 [V]. No RT-DETR sweep, no anomaly model in version 1.
- *Evidence note, 17 Nov 2026 [L]:* the RF-DETR reference documentation, seen only as a search excerpt, describes a `trust_checkpoint` option that defaults to `False` and allows a full-pickle fallback when `True`, and states that its checkpoint-loading path passes trust internally; older RF-DETR code used `weights_only=False`. Which behaviour the **pinned** version has is **not verified** [A]; treat checkpoints as code you trust and contain the detector (Security AI-05, AI-18, test T-88).

D4. **Training data policy.** Public fabric sets are for transfer learning and for a public-domain test column. Evidence for the shipped model comes from staged garments. Union for training is allowed only after perceptual-hash deduplication, license checks per source, and a per-source holdout; never publish one pooled metric. Own garment photos are mandatory because no public set shows finished knit garments [R].

D5. **Dataset use [R].** Primary public set: BDFD9 (CC BY 4.0 verified, phone photos, YOLO labels, Bangladeshi factories), with its 105-image test split as the only public phone-photo test column. ISL-Knit becomes primary only if its dataset license is confirmed on its Kaggle page; until then it is excluded. Supplementary: FabriD version 3 (CC BY 4.0; covers needle mark, missing yarn, stain, hole, and defect-free images; capture device unknown). Negative controls, never trained on: AFID, RAW-FABRID (woven, line-scan), MVTec AD 2 (non-commercial).

D6. **Plan and decision logic.** One n per plan, because one physical sample is inspected for all classes [V: Global Sources]; (Ac, Re) per class. Decision order and conditions are in section H. A zone-aware clause mapping, a critical non-visual attestation, and honest outcome wording are required (rules R4, R13, R14).

D7. **Security baseline.** Argon2id at or above the OWASP minimum [V]; HttpOnly, SameSite session cookie with a CSRF token on unsafe methods [R]; `organization_id` on every table with composite foreign keys so rows cannot reference another organization [R]; upload checks by magic bytes, decode, re-encode, pixel-count limit [A]; torch 2.6 or newer, load only checkpoints the team produced, never a user-supplied file [V].

D8. **Cuts to fit 41 days [R].** The report is an HTML page the browser prints to PDF (no PDF library). The clause mapping is seeded from a JSON file in version 1; the editing screen is version 2. No Bangla UI. No native app. No second detector. The staged shooting and labelling schedule is the long pole and starts in week 1.

## E. Rules that override anything else

R1. **AQL is a quality-level index, not a percent allowance.** AQL 2.5 does not mean "2.5% of the lot may be defective." The operative numbers are sample size n, acceptance number Ac, and rejection number Re.

R2. **Count defective units, not bounding boxes or cartons.** One garment is one sample unit. The plan carries a required `counting_mode`. `highest_class_only`: a garment with several confirmed defects counts once, in its highest confirmed class. `every_class`: it counts in each class where it has a confirmed defect. A secondary source says a garment with several major defects counts as one major [L]; it does not settle the major-plus-minor case. Which mode the standard or the buyer requires is open. A production plan must set the mode explicitly; the demo plan sets `highest_class_only` and is labelled as an assumption. The report prints the mode.

R3. **Three classes, three comparisons, one sample.** Critical, major, and minor are scored separately against the same n. Any class whose count reaches its Re rejects the lot. A standard accept requires all three classes at or under their Ac. The engine rejects any configuration where n is missing, `counting_mode` is unset, or Re is not equal to Ac + 1 for a class (version 1 is single sampling, so no count falls between Ac and Re). For single sampling the tables normally give Re = Ac + 1 [A: verify in a licensed copy]. [v3.1: "not greater than Ac" became "not equal to Ac + 1"; the guard and the database constraint use the stricter rule.]

R4. **Severity is not a model output.** After a person confirms the defect type, map it through the buyer's clause list. The mapping key is (type, zone, size band): the same defect can be major in a front zone and minor in a back zone [L], so the confirmed row records a zone chosen from the buyer's zone list, and a size band when the clause needs one. If the mapping has no entry, do not guess; ESCALATE. Do not train critical, major, or minor from pixels. *Provisional routing lookup:* the system may look up a predicted type in the clause list only to set review priority and ESCALATE routing. That lookup is never stored as a severity, never shown as a severity, and never counted.

R5. **HOLD and ESCALATE are not ISO outcomes.** Under single sampling, ISO 2859-1 ends in accept or reject once the sample is complete and the counts are real. HOLD and ESCALATE are Lotline states. A failed model, a blurry photo, or an empty detection list is not a defect count of zero.

R6. **The model cannot bypass the plan.** Only human-confirmed defective-unit counts enter Ac and Re. The client never sends counts; the server computes them from stored confirmed rows. A supervisor override stores who, when, and why, does not delete the system recommendation, does not change any confirmed count, and appears on the first line of the report as OVERRIDDEN. [v3.1: only an ACCEPT or REJECT decision can be overridden; HOLD and ESCALATE never are; an Admin cannot override; an override to ACCEPT needs a second, different supervisor (PRD 9.6, Security 5.6).]

R7. **Do not reproduce the sampling tables.** ISO 2859-1 and ANSI/ASQ Z1.4 are copyrighted and secondary blogs disagree. Describe the procedure only: lot size and inspection level select a code letter; the letter and the AQL select n, Ac, and Re; an arrow in the table can change n; if n is at least the lot size, inspect 100%. The engine takes n and per-class (Ac, Re) as configuration entered from a licensed copy or the buyer's order. Do not publish a reconstructed numeric table. Open until read from a licensed copy: (a) how n is set when classes carry different AQLs (secondary sources disagree and call the standard ambiguous); (b) how the critical class is treated, given that zero tolerance is buyer policy and the third edition has a clause on special reservation for critical classes.

R8. **Default plan, an assumption, not a fact** [A]: single sampling, normal inspection, General Inspection Level II; critical AQL 0 interpreted as Ac = 0, Re = 1 (one critical defective unit fails); major AQL 2.5; minor AQL 4.0. Tightened and reduced switching are out of version 1. Repeat this assumption wherever the plan appears. Any demo plan is labelled "DEMO PLAN, not from any standard".

R9. **No statistical guarantee without a protocol.** Do not claim conformal coverage, calibration, or "ISO-compliant AI". Say "implements the single-sampling procedure with entered parameters". Without a calibration set from the same distribution, the UI says uncalibrated.

R10. **Random draw.** Sampling plans assume units drawn at random from the lot. Lotline cannot verify that. It records the selection method as self-declared and prints it on the report. Optional helper [R]: generate random unit positions from the lot size and store the seed.

R11. **Empty is not clean; failure is not zero.** Zero proposals leaves a view `pending`. A human must mark it `confirmed_clean`. Inference failure leaves the view `pending` as well.

R12. **Exclusions.** An image may be excluded only with a logged reason (duplicate checksum, not an image, unreadable). An excluded view makes the unit incomplete until a replacement view is uploaded. An image that has an open model proposal cannot be excluded unless a human first rejects that proposal.

R13. **Critical checks that a photo cannot make.** Critical defects in garments are mostly not visible in a photo (hazard or legal breach, for example needle fragments) [L]. Each lot carries `critical_nonvisual_status`: `pending`, `done`, `not_required`, or `failed` (set by a named supervisor, audited; a note is required for `failed`). The outcome cannot be ACCEPT while it is `pending`, and it is REJECT (`REJECT_CRITICAL_NONVISUAL_FAILED`) while it is `failed`, even if the sample is incomplete. The report states that the critical class covers visible defects only. [v3.1: `failed` added; confirmed by the owner 17 Nov 2026.]

R14. **Outcome wording.** ACCEPT means "the sample met the plan". It is a statistical inference, not proof that the lot is defect-free [V: Global Sources]. AQL schemes were designed for a continuing series of lots; for an isolated lot the standards family offers a limiting-quality approach [L], so the report says which plan was applied and does not claim more. For orientation, under a binomial approximation a DEMO PLAN of n = 8, Ac = 0 accepts a lot with 10% defective units about 43% of the time [C: (1-0.10)^8 = 0.430]. Version 2 shows an operating-characteristic curve computed only from the entered n and Ac, with no copyrighted table.

## F. Dataset research (do this before the architecture)

Search official pages, papers, Hugging Face dataset cards, Mendeley, Kaggle, Zenodo, Roboflow Universe, and GitHub. Open the page. Search specifically for finished-garment datasets (t-shirt, polo, sweater, knitwear) and say "none found" if so. For each candidate record fill these columns, tagging every cell:

1. Name, version, and URL opened.
2. Subject: finished garment, fabric swatch or panel, fabric roll or line-scan, other.
3. Knit, woven, or not stated.
4. Image count as stated, and whether augmented copies are inside that count.
5. Classes, and a crosswalk to Lotline's type list (G4). Leave a class unmapped rather than force a match.
6. Normal (defect-free) samples present?
7. Annotation type and format (boxes, polygons, masks, image-level, text).
8. Resolution and capture setup (device, line-scan versus phone, lighting, distance).
9. License wording for the dataset itself (not the article), paraphrased, plus the original source's license for any mirror.
10. Access route and download test level: D0 not tested; D1 link resolves; D2 file listing or archive header seen; D3 downloaded and file count matched. State which level you reached and what tool you used.
11. Gap versus a phone photo of a finished knit garment in a Bangladeshi factory.

Open at least C1 to C7, then keep anything better you actually find.

**Scoring** (weights sum to 100). Rate each criterion 0 to 5 from verified columns only; score = weight x rating / 5.

| Criterion | Weight | Rating anchors [R] |
|---|---|---|
| Domain relevance | 25 | 5 phone photos of finished knit garments; 4 phone photos of knit fabric in a factory; 3 phone photos of any fabric; 2 controlled-camera knit fabric; 1 woven or line-scan; 0 non-textile |
| Annotation usefulness | 20 | 5 YOLO or COCO boxes matching Lotline types; 4 boxes with other classes; 3 masks or polygons convertible to boxes; 2 image-level labels; 0 none or text only |
| Capture diversity | 15 | one point per stated axis: sites, devices, lighting, fabrics or colors, distances (max 5) |
| Size | 10 | unique originals, not augmented: 5 at 2,000 or more; 4 at 1,000; 3 at 500; 2 at 200; 1 below 200; 0 not stated |
| Label quality | 10 | 5 multi-annotator or stated protocol plus your own spot check; 3 single annotator stated; 1 automatic or weak; 0 not stated |
| License fitness | 10 | judged for a public demo and for later commercial use, because the track is startup-framed: 5 CC BY or more permissive; 3 research or non-commercial only; 0 not stated, contact-for-access, or mirror-only |
| Download works | 10 | D3 = 5 points of rating, D2 = 4, D1 = 2, D0 = 0 |

Rule: an unknown field gets rating 0 and the row is flagged *unverified*. Every row with all columns verified ranks above every flagged row, whatever the score. Say so in the table.

## G. Required recommendations

G1. A primary public set, or none (start from D5; confirm or overturn it with evidence). G2. One supplementary set. G3. Whether an anomaly model adds a signal the detector lacks (the opened preprint in C7 reports a high false-flag rate for an autoencoder stage; BDFD9's page lists defect classes only and no normal images). G4. A crosswalk from the chosen public classes to Lotline's type list (hole, dropped stitch, skipped stitch, needle line, oil stain, shade band, other), marking types with no public labels. G5. Union rules (D4). G6. How to collect your own images.

**Evaluation hygiene.** About 150 staged knit photos may debug the demo; they are not evidence of factory performance. Report public, staged, and factory numbers in separate columns. Split by garment id and lot id, never by filename. For public sets without ids, cluster near-duplicates with a perceptual hash and keep each cluster in one split. Augmentations, adjacent video frames, cut-and-paste copies, and multi-class duplicates stay in one split. A garment's clean photo and its defective photo must not straddle train and test.

**Own collection protocol.** Fixed type list a lead can recognize (hole, dropped stitch, skipped stitch, needle line, oil stain, shade band, other). Severity left blank until a lead or a written clause assigns it. Known-good garments. At least two lights and two distances. No faces and no badges. Record garment id, lot id, session id, and phone model in a manifest. Dual-annotate a subset, state its size [R], compute class agreement and box overlap agreement, and keep the disagreements. Freeze the staged test set by hashing its manifest and tagging the repository. Factory photos later are a new test domain; never add them to the frozen staged set. If no factory access exists before the congress, say "no factory evidence" in the report and the pitch.

## H. Architecture to design

Modular monolith: one Python API and one web app, served through one proxy. A separate inference process is allowed only so the site stays up when the model is down: the detector runs in its own database-less container (`Vision`) called only by the `InferenceWorker`, which has no table privileges and reaches PostgreSQL through SECURITY DEFINER functions (v3.1, Option A). No message bus.

Design these modules, each with the invariant it protects:

- **Identity.** Email and password, roles admin / inspector / supervisor, one organization, authorization on every write.
- **Lots.** Lot code, product, color, lot size, buyer, status, `critical_nonvisual_status`. A lot has many sample units; a unit has views. A decided lot is locked; reopening needs a supervisor and creates a new decision.
- **Plan.** Stores the R8 assumption, one n, per-class (Ac, Re), `counting_mode`, and the edition of the source. Pure function. Unit-tested. No import of the vision code.
- **Capture.** Phone-browser upload. Reject non-images and oversized files. Garment id, side (front / back / detail), checksum. A duplicate checksum is flagged (linked to the original), not counted twice. Uploads are idempotent per lot and checksum.
- **Vision.** Detect and localize. Return class and score. No severity head. Every prediction stores the model version. Runs in its own container with no database and no image volume; the model file is mounted read-only and hash-verified before it loads.
- **Review.** Confirm, edit, reject, or add a box; choose zone; mark a view `confirmed_clean`. Severity exists only on the confirmed row, from the clause mapping. Edits use optimistic concurrency (a version field) so two reviewers cannot overwrite each other [R].
- **Uncertainty.** Blur or darkness, low score, or an optional anomaly flag marks the view for review. It does not change Ac.
- **Decision.** Append-only; every computation stores a hash of the confirmed-defect snapshot it used. Evaluate in this order; the first match wins:
  1. HOLD if the plan is missing (`HOLD_PLAN_MISSING`) or invalid (`HOLD_PLAN_INVALID`: n absent, a class with Re not equal to Ac + 1, `counting_mode` unset). If n is at least the lot size, the engine sets n to the lot size (100% inspection).
  2. REJECT if (a) `critical_nonvisual_status` is `failed` (`REJECT_CRITICAL_NONVISUAL_FAILED`, independent of sample completeness); or (b) every required view of all n units is reviewed and verified (none of H1, H2, H4, H5, H6 is active) and any class count is at or above its Re (`REJECT_LIMIT_REACHED`). *Re-check, 17 Nov 2026:* the original argument that counts only grow, so an open severity question or second-person check cannot reverse this, **holds for `every_class`** but **can fail under `highest_class_only`** (a newly confirmed higher-severity defect moves its unit up a class and lowers a lower-class count; a retraction also lowers counts). The order is **kept**: a lot may be rejected and recomputed, never wrongly accepted. Whether to evaluate ESCALATE first in that corner is open (DP-OQ-1).
  3. ESCALATE if any of: (E1) a proposal whose provisional lookup is critical is neither confirmed nor rejected (`ESCALATE_CRITICAL_UNREVIEWED`); (E2) a confirmed defect has type "other" or no clause mapping for its (type, zone, size band) (`ESCALATE_UNMAPPED_CLAUSE`); (E3) the reviewer rejected a proposal whose provisional lookup is critical and a second person has not confirmed the rejection (`ESCALATE_CRITICAL_REJECTION_UNCONFIRMED`); (E4) the reviewer flagged "possible critical, need a second opinion" (`ESCALATE_SECOND_OPINION_REQUESTED`).
  4. HOLD if any of: (H1) fewer than n units exist (`HOLD_UNITS_MISSING`); (H2) a required view is not reviewed: zero proposals not yet cleared, a **live** inference job on a view with no human review, inference failed or never ran with no manual review, a quality-gated image not retaken, an excluded view without a replacement (`HOLD_VIEWS_PENDING`); (H3) `critical_nonvisual_status` is `pending` (`HOLD_CRITICAL_NONVISUAL_PENDING`); (H4) a view's review state contradicts its confirmed defects (`HOLD_VIEW_STATE_INCONSISTENT`); (H5) an included image file is missing or fails its hash check (`HOLD_EVIDENCE_INTEGRITY`); (H6) a technical error that could still be recorded (`HOLD_COMPUTE_ERROR`).
  5. ACCEPT otherwise (`ACCEPT_PLAN_MET`). Every class count is then below its Re, that is, at or under its Ac, and the critical non-visual status is `done` or `not_required`.
  - *Advisory projection:* before review is finished, the UI may show a projected outcome from model proposals, labelled "uncalibrated", plus a banner when a class has already reached its Re. With a real calibration set it may show an interval. The projection never decides anything. An interval is not a HOLD condition, because decisions use only confirmed counts.
- **Report.** One page: plan, n, counts, counting mode, selection method, outcome with the R14 wording, overrides, model version, critical-check status, and which image domains the detector was trained on. The browser prints it to PDF. It is not a second source of truth.

If inference is down, manual inspection still works: a person marks each view `confirmed_clean` or `confirmed_defects`, and the lot can then reach ACCEPT or REJECT. A queued or running inference job never blocks a view that already has a human review (a queued job is cancelled, a running one is discarded when it finishes). The screen says "not inferred". It never shows a clean pass.

## I. Stack

Use this unless a verified finding makes a piece wrong (see D1 to D3, D7):

- React + TypeScript + Vite single-page app, usable on a phone; React Router and a data-fetching library such as TanStack Query [R]. Normalize EXIF orientation, strip GPS metadata, and handle HEIC from iPhones.
- Python + FastAPI, SQLAlchemy, Alembic.
- PyTorch; detector per D3, with the license of detector code and of pretrained weights stated. Compare a second detector only if the baseline fails a localization test you state before training (for example, recall at IoU 0.5 on holes below a threshold the team sets) [R]. An anomaly model never increments the AQL count.
- PostgreSQL. Image files on a local volume for version 1. S3-compatible storage only if a bucket already exists.
- Argon2id password hashes; server sessions in HttpOnly, SameSite cookies. No OAuth in version 1.
- One Docker Compose file, one machine, one reverse proxy with HTTPS. GPU for training. CPU inference is acceptable if one view returns in about 3 seconds and a 16-view lot in about a minute [R: targets, not measurements].

## J. Evaluation

- **Detection**, per image domain, on a frozen split: precision, recall, mAP at a stated IoU, per-class AP, and the false-negative rate on holes and dropped stitches. One mAP mixed across AITEX and phone photos is invalid. Also report view-level recall: the share of truly defective views that receive at least one proposal.
- **Reviewer behavior.** Seed known-defective garments into staged lots and report how often the reviewer marks them clean (automation-bias check).
- **Lot decision**, on frozen mini-lots with known confirmed counts (ground-truth outcome computed by the same engine from dual-annotated counts): false accept, false reject, hold rate, escalate rate, each reported as k of N with an exact interval. Do not report a percentage without N. A false accept that contains a critical defective unit is the failure that matters. Image mAP does not replace this. This tests the human-plus-model pipeline, not the statistical risk of the plan.
- **Calibration.** Name the exact detection-calibration metric; classification ECE does not apply to boxes unchanged. Compute it only on data that was not used to train or to choose the threshold. Otherwise write "not calibrated".
- **Engine tests.** Table-driven, with symbolic values: count = Ac accepts; count = Re rejects; a configuration with Re not greater than Ac is refused; n at or above lot size forces 100% inspection; one critical with an otherwise clean sample REJECTs under the R8 critical rule; REJECT stands when an E2 condition is also open; ACCEPT is blocked by each ESCALATE and HOLD condition alone and in combination; `critical_nonvisual_status = pending` blocks ACCEPT but not REJECT; both counting modes are tested on one garment with a major and a minor defect.

## K. Schema, API, canonical names

**Canonical component names** (use exactly these in every diagram): WebApp, Proxy, API, Identity, Lots, Plan, Capture, Vision, Review, Uncertainty, Decision, Report, InferenceWorker, Postgres, ImageStore. (v3.1: `Vision` and `InferenceWorker` are containers; `ModelStore` is the read-only checkpoint volume mounted into `Vision`.)

**Tables.** Normalized: user, organization, product, lot, sample unit, view, plan, image, inference job, prediction, confirmed defect, view review, clause mapping, decision, override, exclusion log, audit event, model version. A prediction references an image and a model version. A confirmed defect references a sample unit, a view, a reviewer, a zone, and optionally a size band. A decision references the plan, the counting mode, and the snapshot of counts it used. Every table carries `organization_id`. Constraints to state: Re greater than Ac; unique garment code per lot; duplicate checksum linked, not deleted; one decision row per computation, never updated. Add a table only with a stated invariant.

**REST sketch**, not a full catalog: login, create lot, set plan, draw sample (optional), upload image, run inference, confirm defect or mark view clean, set critical-check status, compute decision, get report. Give one sample request and response for upload, and one for the decision, using placeholder values (A6).

## L. Answer order

1. The decision rule, including what is not automated.
2. Dataset table, scores, recommendation, and custom-collection plan (end of Message 1).
3. Version-1 requirements, functional and non-functional.
4. Containers and module boundaries.
5. Vision choice, tied to the annotation format you found.
6. Plan engine: procedure, counting rule, copyright constraint. No pasted numeric table.
7. HOLD and ESCALATE conditions (section H is the source of truth; show them as a decision table in evaluation order).
8. Schema: table list and invariants.
9. API sketch and the two sample payloads.
10. Training and evaluation protocol, including the lot-level tests.
11. Mermaid diagrams, same component names in each: context, containers, inference, inspection sequence (file bytes to ACCEPT, REJECT, HOLD, or ESCALATE), decision, ER, deployment.
12. Version-1 build order, risks (data, model, statistical, operational), and open questions.
13. Competition plan: schedule, roles, demo script, and honest limits.

## M. Versions

- **Version 1.** Lot, entered plan, upload, one detector, human confirm with zone, Ac / Re, four outcomes, printable one-page report, critical-check status, manual mode when inference fails. Done when someone runs at least eight staged garments and the outcome matches a hand calculation, and when three forced cases behave as stated: a model miss that a reviewer adds (counts change, outcome matches the hand calculation); a unit skipped by the reviewer (HOLD); a possible critical left unconfirmed (ESCALATE).
- **Version 2.** Supervisor-edited clause mapping, image-quality gate, threshold chosen on a validation split, operating-characteristic view, staged-versus-public table, override list.
- **Version 3.** Factory photos as their own test set, a second product, retraining. Half a page. Do not design it.

## N. Competition plan (answer section 13)

Fit it to 41 days and a team of 4. Recommendations [R], to be adjusted by you with reasons:
- Roles: vision and data; backend, plan engine, and decision; frontend and capture; QC domain, evaluation, report, and pitch. One person owns the written evaluation.
- Milestones: staged shooting and labelling start in week 1; staged test set frozen by Sun 6 Dec; version 1 end to end by Sun 6 Dec; feature freeze Sun 13 Dec; 14 to 25 Dec testing, evaluation table, deck, and rehearsal with no new features.
- Demo plan: the full stack runs on one laptop from Docker Compose, a phone joins over a hotspot with HTTPS, a pre-seeded lot, and a recorded fallback, because venue Wi-Fi is unknown.
- Pitch: show the arithmetic behind every outcome, one forced HOLD and one forced ESCALATE live, the critical-check gate, and a slide of honest limits (uncalibrated, staged-only evidence, fabric-trained public data, no factory test). Use only numbers the team measured.
- State what you cut to fit the budget and what risk each cut adds.

## O. Security and failure (brief)

Cover: Argon2id hashing; role checks on every write; organization isolation on every query, tested for cross-organization access; CSRF protection; login rate limiting; upload checks by magic bytes, not extension, with size and pixel limits and re-encoding that strips metadata; private image storage served only through authenticated endpoints; checkpoint handling per D7; audit of overrides, critical-check changes, and every decision recompute; what is backed up (database dump plus the image volume plus a checksum manifest) and how often. State the behavior for inference down, database down, duplicate upload, blur, unknown class, and model uncertainty. Never equate a system failure with "no defects."

## P. Leave these open if you could not verify them

BDFD9 split integrity and the count of duplicated images; the dataset license of ISL-Knit (Kaggle page) and of FabriD's capture device and garment-versus-swatch status; the license of each download mirror; the exact Ac / Re cells and n (the team must read them from a standard it is allowed to use, and record the edition); whether the standard or the buyer requires `highest_class_only` or `every_class` counting; how n is set when classes carry different AQLs; how the critical class is handled under the third edition; whether the buyer contract implies an isolated-lot approach; whether RF-DETR trains on the available labels and how it performs here; the congress judging rubric.
