# 1. The editor by stages

Rafael chooses first and fine-tunes after: "somente os dados de modelagem e seleção (biotipo, silhueta, glúteos e seios), e depois disso selecionado e fechado, abrir os outros faders" (2026-11-09).

## Contract

**In:** the character panel, `hm_editor/sheet.py`.

**Out:**
- `sheet.current_stage`, `next_stage`, `fine_moved`: the stages, without `bpy`.
- Stored stage `hm_character.stage` (`choices`, `fine`); `generating` and `built` derived.
- Stage 1 shows the selections and distances only; **Fechar escolhas** checks, makes the body and keeps a named copy.
- Stage 2 locks them and opens the breast faders, the biotype's other parts and the bone parameters; **Reabrir escolhas** returns, keeping them, with **Zerar ajustes finos**.
- The loose MPFB sliders are hidden behind "Modo antigo".

## Agreed and declared

- Loose sliders are out of this version (Rafael, 2026-11-09).
- Reopening keeps the fine adjustments, with a visible reset (Rafael, 2026-11-09).

## Dependencies

Epic `editor-sheet`.

## Pre-work

None.

**Status:** Done (2026-11-09). Unit tests, and the panels and operators in a headless Blender with a stand-in layout. How it looks on screen is left to Rafael.
