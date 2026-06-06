#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

log() {
  printf '\n==> %s\n' "$1"
}

have_command() {
  command -v "$1" >/dev/null 2>&1
}

ensure_apt_packages() {
  if ! have_command apt-get; then
    log "apt-get unavailable; skipping OS package installation"
    return
  fi

  local packages=(python3.12-venv)
  if ! have_command google-chrome && ! have_command chromium && ! have_command chromium-browser; then
    packages+=(google-chrome-stable)
  fi

  log "Installing OS packages: ${packages[*]}"
  sudo apt-get update
  if ! sudo apt-get install -y "${packages[@]}"; then
    log "Chrome package install was unavailable; Playwright will install Chromium instead"
    sudo apt-get install -y python3.12-venv
  fi
}

ensure_backend_environment() {
  log "Creating Python 3.12 virtual environment"
  cd "$API_DIR"
  python3.12 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate

  log "Installing backend editable dev dependencies"
  python -m pip install --upgrade pip
  pip install -e ".[dev]"

  log "Installing Playwright Chromium browser support"
  python -m playwright install --with-deps chromium
}

ensure_frontend_environment() {
  log "Installing frontend dependencies from package-lock.json"
  cd "$WEB_DIR"
  npm ci
}

verify_screenshot_support() {
  log "Verifying Playwright/Chrome screenshot support"
  cd "$API_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python - <<'PY'
from pathlib import Path
from shutil import which

from playwright.sync_api import sync_playwright

output = Path(".venv/screenshot-smoke.png")
browser_path = which("google-chrome") or which("chromium") or which("chromium-browser")
with sync_playwright() as playwright:
    launch_options = {"headless": True}
    if browser_path:
        launch_options["executable_path"] = browser_path
    browser = playwright.chromium.launch(**launch_options)
    page = browser.new_page(viewport={"width": 640, "height": 480})
    page.set_content("<html><body><h1>DeedScout screenshot smoke test</h1></body></html>")
    page.screenshot(path=str(output), full_page=True)
    browser.close()

if not output.exists() or output.stat().st_size == 0:
    raise SystemExit("Playwright screenshot smoke test did not create an image")

print(f"Screenshot smoke test wrote {output} ({output.stat().st_size} bytes)")
PY
}

main() {
  log "Configuring DeedScout Sarasota cloud-agent environment"
  ensure_apt_packages
  ensure_backend_environment
  ensure_frontend_environment
  verify_screenshot_support
  log "Cloud-agent environment setup completed"
}

main "$@"
