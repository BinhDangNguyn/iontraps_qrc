# Iontraps-qrc - trapped-ion quantum reservoir computing for zero-day detection

Team QC-connect:

Minh Dao Tran

Dang Nguyen Binh

Asser Sherif Ahmed Abdelnaby

This is a research code and results repo, not a packaged product. It simulates a trapped-ion
reservoir (all-to-all `ZZPhase` couplings, measure-and-reset memory qubits) on the NF-UNSW-NB15
network-flow dataset and asks whether **more qubits** or **more time steps (L)** make it beat a
classical PCA baseline on known attacks (supervised) and unseen attacks (zero-day).

![AUC vs qubits](figures/auc_vs_qubits.png)

## Contents

- [How this works](#how-this-works)
- [Results at a glance](#results-at-a-glance)
- [Emulator execution (Quantinuum H2-Emulator)](#emulator-execution-quantinuum-h2-emulator)
- [Documents](#documents)
- [Backend support](#backend-support)
- [Worked examples](#worked-examples)
- [Where to take this](#where-to-take-this)
- [Other datasets and topologies](#other-datasets-and-topologies)
- [Picking a run back up](#picking-a-run-back-up)
- [Repository layout](#repository-layout)
- [Resources](#resources)

## How this works

1. **Clone and install** — `pip install -e .` (numpy, pandas, pyarrow, scikit-learn, scipy, matplotlib).
   Add `".[notebooks,dev]"` for Jupyter and pytest, `".[hardware]"` for pytket/qnexus.
2. **Add data** — put an NF-UNSW-NB15 parquet in `data/raw/` (see [data/README.md](data/README.md)).
   The committed results come from the v2 file, which is **not** included; the v1 file runs end to end
   but will not reproduce them.
3. **Run** — a sweep over (qubits × L) writes one JSON per cell plus a summary:
   ```bash
   python scripts/run_sweep.py --dry-run                        # circuit budgets only
   python scripts/run_sweep.py --quick --only 6q_a2a_L6         # wiring check; numbers not meaningful
   python scripts/run_sweep.py --data data/raw/NF-UNSW-NB15-v2.parquet --qubits 6,8 --L 6,8,10
   python scripts/run_sweep.py --qubits 16 --L 6 --workers 24   # parallel, bit-identical to serial
   ```
4. **Plot** — `notebooks/scaling_with_qubits.ipynb` loads `results/` and writes `figures/`.
5. **Check** — `pytest` runs the smoke tests (parallel == serial, one quick cell end to end).

## Results at a glance

18 cells: 6, 8, 10, 12, 14, 16 qubits × L = 6, 8, 10; 512 shots; zero-day family = Exploits.

- Supervised AUC: quantum 0.962–0.986 vs classical 0.984–0.986. Every difference is ≤ 0; the best cell
  (12q, L=10) is −0.001.
- Zero-day AUC: quantum 0.859–0.891 vs classical 0.888. Four cells at 14–16 qubits reach parity
  (+0.002, +0.001, +0.003, 0.000), but no interval excludes zero.
- The trend is **not monotone** in qubits; larger L helps at small N.

Files, provenance of each cell and the check against the report table: [results/README.md](results/README.md).

## Emulator execution (Quantinuum H2-Emulator)

The reservoir circuit runs on Quantinuum's stack, not only in our simulator. Three circuits of the
`6q_a2a_L6` cell (the same frozen reservoir as the sweep: seed 1234, 6 qubits, L = 6, 105 `ZZPhase`
gates and 18 mid-circuit measure-and-resets each) were submitted from the Aqora challenge workspace
with `aqora.QPU` to **`nexus:H2-Emulator`**, 200 shots each, on 14 Oct 2026.

| Job ID | Status |
|---|---|
| `AFByb3ZpZGVySm9iAaE7UeXMfVCXVYSUU-KRFA` | completed |
| `AFByb3ZpZGVySm9iAaE7UerBfkKVNjaa_Qh69Q` | completed |
| `AFByb3ZpZGVySm9iAaE7Ue9Ze1CP_cVW5SsOcA` | completed |

The measured `<Z>` features match this repo's NumPy simulator on the same circuits: **r = 0.994**,
mean |difference| 0.049, **72 of 72 features within 3 sigma** of shot noise. At this size the
emulator's H2 noise model moves the features less than shot noise does; this is a check that the
circuit compiles and executes as simulated, not evidence about the deeper 14–16 qubit circuits.

- Code that ran: [scripts/aqora_emulator_cells.py](scripts/aqora_emulator_cells.py) (marimo cells for the Aqora workspace)
- Record with raw shot counts: [results/emulator/emulator_run_6q_L6.json](results/emulator/emulator_run_6q_L6.json)
- Jobs page: [results/emulator/aqora_jobs_H2-Emulator.png](results/emulator/aqora_jobs_H2-Emulator.png)

The full 18-cell study above is NumPy simulation with sampled shots.

## Documents

- [Team26_QRC_One_Page_Summary_final.pdf](Team26_QRC_One_Page_Summary_final.pdf) — one-page summary
- [docs/QRC_v2_report_full_grid_6to16_qubits.pdf](docs/QRC_v2_report_full_grid_6to16_qubits.pdf) — written report: methods, all 18 cells, intervals, limitations

## Backend support

Select with `--backend` (default `numpy`). The 18-cell study in `results/` was produced with `numpy`;
the emulator run in `results/emulator/` went through `aqora.QPU` (see above).

| Backend    | What it does                                                                     | Cost    | Status                            |
| ---------- | -------------------------------------------------------------------------------- | ------- | --------------------------------- |
| `numpy`  | statevector simulation with sampled shots (`--workers N` for multiprocess)     | CPU     | used for all results              |
| `exact`  | shot-noise-free ceiling, 4^N memory                                              | CPU/RAM | implemented, no committed results |
| `syntax` | compile for a Quantinuum target and validate, no results                         | 0 HQC   | needs `pytket`, untested here   |
| `nexus`  | submit via qnexus to an emulator or hardware (default device in code: `H1-1E`) | HQC     | needs `pytket`, untested here   |
| Aqora `QPU` | `scripts/aqora_emulator_cells.py` in the challenge workspace, `nexus:H2-Emulator` | seconds | **run: 3 jobs, see above**      |

Real hardware ≤ `numpy` ≤ `exact`: improving the hardware can approach the `numpy` result and never pass the
`exact` one, so `exact` is the experiment that tells you whether any shot count could win.

## Worked examples

| Entry point                                       | What it shows                                                                 |
| ------------------------------------------------- | ----------------------------------------------------------------------------- |
| `scripts/run_sweep.py --quick --only 6q_a2a_L6` | smallest end-to-end run: encode → reservoir → readout → AUC (about 10 s)   |
| `scripts/rerun_all.sh`                          | the full grid used in the report, resumable                                   |
| `notebooks/scaling_with_qubits.ipynb`           | load results, verify against the report table, plot AUC / gap / live features |

## Where to take this

- Larger registers (18–20 qubits) with `--workers`; cost grows as 2^N per circuit.
- The `exact` ceiling at 6–10 qubits to separate shot noise from reservoir capacity.
- More shots or readout designs, since many features sit near the shot-noise floor (`live` vs `feat`).
- Other zero-day families (change `ZERO_DAY` in `sweep.py`) and split seeds (only seed 42 is committed).
- Scale the H2-Emulator runs from the 6-qubit check to the 8–16 qubit cells and full test sets.

## Other datasets and topologies

- Datasets: `nfunsw` (NF-UNSW-NB15) and `nslkdd` loaders exist in `core.py`; `--data` / `NFUNSW_PARQUET` select the file.
- Topologies: `all_to_all` and `ring` in `core.make_edges`. The sweep uses all-to-all with
  Sherrington–Kirkpatrick scaling `j_scale = sqrt(7/(N-1))` so only N changes down a column.

## Picking a run back up

`scripts/rerun_all.sh` writes each stage to `results/runs/<stage>/` and drops a `DONE` marker when it
finishes. Re-running the script skips finished stages, so an interrupted 16-qubit run resumes where it stopped.
Reservoirs are frozen per cell (`reservoir_<tag>.npz`), so a resumed cell uses the same couplings.

```bash
PYTHON=python DATA=data/raw/NF-UNSW-NB15-v2.parquet WORKERS=24 bash scripts/rerun_all.sh
```

## Repository layout

```
src/iontraps_qrc/   core.py (reservoir, simulators, readout, detector), sweep.py, parallel.py, report.py
scripts/            run_sweep.py, rerun_all.sh, aqora_emulator_cells.py (H2-Emulator run)
notebooks/          scaling_with_qubits.ipynb
results/            committed results + README; emulator/ holds the H2-Emulator evidence
docs/               written report (PDF)
figures/            PNG / PDF
data/               README; raw/ is git-ignored
tests/              smoke tests
```

## Resources

- [pytket](https://docs.quantinuum.com/tket/api-docs/) and [Quantinuum Nexus docs](https://docs.quantinuum.com/nexus/) — for the `syntax` / `nexus` backends
- NF-UNSW-NB15 — NetFlow version of UNSW-NB15 (Sarhan et al.)
- [results/README.md](results/README.md), [data/README.md](data/README.md) — provenance and data notes
