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

## Result (2026-11-03)

Secondary mentions are marked. "Declared" means no source was read and the value is ours,
to be replaced. The tests run in `skeleton/6`, except where a row names another.

| Joint or movement | How it moves | Range | Source | Data license | Test |
|---|---|---|---|---|---|
| Hip | Flexion, extension | M 130.4 / 17.4°, F 133.8 / 18.1° | [CDC study](https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html), ages 20–44, passive | US government | Bone meshes don't pass through each other at the limits |
| Knee | Flexion, extension | M 137.7 / 1.0°, F 141.9 / 1.6° | Same | Same | Same |
| Ankle | Dorsi, plantar flexion | M 12.7 / 54.6°, F 13.8 / 62.1° | Same | Same | Same |
| Shoulder | Flexion | M 168.8°, F 172.0° | Same | Same | Same |
| Elbow | Flexion, extension | M 144.6 / 0.8°, F 150.0 / 4.7° | Same | Same | Same |
| Shoulder extension, abduction, hip abduction, wrist, fingers, spine segments | — | `joints.DECLARED` | **Declared** | — | Same |
| Jaw | Rotation about the condyles, then rotation with condyle sliding forward and down | Incisor 46.6 mm, condyle 11.9 mm straight-line | [Travers 2000](https://utsouthwestern.elsevierpure.com/en/publications/associations-between-incisor-and-mandibular-condylar-movements-du), abstract read, not the full text | Numbers only | `tests/test_jaw_joints.py`: both values reached, rotation under the proof of concept's 38° |
| Jaw, end of pure rotation | — | 20 mm **declared** between the 10 and 25 mm reported | Starting leads above | — | Slide starts at the break |
| Hyoid during opening | Follows the jaw | **Declared.** Only direction found: up and back when the head extends, forward and down when it flexes | King 1952, through a [secondary mention](https://www.koreascience.or.kr/article/JAKO201926837943544.pdf) | — | Stays below the mandible, no passing through |
| Head during opening | Extends a little with the jaw | **Declared**, no numbers read | — | — | — |
| Gait, lower limb and pelvis | Time-normalized cycle at 101 samples | Measured curves, 24 young adults, treadmill trial T05 | [Fukuchi 2018](https://doi.org/10.6084/m9.figshare.5722711) | CC BY 4.0 | Foot doesn't slide in stance, `skeleton/6` |
| Gait, trunk and arms | — | **Declared.** Fukuchi covers lower limbs and pelvis only | — | — | Rafael's judgement |
| Ribs | Pump handle above, bucket handle below | **Declared** rule; 5° at a deep breath | — | — | Chest expansion measured |
| Smile and blink | Fast closing, slower opening of the lid; blinks near the smile's end | No numbers: [Trutoiu's abstracts](https://ri.cmu.edu/?p=115350) give shape only | — | — | `drive/7` |
| Modiolus | Muscles converge at the corner of the mouth: zygomaticus major, orbicularis oris, buccinator, levator anguli oris, mentalis, depressor labii, depressor anguli oris, platysma, risorius. **Confirmed** | — | [Radiopaedia](https://radiopaedia.org/articles/modiolus-mouth), [2025 study](https://link.springer.com/article/10.1007/s00266-025-04696-0) | — | `muscles/4` |
| Retaining ligaments | Orbital, zygomatic and mandibular bands from periosteum to dermis | Zygomatic ligament 66.5 mm and mandibular 114.8 mm from the tragus | [Cadaver study](https://avesis.mcbu.edu.tr/yayin/05770c7e-9d51-4615-96b6-957570185bf8/true-retaining-ligaments-of-face-as-surgical-landmarks-los-verdaderos-ligamentos-de-retencion-de-la-cara-como-marcadores-quirurgicos), abstract | — | `skin/3` |
| FACS muscles | Standard AU mapping | The FACS manual is sold and wasn't read; only the widely published AU-to-muscle mapping is used | — | — | `drive/5` |
