#!/usr/bin/env bash
# Local validation for terraform-managed-openshift-state.
# No cloud credentials required for default checks.
#
# Usage (from lab root):
#   ./scripts/validate-local.sh
#   ./scripts/validate-local.sh --with-cloud   # also runs recovery inventory scripts

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_CLOUD=false
FAILURES=0
MIN_TF_VERSION="1.7.0"

for arg in "$@"; do
  case "$arg" in
    --with-cloud) WITH_CLOUD=true ;;
    -h|--help)
      echo "Usage: $0 [--with-cloud]"
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

version_ge() {
  # Returns 0 if $1 >= $2 (semver-ish x.y.z)
  local IFS=.
  local i ver_a=($1) ver_b=($2)
  for i in 0 1 2; do
    local a=${ver_a[$i]:-0} b=${ver_b[$i]:-0}
    if ((10#$a > 10#$b)); then return 0; fi
    if ((10#$a < 10#$b)); then return 1; fi
  done
  return 0
}

resolve_terraform() {
  if command -v terraform >/dev/null 2>&1; then
    local ver
    ver="$(terraform version -json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["terraform_version"])' 2>/dev/null || terraform version | head -1 | awk '{print $2}' | tr -d v)"
    if version_ge "$ver" "$MIN_TF_VERSION"; then
      command -v terraform
      return 0
    fi
  fi

  local cache="${ROOT}/.cache"
  local os arch tf
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "${arch}" in
    x86_64) arch="amd64" ;;
    arm64|aarch64) arch="arm64" ;;
  esac
  tf="${cache}/terraform"
  if [ ! -x "${tf}" ]; then
    echo "  … downloading Terraform 1.7.5 for ${os}-${arch}"
    mkdir -p "${cache}"
    curl -fsSL \
      "https://releases.hashicorp.com/terraform/1.7.5/terraform_1.7.5_${os}_${arch}.zip" \
      -o "${cache}/tf.zip"
    unzip -qo "${cache}/tf.zip" -d "${cache}"
    rm "${cache}/tf.zip"
  fi
  echo "${tf}"
}

echo "==> Validating from ${ROOT}"
echo ""

TF="$(resolve_terraform)"
echo "Terraform: $("${TF}" version | head -1)"
echo ""

# --- Shell scripts ---
echo "Shell scripts"
for f in scripts/recovery/*.sh; do
  if bash -n "${f}"; then
    pass "$(basename "${f}") syntax"
  else
    fail "$(basename "${f}") syntax"
  fi
done
echo ""

# --- alert.py ---
echo "Python"
if python3 scripts/alert.py "validate-local smoke test" >/dev/null 2>&1; then
  pass "alert.py runs without webhook"
else
  fail "alert.py"
fi
echo ""

# --- Workflow YAML ---
echo "GitHub Actions workflow"
if ruby -ryaml -e "YAML.load_file('.github/workflows/drift-detection.yml')" >/dev/null 2>&1; then
  pass "drift-detection.yml parses"
else
  fail "drift-detection.yml parse error"
fi
echo ""

# --- terraform fmt ---
echo "Terraform format"
if "${TF}" fmt -check -recursive . >/dev/null 2>&1; then
  pass "terraform fmt"
else
  fail "terraform fmt — run: terraform fmt -recursive ."
fi
echo ""

# --- terraform validate ---
echo "Terraform validate"
validate_dir() {
  local dir="$1"
  local backend_flag="${2:-}"
  (
    cd "${dir}"
    if [ "${backend_flag}" = "false" ]; then
      "${TF}" init -backend=false -input=false >/dev/null
    else
      "${TF}" init -input=false >/dev/null
    fi
    "${TF}" validate >/dev/null
  )
}

for dir in bootstrap/aws bootstrap/azure bootstrap/gcp; do
  if validate_dir "${dir}"; then
    pass "${dir}"
  else
    fail "${dir}"
  fi
done

for dir in modules/rosa-cluster modules/aro-cluster modules/osd-cluster; do
  if validate_dir "${dir}"; then
    pass "${dir}"
  else
    fail "${dir}"
  fi
done

for dir in environments/*/; do
  dir="${dir%/}"
  if validate_dir "${dir}" false; then
    pass "${dir}"
  else
    fail "${dir}"
  fi
done
echo ""

# --- Optional cloud inventory ---
if [ "${WITH_CLOUD}" = true ]; then
  echo "Recovery inventory (requires cloud CLIs + credentials)"
  for s in rosa aro osd; do
    if "./scripts/recovery/${s}-orphan-cleanup.sh" inventory >/dev/null 2>&1; then
      pass "${s} inventory"
    else
      fail "${s} inventory — check CLI installed and credentials configured"
    fi
  done
  echo ""
fi

if [ "${FAILURES}" -eq 0 ]; then
  echo "==> All checks passed"
  exit 0
else
  echo "==> ${FAILURES} check(s) failed"
  exit 1
fi
