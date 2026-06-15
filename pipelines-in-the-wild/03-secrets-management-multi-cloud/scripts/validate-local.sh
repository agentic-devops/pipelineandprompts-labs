#!/usr/bin/env bash
# Local validation for secrets-management-multi-cloud manifests and scripts.
# No cluster or provider credentials required.
#
# Usage (from lab root):
#   ./scripts/validate-local.sh
#   ./scripts/validate-local.sh --with-cluster   # also runs oc/kubectl dry-run

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_CLUSTER=false
FAILURES=0

for arg in "$@"; do
  case "$arg" in
    --with-cluster) WITH_CLUSTER=true ;;
    -h|--help)
      echo "Usage: $0 [--with-cluster]"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }

echo "==> Validating from ${ROOT}"
echo ""

# --- YAML syntax ---
echo "YAML syntax"
if command -v ruby >/dev/null 2>&1; then
  if ruby -ryaml -e '
    require "yaml"
    Dir.glob("manifests/**/*.yaml").sort.each do |path|
      File.read(path).split(/^---\s*$/).each_with_index do |doc, i|
        next if doc.strip.empty?
        YAML.safe_load(doc)
      end
      puts path
    end
  ' >/dev/null 2>&1; then
    pass "all manifest YAML parses (ruby)"
  else
    fail "YAML parse error — run: ruby -ryaml -e \"...\" for details"
  fi
elif python3 -c "import yaml" >/dev/null 2>&1; then
  if python3 -c "
import yaml, glob
for f in sorted(glob.glob('manifests/**/*.yaml', recursive=True)):
    with open(f) as fh:
        for doc in yaml.safe_load_all(fh):
            pass
" 2>/dev/null; then
    pass "all manifest YAML parses (python)"
  else
    fail "YAML parse error"
  fi
else
  fail "no YAML parser — install ruby (built-in on macOS) or: pip install pyyaml"
fi
echo ""

# --- Shell scripts ---
echo "Shell scripts"
if bash -n vault/kubernetes-auth-setup.sh; then
  pass "vault/kubernetes-auth-setup.sh syntax"
else
  fail "vault/kubernetes-auth-setup.sh syntax"
fi
echo ""

# --- Placeholder check ---
echo "Placeholder comments"
if grep -r "AUTHOR TO VALIDATE" manifests/ --include="*.yaml" 2>/dev/null \
  | grep -vE '#.*AUTHOR TO VALIDATE' >/dev/null; then
  fail "uncommented AUTHOR TO VALIDATE placeholders in manifests/"
else
  pass "AUTHOR TO VALIDATE only in YAML comments"
fi
echo ""

# --- kubeconform ---
echo "Kubernetes schema (kubeconform)"
KUBECONFORM=""
if command -v kubeconform >/dev/null 2>&1; then
  KUBECONFORM="$(command -v kubeconform)"
else
  CACHE_DIR="${ROOT}/.cache"
  mkdir -p "${CACHE_DIR}"
  OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
  ARCH="$(uname -m)"
  case "${ARCH}" in
    x86_64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
  esac
  KUBECONFORM="${CACHE_DIR}/kubeconform-${OS}-${ARCH}"
  if [ ! -x "${KUBECONFORM}" ]; then
    echo "  … downloading kubeconform for ${OS}-${ARCH}"
    TMP="$(mktemp -d)"
    curl -fsSL \
      "https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-${OS}-${ARCH}.tar.gz" \
      -o "${TMP}/kubeconform.tar.gz"
    tar -xzf "${TMP}/kubeconform.tar.gz" -C "${TMP}"
    mv "${TMP}/kubeconform" "${KUBECONFORM}"
    chmod +x "${KUBECONFORM}"
    rm -rf "${TMP}"
  fi
fi

MANIFESTS=()
while IFS= read -r -d '' f; do
  MANIFESTS+=("$f")
done < <(find manifests -name '*.yaml' ! -path 'manifests/operator/*' -print0 | sort -z)

if "${KUBECONFORM}" \
  -strict \
  -ignore-missing-schemas \
  -schema-location default \
  -schema-location \
    'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  "${MANIFESTS[@]}"; then
  pass "kubeconform schema validation"
else
  fail "kubeconform reported errors"
fi
echo ""

# --- Optional cluster dry-run ---
if [ "${WITH_CLUSTER}" = true ]; then
  echo "Cluster dry-run"
  KUBE_CMD=""
  if command -v oc >/dev/null 2>&1 && oc whoami >/dev/null 2>&1; then
    KUBE_CMD="oc"
  elif command -v kubectl >/dev/null 2>&1 && kubectl config current-context >/dev/null 2>&1; then
    KUBE_CMD="kubectl"
  fi

  if [ -z "${KUBE_CMD}" ]; then
    fail "no logged-in oc/kubectl — skip with: $0 (without --with-cluster)"
  else
    if ${KUBE_CMD} apply -f manifests/namespace/ --dry-run=server && \
       ${KUBE_CMD} apply -f manifests/rbac/dev-secret-rbac.yaml --dry-run=server; then
      pass "${KUBE_CMD} dry-run: namespace + dev RBAC"
    else
      fail "${KUBE_CMD} dry-run failed"
    fi
    echo "  … SecretStore/ExternalSecret dry-run requires ESO CRDs (lab step 02)"
  fi
  echo ""
fi

# --- Summary ---
if [ "${FAILURES}" -eq 0 ]; then
  echo "==> All checks passed"
  exit 0
else
  echo "==> ${FAILURES} check(s) failed"
  exit 1
fi
