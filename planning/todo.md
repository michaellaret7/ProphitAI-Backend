### Task: Fix matmul warnings in `calculations_v2/risk/calculator._to_psd`

Context: Terminal shows RuntimeWarnings at `backend/src/calculations_v2/risk/calculator.py:14` during covariance PSD reconstruction: divide by zero, overflow, and invalid value encountered in matmul.

Goal: Implement a minimal, safe fix to sanitize inputs/outputs in `_to_psd`, prevent inf/NaN propagation, and ensure robust PSD covariance reconstruction without changing public APIs.

Plan / TODOs:
1) Confirm source line and function causing warnings in `_to_psd` (read-only). [ ]
2) Sanitize covariance input: replace NaN/Inf with 0; enforce symmetry. [ ]
3) Stable eigen handling: floor negatives to small positive; set non-finite eigenvalues to floor; reconstruct via `vecs @ diag(vals) @ vecs.T`. [ ]
4) Post-check result: re-symmetrize and, if any non-finite remains, fallback to diagonal-only covariance. [ ]
5) Run lints on modified file; keep code simple and minimal. [ ]

Review (to be filled after implementation):
- Summary of changes, impact, and any follow-ups.