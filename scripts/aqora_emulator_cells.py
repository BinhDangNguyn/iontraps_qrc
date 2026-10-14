# =============================================================================
# Emulator execution on Quantinuum H2-Emulator -- the cells that produced the
# committed evidence (results/emulator/emulator_run_6q_L6.json and
# results/emulator/aqora_jobs_H2-Emulator.png).
#
# WHERE IT RAN: the Aqora challenge workspace (marimo notebook), appended to the
# template's pytket_example.py. That notebook's first cell provides
#     import marimo as mo
#     from pytket.circuit import Circuit
#     from pytket.passes import AutoRebase
#     from aqora import QPU
#     from aqora.pytket.backend import GATESET
# and these cells reuse those names. Paste each CELL block into its own cell.
#
# WHAT IT DOES: builds 3 circuits of the 6q_a2a_L6 reservoir (the same frozen
# reservoir as the sweep: seed 1234, 105 ZZPhase gates, 18 mid-circuit
# measure-and-reset), submits them with aqora.QPU, and compares the measured
# <Z> features with this repo's NumPy simulator on the same circuits.
#
# RESULT (14 Oct 2026, nexus:H2-Emulator, 200 shots per circuit):
#     job IDs  AFByb3ZpZGVySm9iAaE7UeXMfVCXVYSUU-KRFA
#              AFByb3ZpZGVySm9iAaE7UerBfkKVNjaa_Qh69Q
#              AFByb3ZpZGVySm9iAaE7Ue9Ze1CP_cVW5SsOcA
#     emulator vs NumPy: r = 0.994, mean |diff| 0.049, 72/72 features within
#     3 sigma of shot noise.
# =============================================================================


# ---------------------------------------------------------------- CELL 1 ----
# Make this repo importable inside the workspace (it has no pip; uv instead).
import os, sys, subprocess, shutil, importlib.util

if not os.path.isdir("iontraps_qrc"):
    subprocess.run(["git", "clone", "https://github.com/BinhDangNguyn/iontraps_qrc.git"], check=True)
sys.path.insert(0, os.path.abspath("iontraps_qrc/src"))

qrc_need = {"pandas": "pandas", "sklearn": "scikit-learn", "sympy": "sympy", "altair": "altair"}
qrc_missing = [pkg for mod, pkg in qrc_need.items() if importlib.util.find_spec(mod) is None]
if qrc_missing:
    print("installing:", qrc_missing)
    subprocess.run([shutil.which("uv"), "pip", "install", "--python", sys.executable, *qrc_missing], check=True)

from iontraps_qrc import core
from iontraps_qrc.sweep import make_spec
print("ok: core loaded")

# ---------------------------------------------------------------- CELL 2 ----
# Build the reservoir circuits. No job is sent, nothing is charged.
import numpy as np
from pytket.circuit import Bit

# Same frozen reservoir as the sweep: 6 qubits (3 input + 3 memory), L = 6, seed 1234
qrc_spec = make_spec(6, 3, 3, 6)
qrc_spec.freeze(write=False)

# 3 probe inputs, angles in half-turns (theta in [0,1), phi in [0,2))
qrc_rng = np.random.default_rng(7)
qrc_angles = np.stack([qrc_rng.uniform(0, 1, (3, 6, 3)),
                       qrc_rng.uniform(0, 2, (3, 6, 3))], axis=-1)

qrc_tpl, qrc_mid, qrc_fin, qrc_syms = core.build_template(qrc_spec)
qrc_order = list(qrc_mid) + list(qrc_fin)     # 18 mid-circuit bits, then 6 final bits
qrc_circuits = []
for qrc_a in qrc_angles:
    qrc_c = core.substitute(qrc_tpl, qrc_syms, qrc_a)
    # one 24-bit register "c": c[0..17] = mid-circuit readouts, c[18..23] = final snapshot
    qrc_c.rename_units({qrc_bit: Bit("c", qrc_k) for qrc_k, qrc_bit in enumerate(qrc_order)})
    AutoRebase(GATESET).apply(qrc_c)
    qrc_circuits.append(qrc_c)

# noiseless reference from our own simulator, same circuits, 4000 shots
qrc_ref = core.features_from_bits(
    core.run_numpy(qrc_spec, qrc_angles, 4000, seed=0, verbose=False),
    qrc_spec, correlators=False).astype(float)

qrc_budget = core.circuit_budget(qrc_spec)
mo.md(f"""**Reservoir circuits ready:** {len(qrc_circuits)} circuits, {qrc_spec.n_qubits} qubits,
L = {qrc_spec.n_steps}, {qrc_budget.n_2q} two-qubit gates and {qrc_budget.n_meas} measurements each
(18 mid-circuit measure-and-reset), {qrc_circuits[0].n_gates} gates after rebase.""")


# ---------------------------------------------------------------- CELL 3 ----
# The button. Nothing is sent until you press it.
qrc_platform = mo.ui.dropdown(["nexus:H2-Emulator", "nexus:H2-2E", "nexus:H2-1E"],
                              value="nexus:H2-Emulator", label="Emulator")
qrc_shots = mo.ui.number(start=10, stop=1000, step=10, value=200, label="Shots")
qrc_submit = mo.ui.run_button(label="Submit reservoir circuits", kind="success")
mo.hstack([qrc_platform, qrc_shots, qrc_submit], justify="start")


# ---------------------------------------------------------------- CELL 4 ----
# Submit and collect. Prints the JOB IDs.
mo.stop(not qrc_submit.value,
        mo.callout(mo.md("Press **Submit reservoir circuits** to run the job"), kind="info"))

qrc_qpu = QPU(platform=qrc_platform.value)
qrc_jobs = [qrc_qpu.run(qrc_circ, shots=qrc_shots.value) for qrc_circ in qrc_circuits]
qrc_job_ids = [str(qrc_j.job_id) for qrc_j in qrc_jobs]
print("JOB IDs:", qrc_job_ids)
qrc_counts = [qrc_jj.counts(timeout=1800)[0] for qrc_jj in qrc_jobs]
mo.callout(mo.md("Submitted to **" + qrc_platform.value + "**: " +
                 ", ".join("**" + qrc_id + "**" for qrc_id in qrc_job_ids)), kind="success")


# ---------------------------------------------------------------- CELL 5 ----
# Compare with our simulator and save the evidence file.
import json, datetime

def qrc_features(counts, n_bits, reverse):
    total, z = 0, np.zeros(n_bits)
    for key, val in counts.items():
        s = key if isinstance(key, str) else "".join(str(int(x)) for x in key)
        s = s.replace(" ", "")[-n_bits:]
        if reverse:
            s = s[::-1]
        z += val * np.array([1 - 2 * int(ch) for ch in s])
        total += val
    return z / total

qrc_nb = qrc_ref.shape[1]
qrc_cands = {}
for qrc_rev_try in (False, True):
    qrc_f_try = np.array([qrc_features(cnt, qrc_nb, qrc_rev_try) for cnt in qrc_counts])
    qrc_cands[qrc_rev_try] = (np.corrcoef(qrc_f_try.ravel(), qrc_ref.ravel())[0, 1], qrc_f_try)
qrc_rev = max(qrc_cands, key=lambda r: qrc_cands[r][0])
qrc_r, qrc_emu = qrc_cands[qrc_rev]
qrc_sig = np.sqrt(np.clip(1 - qrc_emu ** 2, 1e-12, None) / qrc_shots.value
                  + np.clip(1 - qrc_ref ** 2, 1e-12, None) / 4000)
qrc_z = (qrc_emu - qrc_ref) / qrc_sig

qrc_record = {
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "platform": qrc_platform.value, "job_ids": qrc_job_ids,
    "cell": qrc_spec.tag, "n_qubits": qrc_spec.n_qubits, "L": qrc_spec.n_steps,
    "reservoir_seed": qrc_spec.seed, "shots": qrc_shots.value,
    "two_qubit_gates": qrc_budget.n_2q,
    "bit_order": "c[0..17] mid-circuit, c[18..23] final" + (" (key reversed)" if qrc_rev else ""),
    "angles_halfturns": qrc_angles.tolist(),
    "features_emulator": qrc_emu.tolist(), "features_reference_numpy": qrc_ref.tolist(),
    "counts": [{str(k): int(v) for k, v in cnt.items()} for cnt in qrc_counts],
    "agreement": {"pearson_r": float(qrc_r),
                  "mean_abs_diff": float(np.mean(np.abs(qrc_emu - qrc_ref))),
                  "share_within_3sigma": float(np.mean(np.abs(qrc_z) < 3))},
}
with open("emulator_run_6q_L6.json", "w") as qrc_fh:
    json.dump(qrc_record, qrc_fh, indent=2)

qrc_ag = qrc_record["agreement"]
mo.md(f"""### Emulator execution evidence
**Platform:** {qrc_platform.value} &nbsp; **Job IDs:** {", ".join(qrc_job_ids)}

Emulator vs our NumPy simulator on the same {len(qrc_circuits)} circuits ({qrc_nb} features each):
correlation **r = {qrc_ag['pearson_r']:.3f}**, mean |difference| **{qrc_ag['mean_abs_diff']:.3f}**,
**{qrc_ag['share_within_3sigma']:.0%}** of features within 3 sigma of shot noise.

Saved to `emulator_run_6q_L6.json`.""")
