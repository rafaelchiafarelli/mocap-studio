# animation-body

**Goal:** a whole human body, starting from MPFB2's sliders, that looks right at rest and shows in animation what a real body shows: "as dobrinhas do corpo, as reentrâncias e todas as ondas de choque do caminhar, quando existem" (Rafael, 2026-11-10).

**Status:** agreed in conversation on 2026-11-10; epics and tasks still to be planned. Nothing of the body is built yet. The tool for judging reference material exists: `human-model/tools/check_reference.py`.

## Why a new start

Rafael (2026-11-10): the assembled models are "total completa e absolutamente inutilizáveis". His reading: volumes deform in unknown ways, so expectations of an anatomical body and physics ambitions come down considerably. It reverses his 2026-11-02 rule against reducing anatomy early.

**What is wrong at rest, in his words:** "a forma parada é simplesmente horrorosa. A pele fica 'quadrada' e com reentrâncias por conta da bexiga. A malha não se estende adequadamente e não preenchemos os espaços com gordura, então a região sobre o seio fica 'cavada' por que o tecido está repuxado."

**Why tuning the old system would not have reached the goal (checked in the code, 2026-11-10):**

- **Folds:** the tissue solver (`hmcore/xpbd.py`) only has contact with the floor, so skin never presses on skin; and MPFB's skin is coarse, with 169 vertices over 16 cm of thigh.
- **Shock waves:** the bones are driven from averaged walking cycles at 24 frames per second, interpolated within each frame, so the heel's impact never enters the simulation.
- **Damping:** at 20 per second, a wave crossing 20 cm of fat loses about three quarters of its strength. An estimate from the tissue values, not a measurement.

## The approach

One cheap mechanism per thing Rafael wants to see, for the whole body at once:

| What he wants to see | How | What is given up |
|---|---|---|
| Body and joints | A clean MPFB2 human, sliders only, its rig and corrections per pose | Bones, muscles and organs inside |
| Folds and creases | A catalogue of fixed lines (under the buttock and the breast, armpit, elbow, knee, waist), their depth tied to the joint's angle and the fat; finer mesh only at the end | A fold not in the catalogue doesn't exist |
| Sway and waves | One layer on the skin: each point moves in or out along its normal and passes the motion to its neighbours, with values per region | True volume, and skin pushing on skin |
| The step's impact | A pulse generated when the foot touches the ground, independent of the capture | Biomechanical fidelity |

The breast starts as one region of the skin layer. The water balloon stays as a study (`G:\mocap-studio-downloads\review\2026-11-09\bexiga\`).

## Decided by Rafael (2026-11-10)

- MPFB2 stays the base. No purchased body.
- The whole body in the first pass, not one fold and one wave first: he analyses everything together.
- The model comes first, while he gathers reference photos and videos.
- The mesh tests M1 and M2 of the document below are left for the future.

## Reference and comparison

- `tools/check_reference.py` rates each photo or video before use (`hm.sh --ref`).
- A comparison against real people needs simple renders of the model, an exception to the rule of no renders unless asked. It was proposed and not yet answered.
- Reference material stays on `G:`, out of the repository, and enters no model.

## Sources and earlier work

- The document Rafael started from: "Modelo humano no Blender: achados e alternativas", https://claude.ai/artifact/7tJ8qHKfmyZht8pjbGNg6W
- The earlier body: branch `body-type-selection-backup`, with every commit of `body-type-selection` and its unfinished work. Runs and results are in `G:\mocap-studio-downloads\review\`.
