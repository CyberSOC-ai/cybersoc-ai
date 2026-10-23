# S1-T03 PR review fixes

Date: 2026-10-23. Review: [Anas's required change on PR #81](https://github.com/CyberSOC-ai/cybersoc-ai/pull/81#discussion_r4361376008).

## Malformed server responses

Previously, a simulated `/completion` stream yielding `[]` raised an uncaught
`AttributeError`. The CLI stopped before saving scores and left the experiment
marked `running`. This was a software reproduction, not an observed failure in
the historical Qwen/Phi runs.

The client now validates response objects and the fields used for template
application, tokenization, completion content and measurements. Malformed data
raises the recognized `InvalidOutput` failure. The CLI regression reproduces the
exact empty-list event on the first case and a valid response on the second:
two attempted, one failed, one valid, twelve not attempted. Predictions, failures,
measurements, final scores and the artifact manifest are saved, with status
`completed_with_failures` and a completion timestamp. Transport tests cover other
malformed response shapes as well.

## Prompt identity

New experiment records reference `prompt.txt`, whose exact file bytes match the
recorded prompt SHA-256. `prompt.json` contains metadata and a copy of the decoded
template; it has a separate whole-artifact hash in the artifact manifest. Template
loading preserves UTF-8 newline bytes. Tests check the referenced file digest and
that the copied template matches the source.

Historical records referenced the JSON wrapper while recording the template
text digest. They are preserved unchanged and should be interpreted using that
older convention, rather than treating the digest as the wrapper's file hash.

## Dirty source records

The reported historical model runs used an uncommitted implementation over base
commit `e8014108784a9ed8c99b623115a3f8f5fe496382`, with `dirty=true`. Their snapshots
only preserved baseline code. They do not prove the exact evaluation code used;
see [the historical results limitations](LOCAL_RESULTS.md).

New runs preserve relevant local changes beyond `ai/baseline`: evaluation code,
contracts, dataset/protocol, experiment inputs and requirements/configuration.
`source-manifest.json` identifies exact bytes at repository-relative paths. The
experiment records its hash and declared scope alongside the real Git state.
Tests verify that a locally edited evaluator is copied and hashed without newline
normalization, and that unrelated `.env`/`.local` files are excluded. This does
not make a dirty checkout clean, capture dependencies outside the declared scope,
or replace pinned runtime/model identity and environment records.

## Detailed evidence access

Soulaiman requested code fixes and merge, with no ZIP or external artifact sharing.
The original detailed Qwen/Phi artifacts remain local and unpublished. Anas's
request for reviewer access is therefore still outstanding; the code fixes and
automated regression checks do not establish independent model-result review.
No reviewer approval or final benchmark readiness is claimed.

## Verification

Native Python 3.14.3: baseline discovery ran 27 tests (25 passed, two optional
backend-dependent skips); contracts passed 19 and evaluation passed 43. Ruff and
repository integrity checks passed. A fresh real Qwen smoke at
`.local/runs/qwen-review-fix` completed one valid attempt with thirteen not
attempted, and all recorded artifact hashes were independently checked. Its
base commit is `c389a665b359a6990c9fcb44aa973278ea491b19`, with `dirty=true` and
the expanded dependency snapshot. This one-case smoke checks runtime compatibility
and recording, not model quality or independent verification of historical runs.
