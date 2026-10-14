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

## Backend support

Select with `--backend` (default `numpy`). Everything in `results/` was produced with `numpy`.

| Backend    | What it does                                                                     | Cost    | Status                            |
| ---------- | -------------------------------------------------------------------------------- | ------- | --------------------------------- |
| `numpy`  | statevector simulation with sampled shots (`--workers N` for multiprocess)     | CPU     | used for all results              |
| `exact`  | shot-noise-free ceiling, 4^N memory                                              | CPU/RAM | implemented, no committed results |
| `syntax` | compile for a Quantinuum target and validate, no results                         | 0 HQC   | needs `pytket`, untested here   |
| `nexus`  | submit via qnexus to an emulator or hardware (default device in code: `H1-1E`) | HQC     | needs `pytket`, untested here   |

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
- Hardware-tier emulator runs via `syntax` then `nexus`.

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
scripts/            run_sweep.py, rerun_all.sh
notebooks/          scaling_with_qubits.ipynb
results/            committed results + README
figures/            PNG / PDF
data/               README; raw/ is git-ignored
tests/              smoke tests
```

## Resources

- [pytket](https://docs.quantinuum.com/tket/api-docs/) and [Quantinuum Nexus docs](https://docs.quantinuum.com/nexus/) — for the `syntax` / `nexus` backends
- NF-UNSW-NB15 — NetFlow version of UNSW-NB15 (Sarhan et al.)
- [results/README.md](results/README.md), [data/README.md](data/README.md) — provenance and data notes
