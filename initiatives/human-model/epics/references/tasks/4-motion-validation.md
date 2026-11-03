## 4. Motion validation

- **Type:** research.
- **Depends on:** `references/1`
- **Contract:**
  - In: published measurements of joint motion, gait and facial movement
  - Requires: primary sources where they exist; flashcards and slides don't count as
    validation
  - Delivers: a table in this file: joint or movement, how it moves, range, source,
    license of any data reused. Also the test that `skeleton/6` runs for each row
- **Pre-work:** —
- **Out of scope:** implementing any joint
- **Tests:** —

**Starting leads, not yet checked at the primary source:**

| Movement | Lead | Open point |
|---|---|---|
| Jaw | [10.6 mm condyle translation in controls](https://boneandjoint.org.uk/Article/10.1302/1358-992X.2023.8.124); [about 41.8 mm incisor drop](https://hal.univ-lorraine.fr/hal-03284700v1/document); [Posselt's envelope](https://en.wikipedia.org/wiki/Posselt%27s_envelope_of_motion) | Pure rotation ends between 10 and 25 mm, depending on the source. Rotation angle and how far the incisor moves back |
| Hyoid and head during opening | None found | Needs its own search |
| Gait | [Fukuchi 2018](https://peerj.com/articles/4640) (CC BY); [Moore 2015](https://pubmed.ncbi.nlm.nih.gov/25945311/) | Fukuchi covers lower limbs and pelvis only |
| Full-body joints | [Rajagopal model](https://simtk.org/home/full_body) | License text unread |
| Smiles and blinks | [Trutoiu](https://ri.cmu.edu/?p=115350) | Numbers still to read |
| Face muscles to movement | [FACS](https://en.wikipedia.org/wiki/Facial_Action_Coding_System) | Is the manual usable? |
| Face layers and anchors | [Retaining ligaments review](https://pubmed.ncbi.nlm.nih.gov/23855010/), [facelift anatomy](https://pubmed.ncbi.nlm.nih.gov/31514803/) | Full text unread; modiolus not yet confirmed |

Z-Biomechanics isn't a validation source: its capture animations cross arms and legs
when applied directly to its main armature, and the cause isn't proven.
