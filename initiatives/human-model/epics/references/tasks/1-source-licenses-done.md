## 1. Source licenses

- **Type:** research (the session reads the licenses; Rafael decides).
- **Depends on:** —
- **Contract:**
  - In: every source planned for reference or derivation, starting with Z-Anatomy,
    MuSkeMo, anatomy3d-blender, MPFB, ANSUR II, Fukuchi 2018, the Rajagopal model,
    Tissue and Pose Shape Keys
  - Requires: the commercial-use rule in the `mocap-workflow` skill
  - Delivers: a table in this file: source, version, license as read, what we'd
    take from it (looking, measuring, deriving), commercial use, open questions
- **Pre-work:** —
- **Out of scope:** using any source
- **Tests:** —

**Questions Rafael has to settle:**

- **Z-Anatomy:** CC BY-SA 4.0 with BodyParts3D at CC BY-SA 2.1 JP, some parts NC.
  CC BY-SA isn't on the rule's allowed list. Is measuring from it, then building our
  own, free of share-alike? This needs a clear answer, possibly from a lawyer.
- **MuSkeMo:** no license found, and `scripts/icp_point_to_plane.py` declares
  CC-BY-NC.
- **ANSUR II:** marked "approved for public release; distribution is unlimited",
  which isn't a formal license.
- **Rajagopal model:** the SimTK license text hasn't been read.
- **Parrot Lipsync:** already recorded as not settled in `DEPENDENCIES.md`.

## Result (2026-11-03)

Rafael delegated these decisions on 2026-11-03 and reviews them afterwards. This is
an engineer's reading of the license texts, not legal advice.

| Source | Version | License as read | What we take | Commercial use | Open questions |
|---|---|---|---|---|---|
| [TotalSegmentator CT dataset](https://zenodo.org/records/10047292) | 2.0.1 | CC BY 4.0 (Zenodo API `cc-by-4.0`) | **Derive:** bone and muscle labels to meshes; **measure:** per-sex statistics | Yes, with attribution | De-identified patient scans, sex and age in `meta.csv`. Credit is required wherever the model ships |
| [BMF Toolkit](https://github.com/manishsreenivasa/BMFToolkit) | commit `e3e781e` | zlib | **Derive:** female lower-body bones, from Visible Human CT | Yes | Altered versions must be marked as altered |
| [Rajagopal 2016](https://simtk.org/home/full_body) | 4.0 | MIT (Stanford, read on SimTK's release page) | **Derive:** forearm and hand bones, muscle path points; joint axes | Yes | Copy comes from `opensim-org/opensim-models`, whose repository has no license file; SimTK's download needs a login. Same model, but the MIT grant was read on SimTK |
| [ANSUR II](https://www.openlab.psu.edu/ansur2/) | public CSVs | US Army data "approved for public release; distribution is unlimited"; no formal license | **Measure:** external validation only. Nothing ships | Yes in practice | Not a formal license, which is why it's validation only |
| [Fukuchi 2018](https://doi.org/10.6084/m9.figshare.5722711) | figshare 5722711 | CC BY 4.0 (figshare API) | **Derive:** walking joint angles; **measure** | Yes, with attribution | — |
| [CDC joint range study](https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html) | Soucie 2011 | US government public data | **Measure:** range limits | Yes | — |
| MPFB | 2.0.18 | Code GPL-3.0+; MakeHuman base mesh, targets and assets CC0 | **Derive:** skin, rig, eyes, teeth, tongue | Yes | This session didn't find a statement in the add-on on whether GPL reaches a generated character. The usual reading is that it doesn't, since the mesh and targets are CC0 |
| Tissue | 0.3.76 | GPL-3.0+ | **Tool:** pattern experiment | Yes (rule: GPL for tools) | — |
| Pose Shape Keys | — | GPL-3.0+ | Not used | Yes | — |
| Z-Anatomy, BodyParts3D | current | CC BY-SA 4.0 and CC BY-SA 2.1 JP, some parts NC | **Look and compare only:** validation numbers in reports | Share-alike isn't on the allowed list, and NC parts are forbidden | See decision 1 |
| MuSkeMo | — | No license found; one file CC-BY-NC | Nothing | No | — |
| anatomy3d-blender | — | GPL-2.0 | Nothing: draws fibers, no deformation | Tool only | — |
| Parrot Lipsync | 1.1.4 | Manifest MIT, repository GPL-3.0, not settled | Nothing new. `drive` reads phonemes from Allosaurus, as the faders do | Open | Already recorded in `DEPENDENCIES.md` |

**Decisions, taken on Rafael's behalf:**

1. **Z-Anatomy stays out of the model.** No mesh, patch or coordinate from it enters
   anything we build. This removes the share-alike question instead of answering it,
   so no lawyer is needed now. It's still measured as a comparison in `references/3`,
   and those numbers stay in reports. The jaw proof of concept remains review-only.
2. **Bones come from CT labels and permissive meshes**, not from an atlas: this also
   closes the female gap, because the CT dataset has 510 female scans.
3. **MuSkeMo and anatomy3d-blender are dropped.**

**CC BY obligations:** [`human-model/ATTRIBUTION.md`](../../../../../human-model/ATTRIBUTION.md)
lists the credits a film using this model has to carry.
