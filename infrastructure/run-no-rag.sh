#!/usr/bin/env bash
# Run only from existing local artifacts; never build, pull images or publish ports.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
run_commit="$(git rev-parse HEAD)"
run_dirty=false
if [[ -n "$(git status --porcelain)" ]]; then run_dirty=true; fi
image="${NO_RAG_IMAGE:-sha256:3f1fc28da92c04f52ba621ac8837e010297c82982c04f13be86afd97301232b4}"
[[ "$image" =~ (sha256:)[a-f0-9]{64}$ ]] || { echo "Use a verified content-addressed image" >&2; exit 2; }
run_parent="$repo_root/artifacts/local-inference/runs"
mkdir -p "$run_parent"
run_name="shared-no-rag-$(date -u +%Y%m%dT%H%M%S)-$$"
terminal_options=()
for argument in "$@"; do
  if [[ "$argument" == --interactive ]]; then
    terminal_options=(-i)
    if [[ -t 0 && -t 1 ]]; then terminal_options=(-it); fi
  fi
done
printf 'Run output (unless --check): %s/%s\n' "$run_parent" "$run_name"
docker run "${terminal_options[@]}" --rm --pull=never --network none --read-only \
  --memory 3g --memory-swap 3g --cpus 2 \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  -e "CYBERSOC_EXECUTION_IMAGE=$image" -e "CYBERSOC_RUN_COMMIT=$run_commit" -e "CYBERSOC_RUN_DIRTY=$run_dirty" \
  --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  -v "$repo_root:/workspace:ro" -v "$run_parent:/runs:rw" \
  -w /workspace --entrypoint python "$image" \
  -B -m ai.no_rag.run --output "/runs/$run_name" "$@"
