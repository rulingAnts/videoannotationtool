; NSIS script for Visual Stimulus Kit Tool Windows installer
;
; Source: the ONEDIR PyInstaller build (dist_onedir\Visual Stimulus Kit Tool\).
; An installed app has no reason to pay the onefile self-extraction cost on
; every launch, so the installer ships the one-folder bundle (launcher .exe
; plus its _internal folder) and installs it as-is.
;
; Build with:  makensis /DVERSION=2.3.3 installer\videoannotation_installer.nsi
; (run PyInstaller with pyinstaller-onedir.spec --distpath dist_onedir first)

!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define APPNAME "Visual Stimulus Kit Tool"
!define COMPANY "Seth Johnston"
!define REGKEY "Software\VisualStimulusKitTool"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\VisualStimulusKitTool"

; VERSION can be overridden from the command line: makensis /DVERSION=2.3.3
!ifndef VERSION
!define VERSION "0.0.0"
!endif

Name "${APPNAME}"
OutFile "Visual-Stimulus-Kit-Tool-${VERSION}-setup.exe"

; "highest" lets an admin install for all users while still allowing a
; standard user to install just for themselves without elevation.
RequestExecutionLevel highest

; Default to a per-user location; the scope page overrides $INSTDIR to match
; the user's choice before the directory page is shown.
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
InstallDirRegKey HKCU "${REGKEY}" "Install_Dir"

Var AllUsers
Var Dialog
Var RadioAll
Var RadioUser

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "${COMPANY}"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2025 ${COMPANY}"
VIAddVersionKey "FileDescription" "${APPNAME} Installer"

Page custom SelectInstallScope SelectInstallScopeLeave
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

; Writes the "Installed Apps" (Add/Remove Programs) entry into the given hive.
!macro WriteUninstallInfo HIVE
    WriteRegStr ${HIVE} "${UNINSTKEY}" "DisplayName" "${APPNAME}"
    WriteRegStr ${HIVE} "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
    WriteRegStr ${HIVE} "${UNINSTKEY}" "Publisher" "${COMPANY}"
    WriteRegStr ${HIVE} "${UNINSTKEY}" "DisplayIcon" "$\"$INSTDIR\${APPNAME}.exe$\""
    WriteRegStr ${HIVE} "${UNINSTKEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr ${HIVE} "${UNINSTKEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
    WriteRegStr ${HIVE} "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD ${HIVE} "${UNINSTKEY}" "NoModify" 1
    WriteRegDWORD ${HIVE} "${UNINSTKEY}" "NoRepair" 1
    WriteRegDWORD ${HIVE} "${UNINSTKEY}" "EstimatedSize" $0
!macroend

Function .onInit
    StrCpy $AllUsers 0
FunctionEnd

Function SelectInstallScope
    nsDialogs::Create 1018
    Pop $Dialog
    ${If} $Dialog == error
        Abort
    ${EndIf}
    ${NSD_CreateRadioButton} 10 10 90% 12u "Install for anyone using this computer (requires admin)"
    Pop $RadioAll
    ${NSD_CreateRadioButton} 10 30 90% 12u "Install just for me (no admin required)"
    Pop $RadioUser
    ${NSD_SetState} $RadioUser 1
    nsDialogs::Show
FunctionEnd

Function SelectInstallScopeLeave
    ${NSD_GetState} $RadioAll $0
    ${If} $0 == 1
        ; All-users install needs admin; fall back to per-user if we don't have it.
        UserInfo::GetAccountType
        Pop $1
        ${If} $1 != "Admin"
            MessageBox MB_OK|MB_ICONINFORMATION "Administrator rights are required to install for all users.$\r$\nInstalling just for you instead."
            StrCpy $AllUsers 0
        ${Else}
            StrCpy $AllUsers 1
        ${EndIf}
    ${Else}
        StrCpy $AllUsers 0
    ${EndIf}

    ; Keep $INSTDIR, the shell context and the install target consistent.
    ${If} $AllUsers == 1
        SetShellVarContext all
        StrCpy $INSTDIR "$PROGRAMFILES64\${APPNAME}"
    ${Else}
        SetShellVarContext current
        StrCpy $INSTDIR "$LOCALAPPDATA\Programs\${APPNAME}"
    ${EndIf}
FunctionEnd

Section "Install"
    SetOutPath "$INSTDIR"
    ; Onedir bundle: the launcher .exe plus its _internal folder.
    File /r "..\dist_onedir\${APPNAME}\*.*"

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Size reported in Add/Remove Programs (KB).
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2

    ${If} $AllUsers == 1
        WriteRegStr HKLM "${REGKEY}" "Install_Dir" "$INSTDIR"
        WriteRegStr HKLM "${REGKEY}" "Scope" "all"
        !insertmacro WriteUninstallInfo HKLM
    ${Else}
        WriteRegStr HKCU "${REGKEY}" "Install_Dir" "$INSTDIR"
        WriteRegStr HKCU "${REGKEY}" "Scope" "user"
        !insertmacro WriteUninstallInfo HKCU
    ${EndIf}

    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPNAME}.exe"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Function un.onInit
    ; Recover the scope the app was installed with so the uninstaller looks in
    ; the right Start Menu and registry hive.
    ReadRegStr $0 HKLM "${REGKEY}" "Scope"
    ${If} $0 == "all"
        StrCpy $AllUsers 1
        SetShellVarContext all
    ${Else}
        StrCpy $AllUsers 0
        SetShellVarContext current
    ${EndIf}
FunctionEnd

Section "Uninstall"
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"

    ; Only remove the tree if it really looks like our install, so a wrong
    ; $INSTDIR can never take an unrelated folder with it.
    ${If} ${FileExists} "$INSTDIR\${APPNAME}.exe"
        Delete "$INSTDIR\Uninstall.exe"
        RMDir /r "$INSTDIR"
    ${Else}
        Delete "$INSTDIR\Uninstall.exe"
        RMDir "$INSTDIR"
    ${EndIf}

    ${If} $AllUsers == 1
        DeleteRegKey HKLM "${UNINSTKEY}"
        DeleteRegKey HKLM "${REGKEY}"
    ${Else}
        DeleteRegKey HKCU "${UNINSTKEY}"
        DeleteRegKey HKCU "${REGKEY}"
    ${EndIf}
SectionEnd
