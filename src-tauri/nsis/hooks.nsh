; NSIS installer hooks for FF Downloader.
; These macros and callbacks are invoked by Tauri's NSIS template
; during both fresh installs AND silent OTA (updater) installs.


; ────────────────────────────────────────────────────────────────
; MUI_CUSTOMFUNCTION_GUIINIT — MANUPRODUCTKEY registry bridge
; ────────────────────────────────────────────────────────────────
;
; Changing bundle.publisher from unset to "AnInsomniacy" shifted
; the MANUFACTURER variable (motrix → AnInsomniacy), which moved
; the MANUPRODUCTKEY registry path:
;
;   OLD: HKCU\Software\motrix\MotrixNext        (≤ 3.6.1)
;   NEW: HKCU\Software\AnInsomniacy\FFDownloader   (≥ 3.6.2)
;
; The template's PageLeaveReinstall reads MANUPRODUCTKEY to build
; the `_?=` parameter when launching the old uninstaller.  An
; empty `_?=` causes the uninstaller to fail its integrity check
; → "NSIS Error: Error launching installer" (issue #159).
;
; Fix: copy the install-directory value from the old key to the
; new key BEFORE any pages are displayed.
;
; MUI2 owns .onGUIInit (via MUI_FUNCTION_GUIINIT), so we cannot
; define it directly.  Instead, use MUI_CUSTOMFUNCTION_GUIINIT to
; register a named function that MUI2 calls from within its own
; .onGUIInit.  This !define must appear BEFORE !insertmacro
; MUI_LANGUAGE — which it does, since hooks are included at
; template line 33, well before the language macros.
;
; Execution order:
;   .onInit  (template)  → RestorePreviousInstallLocation (reads
;                           new MANUPRODUCTKEY — empty, no-op)
  ;   .onGUIInit (MUI2)    → calls FFDownloaderBridgeMANUPRODUCTKEY (this)
;   Welcome page
;   MULTIUSER page       → RestorePreviousInstallLocation called
;                           again (now succeeds via bridged data)
;   Reinstall page       → PageLeaveReinstall reads MANUPRODUCTKEY
;                           (now succeeds — _?= has correct path)
;   Section Install      → PREINSTALL hook (handles the rest)
;
; Silent mode: .onGUIInit is NOT called, but silent mode skips all
; pages — PageLeaveReinstall never fires, and the PREINSTALL hook
; handles directory redirection independently.
;
; This function is safe for fresh installs (old key absent → no-op)
; and for already-migrated users (old key already cleaned up by
; PREINSTALL → no-op).

!define MUI_CUSTOMFUNCTION_GUIINIT FFDownloaderBridgeMANUPRODUCTKEY

Function FFDownloaderBridgeMANUPRODUCTKEY
  ; Try HKCU first (old currentUser installs write here)
  ReadRegStr $R0 HKCU "Software\motrix\MotrixNext" ""
  StrCmp $R0 "" _ff_downloader_bridge_hklm 0
    WriteRegStr HKCU "Software\AnInsomniacy\FFDownloader" "" $R0
    DetailPrint "Bridged MANUPRODUCTKEY (HKCU): $R0"
    Goto _ff_downloader_bridge_done

  _ff_downloader_bridge_hklm:
  ; Try HKLM (unlikely but defensive: per-machine with old publisher)
  ReadRegStr $R0 HKLM "Software\motrix\MotrixNext" ""
  StrCmp $R0 "" _ff_downloader_bridge_done 0
    WriteRegStr HKLM "Software\AnInsomniacy\FFDownloader" "" $R0
    DetailPrint "Bridged MANUPRODUCTKEY (HKLM): $R0"

  _ff_downloader_bridge_done:
FunctionEnd


; ────────────────────────────────────────────────────────────────
; NSIS_HOOK_PREINSTALL — in-place upgrade migration
; ────────────────────────────────────────────────────────────────

!macro NSIS_HOOK_PREINSTALL
  ; ── Migration: currentUser → both ──────────────────────────────
  ;
  ; Versions ≤ 3.6.2-beta.1 shipped with installMode "currentUser",
  ; which writes the uninstall registry entry under HKCU.
  ;
  ; Starting from 3.6.2, installMode is "both".  In silent/update
  ; mode (/S), the "both" NSIS template defaults to per-machine
  ; scope and reads HKLM — it will NOT find the old HKCU entry,
  ; causing a duplicate installation.
  ;
  ; Fix: unconditionally check HKCU for a previous per-user install.
  ; If found:
  ;   1. Strip surrounding quotes from InstallLocation
  ;   2. Redirect $INSTDIR + $OUTDIR to the old path
  ;   3. Delete the stale HKCU uninstall entry (prevents "Apps &
  ;      Features" from showing two FFDownloader rows)
  ;   4. Delete the orphaned MANUPRODUCTKEY left by the old
  ;      MANUFACTURER value ("motrix" → "AnInsomniacy")
  ;   5. Remove any Program Files residual from prior buggy installs
  ;
  ; Registry key: HKCU\Software\Microsoft\Windows\CurrentVersion
  ;                 \Uninstall\FFDownloader
  ; Tauri uses the productName (not identifier) as the key name.
  ; The InstallLocation value is stored WITH surrounding quotes
  ; (e.g., "C:\Users\xxx\AppData\Local\FFDownloader"), so we must
  ; strip them before assigning to $INSTDIR.
  ;
  ; Safety: this hook runs inside `Section Install`, BEFORE any
  ; File commands or registry writes.  The template's subsequent
  ; `WriteRegStr SHCTX UNINSTKEY ...` will create the definitive
  ; new entry — nothing between this hook and that write depends
  ; on the HKCU data we delete here.  See installer.nsi lines
  ; 619–700 for the authoritative execution order.

  ReadRegStr $R0 HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\FFDownloader" \
    "InstallLocation"
  StrCmp $R0 "" _ff_downloader_skip_migration 0

    ; ── 1. Strip surrounding quotes ──────────────────────────────
    ; "C:\path" → C:\path
    ; Uses named labels instead of fragile +N relative offsets.
    StrCpy $R1 $R0 1        ; first character
    StrCmp $R1 '"' 0 _ff_downloader_no_lead_quote
      StrCpy $R0 $R0 "" 1   ; remove first char
    _ff_downloader_no_lead_quote:
    StrLen $R1 $R0
    IntOp $R1 $R1 - 1
    StrCpy $R2 $R0 1 $R1    ; last character
    StrCmp $R2 '"' 0 _ff_downloader_no_trail_quote
      StrCpy $R0 $R0 $R1    ; remove last char
    _ff_downloader_no_trail_quote:

    ; ── 2. Redirect install directory ────────────────────────────
    StrCpy $INSTDIR $R0
    ; Tauri's template calls `SetOutPath $INSTDIR` BEFORE this hook,
    ; so $OUTDIR still points to the template's default.  Re-issue
    ; SetOutPath to sync $OUTDIR with the corrected $INSTDIR.
    SetOutPath $INSTDIR
    DetailPrint "Migrated install directory: $INSTDIR"

    ; ── 3. Delete stale HKCU uninstall entry ─────────────────────
    ; This is the root cause of duplicate "Apps & Features" entries.
    ; The Install section will write a fresh entry to SHCTX (HKLM
    ; for "all users", HKCU for "current user") at the end.
    DeleteRegKey HKCU \
      "Software\Microsoft\Windows\CurrentVersion\Uninstall\FFDownloader"
    DetailPrint "Deleted stale HKCU uninstall entry"

    ; ── 4. Delete orphaned MANUPRODUCTKEY ────────────────────────
    ; Versions that shipped with publisher unset derived MANUFACTURER
    ; from the identifier's second segment ("motrix"), writing the
    ; install-location cache to HKCU\Software\motrix\MotrixNext.
    ; Now that publisher = "AnInsomniacy", MANUPRODUCTKEY changed to
    ; HKCU\Software\AnInsomniacy\FFDownloader.  Clean up the old one
    ; so RestorePreviousInstallLocation does not read stale data.
    DeleteRegKey HKCU "Software\motrix\MotrixNext"
    DeleteRegKey /ifempty HKCU "Software\motrix"
    DetailPrint "Deleted orphaned registry key: Software\motrix"

    ; ── 5. Remove Program Files residual ─────────────────────────
    ; A prior beta with a SetOutPath bug left partial files in the
    ; per-machine default directory while the real install lived in
    ; AppData\Local.  Clean up only if $INSTDIR is NOT under the
    ; system Program Files directory (i.e., the migration target
    ; differs from the per-machine default location).
    ;
    ; Dynamic comparison: extract the first N characters of $INSTDIR
    ; where N = length of $PROGRAMFILES64, then compare.  This works
    ; regardless of which drive Windows is installed on.
    StrLen $R3 "$PROGRAMFILES64"
    StrCpy $R4 $INSTDIR $R3
    StrCmp $R4 "$PROGRAMFILES64" _ff_downloader_skip_pf_cleanup 0
      ; $INSTDIR is NOT under Program Files — safe to remove residual
      IfFileExists "$PROGRAMFILES64\FFDownloader\*.*" 0 _ff_downloader_skip_pf_cleanup
        RMDir /r "$PROGRAMFILES64\FFDownloader"
        DetailPrint "Removed Program Files residual: $PROGRAMFILES64\FFDownloader"
    _ff_downloader_skip_pf_cleanup:

  _ff_downloader_skip_migration:

  ; Defense-in-depth: kill any lingering sidecar before file copy.
  ; Tauri bundles externalBin as motrix-next-engine.exe.
  ; On Windows, a running .exe is locked by the OS and cannot be
  ; overwritten.  taskkill exits 128 if the process is absent.
  nsExec::Exec 'taskkill /F /IM motrix-next-engine.exe'
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ; Flush Windows icon cache so updated icons appear immediately.
  ; ie4uinit.exe is a built-in Windows 10/11 system utility that
  ; soft-refreshes the shell icon display without requiring a reboot.
  ; This is the industry-standard approach used by Electron, VS Code,
  ; and other major desktop applications.
  nsExec::ExecToLog 'ie4uinit.exe -show'
!macroend
