## 3. Measurement validation

- **Type:** research, with a measuring script.
- **Depends on:** `references/1`, `references/2`
- **Contract:**
  - In: Z-Anatomy's meshes for the kept structures; ANSUR II male and female CSVs,
    analyzed separately as the data's authors advise
  - Requires: each measurement's definition matched to the source's definition
  - Delivers: a table in this file: measurement, Z-Anatomy value, source value and
    spread, source, gap. Also a list of what no open source covers, starting with
    measured female anatomy
- **Pre-work:** download the ANSUR II CSVs, if `references/1` allows it
- **Out of scope:** correcting the model
- **Tests:** the measuring script's unit conversions

**Limits:** ANSUR II is external body measurement of US Army personnel, not a
civilian sample, and has no internal anatomy. Z-Anatomy comes from one male body, so a
gap may be normal variation rather than an error. Facial and muscle measurements
need other sources, to be found here.

Sources: [ANSUR II](https://www.openlab.psu.edu/ansur2/),
[Army overview](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx).
