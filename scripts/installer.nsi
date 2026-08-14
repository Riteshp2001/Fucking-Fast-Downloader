Unicode true
SetCompressor /SOLID lzma
RequestExecutionLevel user

!include "MUI2.nsh"

!ifndef APP_VERSION
!error "APP_VERSION must be defined"
!endif
!ifndef APP_BASENAME
!error "APP_BASENAME must be defined"
!endif
!ifndef APP_DISPLAY_NAME
!error "APP_DISPLAY_NAME must be defined"
!endif
!ifndef BUNDLE_DIR
!error "BUNDLE_DIR must be defined"
!endif
!ifndef OUTPUT_FILE
!error "OUTPUT_FILE must be defined"
!endif
!ifndef APP_ICON
!error "APP_ICON must be defined"
!endif

Name "${APP_DISPLAY_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\${APP_DISPLAY_NAME}"
InstallDirRegKey HKCU "Software\${APP_DISPLAY_NAME}" "InstallLocation"

!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${BUNDLE_DIR}\*"

  WriteRegStr HKCU "Software\${APP_DISPLAY_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "DisplayName" "${APP_DISPLAY_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "Publisher" "Riteshp2001"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\${APP_DISPLAY_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_DISPLAY_NAME}\${APP_DISPLAY_NAME}.lnk" "$INSTDIR\${APP_BASENAME}.exe"
  CreateShortcut "$DESKTOP\${APP_DISPLAY_NAME}.lnk" "$INSTDIR\${APP_BASENAME}.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APP_DISPLAY_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_DISPLAY_NAME}\${APP_DISPLAY_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_DISPLAY_NAME}"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DISPLAY_NAME}"
  DeleteRegKey HKCU "Software\${APP_DISPLAY_NAME}"
  RMDir /r "$INSTDIR"
SectionEnd
