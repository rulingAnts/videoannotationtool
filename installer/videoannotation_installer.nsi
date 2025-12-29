; NSIS script for Visual Stimulus Kit Tool Windows installer
; Output: VisualStimulusKitToolSetup.exe

!include "nsDialogs.nsh"

# Default to per-user
!define APPNAME "Visual Stimulus Kit Tool"
!define COMPANY "Seth Johnston"
!define VERSION "2.0.3"

Name "Visual Stimulus Kit Tool"
OutFile "Visual Stimulus Kit Tool Setup ${VERSION}.exe"

# Allow user to choose install scope
InstallDirRegKey HKCU "Software\VisualStimulusKitTool" "Install_Dir"
InstallDir "$LocalAppData\Programs\Visual Stimulus Kit Tool"

# Variables for scope
Var AllUsers

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "${COMPANY}"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2025 ${COMPANY}"
VIAddVersionKey "FileDescription" "Visual Stimulus Kit Tool Installer"

# Custom page for install scope
Page custom SelectInstallScope
Page directory
Page instfiles

Var Dialog
Var RadioAll
Var RadioUser

Function .onInit
    StrCpy $AllUsers 0
FunctionEnd

Function SelectInstallScope
    nsDialogs::Create 1018
    Pop $Dialog
    StrCmp $Dialog error 0 +2
        Abort
    ${NSD_CreateRadioButton} 10 10 200 12 "Install for anyone using this computer (requires admin)" $Dialog
    Pop $RadioAll
    ${NSD_CreateRadioButton} 10 30 200 12 "Install just for me (no admin required)" $Dialog
    Pop $RadioUser
    ${NSD_SetState} $RadioUser 1
    nsDialogs::Show
    ; Default to per-user
    StrCpy $AllUsers 0
    ${NSD_GetState} $RadioAll $0
    StrCmp $0 1 0 +2
        StrCpy $AllUsers 1
FunctionEnd


Section "Install"
    StrCmp $AllUsers 1 0 +5
        SetShellVarContext all
        SetOutPath "$ProgramFiles64\${APPNAME}"
        WriteRegStr HKLM "Software\VisualStimulusKitTool" "Install_Dir" "$ProgramFiles64\${APPNAME}"
        Goto +4
    SetShellVarContext current
    SetOutPath "$LocalAppData\Programs\${APPNAME}"
    WriteRegStr HKCU "Software\VisualStimulusKitTool" "Install_Dir" "$LocalAppData\Programs\${APPNAME}"
    File "..\dist\Visual Stimulus Kit Tool.exe"
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\Visual Stimulus Kit Tool.exe"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Visual Stimulus Kit Tool.exe"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"
    RMDir /r "$INSTDIR"
SectionEnd
