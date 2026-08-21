#!/usr/bin/env python3
"""
Script di sincronizzazione: copia il dashboard HTML da OneDrive → GitHub repo
quando il file su OneDrive cambia, e opzionalmente fa commit automatico.

Uso:
    python3 sync_oncologia_dashboard.py

Configurazione:
    Modifica i path sotto CONFIGURATION
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import hashlib

# ==============================================================================
# CONFIGURATION
# ==============================================================================

ONEDRIVE_HTML = Path.home() / "Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/dashboard/oncologia-concorso.html"
GITHUB_REPO = Path.home() / "Documents/oncologia-concorso-pages"
GITHUB_HTML = GITHUB_REPO / "oncologia-concorso.html"

AUTO_COMMIT = True  # Se True, fa commit automatico su GitHub
COMMIT_MESSAGE = "Update dashboard HTML from OneDrive"

# ==============================================================================
# UTILITIES
# ==============================================================================

def file_hash(file_path):
    """Calcola hash MD5 di un file"""
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def log_msg(msg, level="INFO"):
    """Log con timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def run_git_command(cmd, cwd=None):
    """Esegui comando git e ritorna output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or GITHUB_REPO,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        log_msg(f"Git error: {e.stderr}", "ERROR")
        return None

def sync_dashboard():
    """Sincronizza il file HTML da OneDrive → GitHub"""

    # 1. Verifiche preliminari
    if not ONEDRIVE_HTML.exists():
        log_msg(f"❌ File su OneDrive non trovato: {ONEDRIVE_HTML}", "ERROR")
        return False

    if not GITHUB_REPO.exists():
        log_msg(f"❌ Repository GitHub non trovato: {GITHUB_REPO}", "ERROR")
        return False

    # 2. Calcola hash prima e dopo (per verificare se è cambiato)
    hash_before = file_hash(GITHUB_HTML) if GITHUB_HTML.exists() else None

    # 3. Copia il file
    try:
        log_msg(f"📋 Copiando {ONEDRIVE_HTML.name}...")
        shutil.copy2(ONEDRIVE_HTML, GITHUB_HTML)
        log_msg(f"✅ File copiato in {GITHUB_HTML}")
    except Exception as e:
        log_msg(f"❌ Errore nella copia: {e}", "ERROR")
        return False

    # 4. Verifica che il file sia cambiato
    hash_after = file_hash(GITHUB_HTML)
    if hash_before == hash_after:
        log_msg("ℹ️  File non è cambiato (hash identico), niente da fare")
        return True

    # 5. Se AUTO_COMMIT, fai commit su GitHub
    if AUTO_COMMIT:
        log_msg("🔄 Preparando commit su GitHub...")

        # Verifica che siamo in un repo git
        status = run_git_command(["git", "rev-parse", "--git-dir"])
        if not status:
            log_msg("❌ Non sei in un repository git", "ERROR")
            return False

        # Aggiungi il file
        run_git_command(["git", "add", "oncologia-concorso.html"])

        # Commit
        result = run_git_command([
            "git", "commit",
            "-m", f"{COMMIT_MESSAGE} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ])

        if result is not None:
            log_msg(f"✅ Commit effettuato: {result[:60]}...")
        else:
            log_msg("⚠️  Commit non effettuato (forse nessuna modifica?)", "WARN")

    return True

def watch_mode():
    """Modalità 'watch': monitora il file e sincronizza quando cambia"""
    log_msg("👀 Watch mode attivato (premi Ctrl+C per fermare)")
    log_msg(f"   Sorgente: {ONEDRIVE_HTML}")
    log_msg(f"   Destinazione: {GITHUB_HTML}")

    last_hash = None

    try:
        while True:
            current_hash = file_hash(ONEDRIVE_HTML)

            if current_hash != last_hash:
                if last_hash is not None:  # Skippa il primo check
                    log_msg("📝 Cambio rilevato, sincronizzando...")
                    sync_dashboard()
                last_hash = current_hash

            # Controlla ogni 5 secondi
            import time
            time.sleep(5)

    except KeyboardInterrupt:
        log_msg("\n👋 Watch mode fermato")
        return True

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        # Modalità watch (monitora continuamente)
        watch_mode()
    else:
        # Modalità one-shot (sincronizza una volta)
        log_msg("🚀 Sincronizzazione dashboard HTML")
        success = sync_dashboard()

        if success:
            log_msg("✨ Sincronizzazione completata!")
            sys.exit(0)
        else:
            log_msg("❌ Sincronizzazione fallita", "ERROR")
            sys.exit(1)
