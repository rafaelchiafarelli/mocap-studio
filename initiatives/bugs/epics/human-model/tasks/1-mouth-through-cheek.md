# Inner mouth pokes through the cheek with strong muscle activation

- **Symptom:** in the muscles-only panel, a red patch of the mouth's inside shows through the cheek.
- **Where:** `human-model/hmcore/softtissue.py`, `Region.solve`: nothing keeps skin outside the mouth cavity.
- **Reproduce:** frames 120 and 360 of `comparacao_faders_hibrido_musculos.mp4`, right panel.
- **Impact:** only the muscles-only variant, which is not recommended.
- **Status:** Open. Likely fix: treat the mouth's inner vertices as a separate sheet.
