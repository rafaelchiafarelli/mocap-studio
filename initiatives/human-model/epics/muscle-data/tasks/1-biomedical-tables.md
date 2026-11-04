## 1. Biomedical tables

- **Type:** research.
- **Depends on:** `references/1`, `references/3`
- **Contract:**
  - In: Rafael's lead (2026-11-03): biomedical tables might give the values for every muscle
  - Requires: the commercial-use rule on the data's license; primary sources; a source's sample recorded (specimens, sex, age)
  - Delivers: a table in this file, one row per muscle in `human-model/data/muscles.json`: mass or volume, fiber length, cross-section, pennation, attachment description, source, sample, license, and "none found" where that's the truth. Then a list of which declared values each row would replace
- **Pre-work:** —
- **Out of scope:** changing `data/muscles.json`, which is a task of its own once this reads well
- **Tests:** —

**Why it matters:** declared values are the model's main weakness, and CT volumes already show gluteus maximus 54% too large and back muscles too small (`muscles/7`).

**Leads, none read yet.** A first search found no single open table covering every muscle, so expect to combine several:

- Face: [Happak et al. 1997](https://bioweb.supagro.inrae.fr/ESTHER/paper/Happak_1997_Anat.Rec_249_276), ten facial muscles from 11 cadavers, lengths 29 to 65 mm. Its access and terms are unknown.
- Search results still to match to their papers: [PMC2650051](https://pmc.ncbi.nlm.nih.gov/articles/PMC2650051), [PMC5199092](https://pmc.ncbi.nlm.nih.gov/articles/PMC5199092), [PMC11889482](https://pmc.ncbi.nlm.nih.gov/articles/PMC11889482), [arXiv 2411.00071](https://www.arxiv.org/pdf/2411.00071). They appear to include a 27-muscle lower-limb study from 21 specimens, a single 104-year-old female cadaver, 14 neck muscles from 10 cadavers, and a comparison of open lower-limb model parameters against 57 studies.

Numbers themselves are generally reusable facts, but a table's own license still gets read and recorded here.
