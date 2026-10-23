# Exploration — script → shot list → previz (2026-10-17 → 10-23)

Knowledge transfer from a claude.ai session. **Exploration only: no
initiative, epic, task or branch chain exists for this yet.** Follow the
`mocap-workflow` skill before turning anything here into task files, and ask
Rafael before creating any.

> **Priority context.** Rafael has said the overall project feels too big and
> wants to see small parts working first. The agreed first step is an
> isolated face test (recorded speech → Audio2Face → exaggerated blendshapes →
> Blender). This previz track does **not** jump ahead of that.

This is **project** work (workhorse: pre-production → production). Nothing
here is film-specific; the pilot film is referred to only as "the pilot film"
(location in `HANDOFF.md`).

## 1. Goal (Rafael's words, condensed)

- Turn scripts into storyboards **without AI-generated images**. AI may only
  produce the *text* that generates images; output must be editable later,
  ideally with layers.
- Not a classic 2D board: **real 3D blocking** (positions, camera, lens), with
  an editable 2D output derived from it.
- It is part of the workhorse: scripts are written, processed and turned into
  a **shot list for production**; **sets and props derive from the script**.
- Must integrate with `mocap-preprod`, `mocap-dashboard` and the capture repos.
- Rafael does not want to manage processes by hand. He wants to **decide once
  and propagate to the remaining scenes**, and **see an image soon after
  writing a scene**.
- Token cost is a hard constraint.
- Target **Blender 5.2+**; must stay **robust to Blender evolution**.

## 2. Decisions made (by Rafael, in the exploration session)

| # | Decision |
|---|---|
| D1 | The 3D scene is the source of truth for the image; SVG is *derived* from it (STL rejected: no scene, camera, hierarchy or layers). |
| D2 | Harpia is used for the contracts (native Python output). |
| D3 | The **writer's text is the source of truth** for the script, written in a tool made for screenwriters. Harpia only receives what is *extracted* from it; it never writes back to the script. (Rejected: modelling the screenplay itself in Harpia with Fountain as a view.) |
| D4 | Rafael will try converting the pilot film's script (currently `.docx`) to **Fountain**. |
| D5 | Film-root files are structured for parallel processing and preview, integrated with `mocap-preprod`. |

## 3. Spikes already done (evidence in `spikes/`)

### 3.1 Blender → layered SVG — **resolved**

Run headless with the `bpy==5.2.2` wheel. **Stack note:** that wheel requires
**Python 3.13** (`Requires-Python: ==3.13.*`), while `DEPENDENCIES.md` fixes
3.12. Running previz through `bpy` as a module is therefore a divergence to
decide; the alternative is running the same script inside Blender 5.2.2
(`blender -b --python …`), which keeps the stack as is.

- **Freestyle SVG Exporter** is no longer bundled in 5.2.
- **`wm.grease_pencil_export_svg`** headless ignored the scene camera, emitted
  strokes as filled outlines (hard to edit) and plain `<g>` groups (Inkscape
  does not see them as layers). Rejected.
- **Working approach** (`spikes/lineart_svg_spike.py`):
  1. One collection per layer (`Cenario`, `Personagens`, `Props`).
  2. One Grease Pencil v3 object, one GP layer per collection, each fed by a
     `LINEART` modifier with `source_type='COLLECTION'`. Occlusion across
     collections works (floor line hidden behind characters).
  3. `object.lineart_bake_strokes()`, then remove the modifiers.
  4. **Own code** reads stroke points, projects them with
     `bpy_extras.object_utils.world_to_camera_view`, and writes SVG with
     `<g inkscape:groupmode="layer" inkscape:label="...">`, plain polylines,
     and scene/camera/Blender version in `<metadata>`.
- **Blender-robustness rule:** the only Blender-coupled surface is Line Art
  modifier + bake + reading stroke points (~50 lines) → isolate it in one
  adapter module. The SVG writer is pure Python. Run the adapter test against
  each new Blender release (manifest + checker: `mocap-studio` bootstrap/3).

### 3.2 Fountain parsers — **both existing Python parsers fail for us**

Sample: `spikes/fountain/sample_ptbr.fountain` (neutral fixture).

| Parser | License | Result |
|---|---|---|
| Jouvence 0.4.2 | Apache-2.0 | Character regex is `[A-Z]` (ASCII): accented names are lost and the rest of the scene collapses into action. No dual dialogue. |
| screenplain 0.12.0 | MIT | Handles accents, `#12#` scene numbers, dual dialogue. **Drops `[[notes]]` and `=` synopses.** |

Recommendation: a **small own parser** (spec 1.1 fits on one screen), with
tests for accents, dual dialogue, notes, PT-BR headings.

## 4. Fountain — facts relevant to us

- Spec **1.0** (Feb 2012), **1.1** (Mar 2014, current, frozen since). Stable,
  but nothing new will be added.
- Elements: scene heading (INT/EXT/EST/INT./EXT/I/E, force with `.`), scene
  number `#12A#`, character (all caps, force `@`), dialogue, parenthetical,
  dual dialogue `^`, transition (`TO:`, force `>`), action (force `!`),
  centered `>x<`, lyrics `~`, notes `[[ ]]`, boneyard `/* */`, sections `#`,
  synopses `=`, page break `===`, title page `Key: value`, emphasis `*` `**` `_`.
- Weaknesses for us: heuristic classification (an all-caps PT-BR action line
  like `TUDO ESCURO.` becomes a character); Brazilian `CENA 13 - …` headings
  are not recognized; no production metadata; **scene number is the only
  identity**; parsers diverge (no official test suite found).
- Editors: Beat, Trelby (Python, GPL — allowed as a tool; exchange files only),
  Afterwriting, VS Code "Better Fountain" (preview, scene outline, character
  autocomplete, PDF export).

**Boundary rule:** only the script parser reads `.fountain`; it emits
`script.harpia` messages. Nothing downstream sees Fountain.

## 5. Proposed architecture (not approved — for validation)

### 5.1 Workhorse flow

```
P-2 Writing      Fountain editor → script.fountain in the film root
P-1 Breakdown    parser (deterministic): scenes, characters, dialogue
                 hosted agent: sets, props, wardrobe per scene → creator reviews
P0  Pre-prod     shot list + 3D blocking + SVG storyboard; asset catalog
                 (every prop/set starts as a box and evolves)
P1  Setup        floor area per shot (from blocking) → body-camera placement
P2  Capture      every take references a shot_id
P3–P4            unchanged
P5  Blender      previz scene receives the MocapTake; cameras already there
```

### 5.2 The scene is the unit of everything (film root)

```
<film-root>/
  script/script.fountain         writer edits one file
  build/scenes/sc-012.json       parser splits per scene (script.harpia) + text hash
  analysis/                      mocap-preprod as today (brief, worklist, memos)
  specs/sc-012/props.json        structured twin of the specialist memo (production.harpia)
              shots.json
              blocking.json
  previz/sc-012/shot-03.svg      generated from specs
  .film-workflow/                state (mocap-dashboard already anticipates this folder)
```

- **Parallel:** per-scene jobs never share files; the text hash tells which
  scenes changed after a rewrite, and only those are reprocessed. Replaces the
  manual per-section sessions of the script-readiness analyst
  (relates to HANDOFF open question 15).
- **Preview:** a scene renders as soon as its own specs exist; unapproved
  assets appear as boxes; proposed specs are watermarked "proposta".
- **Integration with preprod:** each specialist writes its memo (for humans)
  **plus** a structured sidecar validated by Harpia (for machines).

### 5.3 Write a scene → see the image

```
save script.fountain
 → parser: sc-012 changed (hash)              seconds, 0 tokens
 → breakdown of sc-012 with the bible         1 cheap call
 → proposed shot list + blocking              1 call
 → Blender build + Line Art → SVG             seconds/minutes, 0 tokens
 → appears in the dashboard as "proposta"
```

Driven by a **deterministic orchestrator** (watches the film root, queues
per-scene steps in dependency order) — not an agent, not manual sessions.
Events between apps go through Harpia (stack rule).

### 5.4 Decide once, propagate: the film "bible"

Structured film-wide decisions (in the film root): locations (layout,
dimensions, assets), characters (mannequin proportions, default wardrobe),
camera language rules (e.g. "dialogue = shot/reverse 50 mm, open on a wide"),
style. Per-scene agents apply the bible and only flag **exceptions** (new
location, unknown prop, rule broken). Rafael reviews exceptions, not scenes.

### 5.5 Token cost

- Cost is driven by context read per run, not mainly by platform. Per-scene
  runs read one scene + the bible, not the whole script.
- No tokens: parsing, hashing, scheduling, Blender build, SVG.
- Cheap model: extraction. Expensive model: only judgement.
- Agents are already canonical in `.claude/agents/` with Copilot adapters
  generated by `mocap-preprod/scripts/sync_agents.py`; the same mechanism can
  emit further platform adapters if Rafael wants to compare cost.

### 5.6 Repository map

| Repo | Role |
|---|---|
| `mocap-preprod` | agents; start emitting structured specs |
| `mocap-contracts` | `script.harpia` (`Scene`, `Character`, `Element`), `production.harpia` (`Shot`, `ShotCamera`, `Blocking`); `Take` gets optional `shot_id` (HANDOFF Q11: Claude defines these as tasks when the need is real) |
| script parser | `.fountain` → `build/scenes/` (new repo or inside preprod — undecided) |
| previz | specs → Blender → layered SVG (new repo or inside `mocap-blender` — undecided) |
| `mocap-dashboard` | state + per-scene previz thumbnails |
| `mocap-studio` | P1/P2 consume the shot list |

## 6. Open — needs Rafael

**Decisions**
1. Harpia as the on-disk format for specs and workflow state (fills the
   "on-disk schema left for later" in the dashboard's workflow-state contract)?
2. **Approval by rule:** approve a bible rule once and treat derived outputs
   as approved while they comply; only deviations go to review. This changes
   an invariant of the workflow-state contract (every AI output is proposed
   until approved).
3. Previz runtime: `bpy` module (Python 3.13, diverges from 3.12) or Blender
   5.2.2 binary in background mode.
4. Fountain editor of choice; input conventions (`INT./EXT.` mandatory? scene
   numbers mandatory?).
5. Coordinates/units/axes/floor origin shared with `mocap-contracts` so
   blocking and takes land in the same place.
6. Overlaps HANDOFF Q14 (storyboard style, recipe/shot file formats, target
   skeleton) — answer once for both.
7. Final output: one SVG per shot, or a multi-panel board sheet.

**Unknowns (need a test)**
- **U1 — stable identity across rewrites.** Scene number is the only anchor;
  some editors renumber. Who assigns it, when does it freeze ("script lock")?
  Importer must diff and *warn* ("sc-12: a prop left the text, still in
  breakdown"), never fix.
- **U2 — can the hosted agent produce coherent blocking/cameras from a real
  scene, consistent across shots?** Untested and the core of §5.3. Test with
  one scene of the pilot film + a hand-written minimal bible, no code
  (a film session, outputs in the film root).
- **U3 — mannequin rig vs mocap skeleton.** Depends on the `MocapTake` joint
  set (HANDOFF Q14 "target skeleton").
- Optional writer lint (warn on `CENA 13 -` headings, all-caps action lines).

## 7. Suggested next steps (after the face test)

1. Convert the pilot script `.docx` → Fountain **with a script, not an LLM**
   (docx paragraph styles map to scene/character/dialogue).
2. Run U2 on one converted scene with a minimal hand-written bible.
3. Then decide approval-by-rule (#2) and the orchestrator.
4. Only then plan initiatives/tasks per the `mocap-workflow` skill.

## 8. Files

- `spikes/lineart_svg_spike.py` — scene → Line Art → own projection → layered
  SVG. Run with `bpy==5.2.2`: `python spikes/lineart_svg_spike.py -- out.svg`
  (writes `out_own.svg`, the good one). Output is not committed (regenerable).
- `spikes/fountain/` — neutral PT-BR sample and the two parser probes
  (`pip install jouvence screenplain`).
