#!/usr/bin/env bash
# Local artifacts only. No image pulls, builds, external network or published ports.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
artifact_root="$repo_root/artifacts/local-inference/vector-v1"
store_name="cybersoc-vector-v1"
qdrant_image="qdrant/qdrant:v1.20.0@sha256:2d1b0bfd0a961275481ea09400fc98008216ae54e1b52ed7d24520d63050c644"
embed_image="cybersoc-rag-eval@sha256:4e3e26e112a65a2566ea2930eae2ef2fe02055d04327b6d739531aa2f5231c5c"
llm_image="sha256:3f1fc28da92c04f52ba621ac8837e010297c82982c04f13be86afd97301232b4"
embed_image="${VECTOR_EMBED_IMAGE:-$embed_image}"
llm_image="${VECTOR_LLM_IMAGE:-$llm_image}"
for selected_image in "$embed_image" "$llm_image"; do
  [[ "$selected_image" =~ (sha256:)[a-f0-9]{64}$ ]] || { echo "Use a verified content-addressed image" >&2; exit 2; }
done
mkdir -p "$artifact_root"
command="${1:?Choose start, stop, build, publish, snapshot, restore, evaluate, retrieve, preflight or investigate}"
shift
if [[ "$command" == start ]]; then
  if docker container inspect "$store_name" >/dev/null 2>&1; then
    [[ "$(docker inspect -f '{{index .Config.Labels "cybersoc.component"}}' "$store_name")" == vector-v1 ]]
    [[ "$(docker inspect -f '{{.Image}}' "$store_name")" == sha256:2d1b0bfd0a961275481ea09400fc98008216ae54e1b52ed7d24520d63050c644 ]]
    docker start "$store_name"
  else
    mkdir -p "$artifact_root/qdrant-storage"
    docker run -d --pull=never --name "$store_name" --label cybersoc.component=vector-v1 \
      --network none --read-only --memory 512m --memory-swap 512m --cpus 1 \
      --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
      -e QDRANT__TELEMETRY_DISABLED=true \
      --tmpfs /tmp:rw,nosuid,nodev,size=64m \
      --tmpfs "/qdrant/snapshots:rw,nosuid,nodev,uid=$(id -u),gid=$(id -g),size=128m" \
      -v "$artifact_root/qdrant-storage:/qdrant/storage:rw" "$qdrant_image"
  fi
  exit
fi
if [[ "$command" == stop ]]; then
  [[ "$(docker inspect -f '{{index .Config.Labels "cybersoc.component"}}' "$store_name")" == vector-v1 ]]
  docker stop "$store_name"
  exit
fi
image="$embed_image"
network=(--network "container:$store_name")
if [[ "$command" == build ]]; then network=(--network none); fi
if [[ "$command" == preflight || "$command" == investigate ]]; then
  image="$llm_image"; network=(--network none)
fi
run_commit="$(git rev-parse HEAD)"
run_dirty=false
if [[ -n "$(git status --porcelain)" ]]; then run_dirty=true; fi
docker run --rm --pull=never "${network[@]}" --read-only \
  --memory 3g --memory-swap 3g --cpus 2 --user "$(id -u):$(id -g)" \
  --cap-drop ALL --security-opt no-new-privileges \
  -e "VECTOR_EXECUTION_IMAGE=$image" -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e TOKENIZERS_PARALLELISM=false \
  -e "CYBERSOC_RUN_COMMIT=$run_commit" -e "CYBERSOC_RUN_DIRTY=$run_dirty" \
  --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  -v "$repo_root:/workspace:ro" -v "$artifact_root:/artifacts:rw" \
  -w /workspace --entrypoint python "$image" -B -m rag.vector.run "$command" "$@"
