# SMOXI Service — Nuitka + Inno Setup packaging

Professional Windows release packaging.

## Prerequisites

- Python 3.11+ venv with `requirements/production.txt` (+ `nuitka`, `ordered-set`, `zstandard`)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` on PATH or edit script)
- Optional: code-signing certificate

## Build EXE (Nuitka)

```powershell
pwsh -File scripts/build_nuitka.ps1
```

Output: `dist/smoxi-service/` (onedir) or single EXE depending on flags.

## Build installer (Inno Setup)

```powershell
pwsh -File scripts/build_installer.ps1
```

Produces `installer/output/SMOXIServiceSetup-x.y.z.exe`.

## Smoke checklist (clean VM)

1. Install → launch → login `admin` / seed password
2. Create quick intake WO
3. Open Calendar, Notifications, Reports
4. Uninstall cleanly
