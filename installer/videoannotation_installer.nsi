; NSIS installer for Video Annotation Tool (x86-64)
; - Upgrades in place (detects prior install via registry and $INSTDIR)
; - Preserves user settings (under %APPDATA%\${APP_NAME} by default)
; - Writes an uninstaller and proper registry entries

Unicode true

!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ---------------------------
; Product metadata
; These may be overridden by makensis /D switches
!define APP_NAME   "Video Annotation Tool"
!define APP_EXE    "Video Annotation Tool.exe"
!ifndef VERSION
  !define VERSION  "1.2.1"
!endif
!ifndef ICON
  !define ICON     "assets\\icon.ico"
!endif
!define COMPANY    "Acme"
; Stable GUID used to identify this app's uninstall entry (do not change once released)
!define APP_GUID   "{B8F1B54B-27D5-4539-9D8B-1E9B9E2E0B6D}"

; ---------------------------
; Installer settings
Name "${APP_NAME}"
; Write the installer to the repo root (parent of installer\)
OutFile "${__FILEDIR}\..\${APP_NAME}-Setup-${VERSION}.exe"
RequestExecutionLevel admin
BrandingText "${APP_NAME} ${VERSION}"
Icon "${ICON}"
UninstallIcon "${ICON}"
SetCompressor /SOLID lzma
SetCompress auto

; Default install dir and remember previous
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${COMPANY}\${APP_NAME}" "InstallLocation"

; ---------------------------
; Pages
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

; ---------------------------
; Helper macros
!macro TrySilentUninstall
  ; If an existing Uninstall.exe is present in $INSTDIR, run it silently and keep dir
  IfFileExists "$INSTDIR\Uninstall.exe" 0 +3
    DetailPrint "Uninstalling previous version from $INSTDIR"
    ExecWait '"$INSTDIR\Uninstall.exe" /S _?=$INSTDIR'
!macroend

; ---------------------------
Section "Install"
  SetRegView 64
  SetOverwrite ifnewer
  SetOutPath "$INSTDIR"

  ; Attempt uninstall of previous version (in-place upgrade)
  !insertmacro TrySilentUninstall

  ; Main application binary (built by PyInstaller onefile)
  ; The script resides in installer, so reference the parent directory's dist folder
  File "..\dist\${APP_EXE}"

  ; Shortcuts
  ; Use the installed EXE as the shortcut icon to avoid referencing build-time assets
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Registry: remember install location and uninstall info
  WriteRegStr HKLM "Software\${COMPANY}\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\${COMPANY}\${APP_NAME}" "Version" "${VERSION}"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "Publisher" "${COMPANY}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}" "NoRepair" 1
SectionEnd

; ---------------------------
Section "Uninstall"
  SetRegView 64

  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"

  ; Remove program files (preserve user settings)
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  ; Uninstall registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_GUID}"
  DeleteRegKey HKLM "Software\${COMPANY}\${APP_NAME}"

  ; NOTE: We intentionally do NOT remove user settings under %APPDATA%\${APP_NAME}
  ; If you want to optionally remove them, uncomment below and prompt the user.
  ; MessageBox MB_ICONQUESTION|MB_YESNO "Remove user settings as well?" IDNO +3
  ;  RMDir /r "$APPDATA\${APP_NAME}"
  ;  DetailPrint "Removed user settings at $APPDATA\${APP_NAME}"
SectionEnd
