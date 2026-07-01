#!/usr/bin/env bash
# Download SurrealDB v2 binary for desktop packaging.
#
# Usage:
#   bash desktop/download_surrealdb.sh              # current machine
#   bash desktop/download_surrealdb.sh darwin-arm64  # cross-fetch for CI matrix
#
# Output: desktop/resources/surrealdb/surreal (or surreal.exe on Windows fetch)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/desktop/binaries.env"
OUT_DIR="$ROOT/desktop/resources/surrealdb"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

SURREALDB_VERSION="${SURREALDB_VERSION:-2.5.0}"
SURREALDB_DOWNLOAD_ROOT="${SURREALDB_DOWNLOAD_ROOT:-https://download.surrealdb.com}"

detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Darwin)
      case "$arch" in
        arm64) echo "darwin-arm64" ;;
        x86_64) echo "darwin-amd64" ;;
        *) echo "unsupported macOS arch: $arch" >&2; exit 1 ;;
      esac
      ;;
    Linux)
      case "$arch" in
        x86_64 | amd64) echo "linux-amd64" ;;
        aarch64 | arm64) echo "linux-arm64" ;;
        *) echo "unsupported Linux arch: $arch" >&2; exit 1 ;;
      esac
      ;;
    MINGW* | MSYS* | CYGWIN*)
      echo "windows-amd64"
      ;;
    *)
      echo "unsupported OS: $os" >&2
      exit 1
      ;;
  esac
}

PLATFORM="${1:-$(detect_platform)}"
VERSION_TAG="v${SURREALDB_VERSION}"
BASE_URL="${SURREALDB_DOWNLOAD_ROOT}/${VERSION_TAG}"

mkdir -p "$OUT_DIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> SurrealDB ${VERSION_TAG} for ${PLATFORM}"
echo "    ${BASE_URL}"

case "$PLATFORM" in
  darwin-arm64 | darwin-amd64 | linux-amd64 | linux-arm64)
    ARCHIVE="surreal-${VERSION_TAG}.${PLATFORM}.tgz"
    curl -fsSL "${BASE_URL}/${ARCHIVE}" -o "$WORK/${ARCHIVE}"
    tar -xzf "$WORK/${ARCHIVE}" -C "$WORK"
    install -m 755 "$WORK/surreal" "$OUT_DIR/surreal"
    rm -f "$OUT_DIR/surreal.exe"
    ;;
  windows-amd64)
    EXE="surreal-${VERSION_TAG}.windows-amd64.exe"
    curl -fsSL "${BASE_URL}/${EXE}" -o "$OUT_DIR/surreal.exe"
    rm -f "$OUT_DIR/surreal"
    ;;
  *)
    echo "Unknown platform: $PLATFORM" >&2
    echo "Expected: darwin-arm64 | darwin-amd64 | linux-amd64 | linux-arm64 | windows-amd64" >&2
    exit 1
    ;;
esac

if [[ -f "$OUT_DIR/surreal" ]]; then
  "$OUT_DIR/surreal" version || true
fi

echo "==> Installed to $OUT_DIR"
