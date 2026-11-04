# The character editor

How to change a human's body and face in Blender, and test the result by hand. The add-on is **Human Model Editor**, in the sidebar tab **Human**. Press `N` in the 3D view if the sidebar is closed, and click **Human** at its right edge: Blender doesn't let an add-on choose the tab, and a file you open may show another one.

## The one idea to learn

A character has two forms, and the editor shows different things for each.

| | **The sliders file** | **The built model** |
|---|---|---|
| What it is | A plain human: skin, eyes, teeth, tongue | Everything: skin, rig, 181 bones, 200 muscles, face fields |
| What you do | Decide how the person looks | Test how they move: jaw, breath, tongue, face muscles, poses |
| Changes the shape? | **Yes, instantly** | **No, it's baked** |
| Saved as | A **recipe**, one small `.json` file | `<name>.blend` |

The recipe is the character. You go from one form to the other with **Build full model** (about 4.5 minutes) and **Change this character** (a few seconds). The editor never shows shape sliders on a built model, because moving them there moves the skin and leaves the bones, muscles and fields behind.

## Start Blender

Open `G:\mocap-studio-downloads\apps\blender\5.2.2\blender-5.2.2-windows-x64\blender.exe`. This is the only Blender with MPFB and the add-on installed.

## Make a character, step by step

1. **Tab Human > New male** or **New female.** A neutral person appears in about three seconds. In a Blender file that has never been saved, the startup cube is removed.
2. **Name it** in the `Name` field, for example your character's name. It names the folder and files.
3. **Set the big things in Whole body:** age, height, weight, muscle, proportions, ancestry. To ask for a real height, type metres in **Stature** and click **Set**: it measures this body and moves the height slider until it matches.
4. **Shape the details.** Open a panel such as **Face: Nose**, or type in **Find a slider** (`lip`, `jaw`, `shoulder`). Sliders go from −1 to +1, and hovering over one says what each end does.
5. **See what you've done in What I changed.** The ✕ beside a slider resets it, and **Reset every slider** resets them all.
6. **Save** the recipe. A character made for a film belongs in that film's root, as `characters/<id>.json`, not in this repository.
7. **Build full model.** You can keep working in Blender while it runs. The panel shows the stage, 1 to 5.
8. **Open built model,** then test it.

## Test a built model

Any built `.blend` works, through File > Open. They're in `G:\mocap-studio-downloads\models\hm-build\<name>\`.

| Panel | What it does |
|---|---|
| **Layers** | Skin Solid, Wire or Hidden. Wire lets you see inside. Bones, Muscles and Attachments on or off. This changes the view, not the renders |
| **Jaw, breath and tongue** | The live controls. Hover over one and press `I` to keyframe it |
| **Face muscles** | 22 muscles, both sides together. Tick **Left and right apart** for one slider per side: those are the ones you can keyframe, and the way to make an uneven expression |
| **Pose** | **Pose the body** selects the rig and enters Pose Mode, where you rotate joints with `R`. **Reset pose** returns to rest |

To change the person, click **Change this character**. It reads the file's sliders into a plain human, and the built file stays as it is on disk. Save under a new name if you want to keep both.

Good first tests: zygomaticus major at 0.6 is a smile, jaw open at 0.3 opens the mouth, and with skin on Wire and Bones on, rotating `upper_arm.L` shows the skeleton following.

## What each change really does

Read this before trusting a slider. A dot **•** beside a slider means **skin only**.

| You change | Skin | Bones | Muscles |
|---|---|---|---|
| Height, limb lengths, shoulders, ribs | Yes | Yes | Yes |
| Head shape, chin | Yes | Skull and jaw fit to it | Face fields recomputed |
| Nose, lips, eyes | Yes | None needed | Face fields recomputed |
| Hips | Yes | Pelvis grows, **even if the hip is meant to be fat** | Attachments move |
| **• Muscle, arm and leg muscle, gluteus, breasts, fat, belly** | Yes | **No** | **No** |

The evidence and the measures are in [character-controls.md](character-controls.md#what-follows-a-change). The dot on belly sliders is my reading of that table's "Fat" row: those sliders weren't tested on their own.

So a very muscular or very heavy character looks right from outside, but with an average body inside. It shows when you turn on Muscles, and it matters as soon as something depends on the inner layers.

## Limits that are on purpose

- **Sliders stop at 0.8 when dragged.** Some targets break above it: `nose-point-down` makes a spike, `head-square` a ridge. Double-click and type a value to go up to 1.
- **Age stops at 0.5, the adult minimum.** Below it MPFB makes a child's body. A recipe under 0.5 is refused, with the reason. That includes four of the six test people: bug `human-model/8`.
- **Genital sliders aren't offered,** and a recipe with them is refused, as you decided.
- **Sex is male or female.** In-between values are untested in the build.

## Known problems you'll meet

| Problem | Bug |
|---|---|
| A smile can tear at the mouth's corners on a changed nose, lips or eyes. Check every new face with the smile test | `human-model/7` |
| Muscle thickness doesn't follow the muscle slider | `human-model/6` |
| Joints can bend past their limits | `human-model/3` |
| Skin material, hair and clothes aren't applied: the built model has plain skin | [status.md](status.md) |

The readout's mass is an estimate from the skin's volume at a declared density. Weight's range is narrow: at full weight the body is still at a normal BMI, so a heavy character also needs the belly and fat sliders ([character-controls.md](character-controls.md#real-units)).

## When something goes wrong

| You see | Do this |
|---|---|
| No **Human** tab | Edit > Preferences > Add-ons, enable **Human Model Editor**. If it isn't listed, run the install command below |
| "MPFB wasn't found" | Install MPFB 2.0.18: see `DEPENDENCIES.md` |
| "The build failed" | The panel names the log. Most often Docker isn't running: check Docker Desktop, then build again. Your recipe is already saved |
| "The output folder must be on G:" | Docker only sees `G:` |
| Sliders are greyed or missing | Return to Object Mode |
| You replaced a human by accident | Its unsaved sliders are in `hm_editor_last_sliders.json` in the Windows temp folder. The panel gives the path. **Open...** reads it back |

## Install or update

From WSL, at the repository's root, with Blender closed:

```sh
python3 human-model/install_editor.py
```

It installs into the Blender above and enables it. The package also stays at `G:\mocap-studio-downloads\apps\hm-editor\hm_editor.zip`. It records which WSL distribution and repository it came from, so builds run from this copy of the code.

To check it without the interface:

```sh
python3 human-model/blender_run.py --blend /mnt/g/mocap-studio-downloads/models/hm-build/male/male.blend human-model/blender/editor_check.py "$PWD/human-model/data/recipes/male.json" /mnt/g/mocap-studio-downloads/scratch-hm-editor
```
