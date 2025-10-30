; HM NIS Edit Wizard helper defines
!define PROG_NAME "ChemCanvas"
!define PROG_VERSION "0.10.0"
!define PROG_PUBLISHER "Arindamsoft"
!define PROG_ICON "chemcanvas.ico"
!define PROG_EXEC "chemcanvas.exe"

!define PRODUCT_DIR_REGKEY "Software\${PROG_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROG_NAME}"


Name "${PROG_NAME}"
OutFile "${PROG_NAME}.exe"
; InstallDir must not have space
InstallDir "$PROGRAMFILES64\${PROG_NAME}"
; Get previous install directory if already installed
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
SetCompressor lzma

; Required Plugins
!include "FileAssociation.nsh"

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\data\${PROG_ICON}"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; MUI pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipDirectoryPage
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PROG_EXEC}"
!insertmacro MUI_PAGE_FINISH

; Skip choosing directory when updating older version
Function SkipDirectoryPage
  ReadRegStr $0 HKLM "${PRODUCT_DIR_REGKEY}" ""
  ${IF} $0 != ""
    Abort
  ${EndIf}
FunctionEnd

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES
; Language files
!insertmacro MUI_LANGUAGE "English"
; MUI end ------

; This shows version info in installer, VIFileVersion and VIProductVersion must be in x.x.x.x format
VIProductVersion "${PROG_VERSION}.0"
VIFileVersion "${PROG_VERSION}.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "ChemCanvas"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "Chemical Drawing Tool"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "Arindamsoft"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${PROG_VERSION}.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "Arindam Chaudhuri <arindamsoft94@gmail.com>"


!define BUILDDIR      "dist\chemcanvas"
!define QTBIN_DIR     "dist\chemcanvas\_internal\PyQt5\Qt5\bin"
!define QTPLUGINS_DIR "dist\chemcanvas\_internal\PyQt5\Qt5\plugins"

Section "MainSection" SEC01
  ; Delete files from previous version
  RMDir /r "$INSTDIR\_internal"
  
  ; Install this version
  SetOutPath "$INSTDIR"
  SetOverwrite try
  ;File /r /x "bin" /x "plugins" "${BUILDDIR}\_internal"
  File /r /x "Qt5" "${BUILDDIR}\_internal"
  ; Install Qt5 libraries
  SetOutPath "$INSTDIR\_internal\PyQt5\Qt5\bin"
  File "${QTBIN_DIR}\MSVCP140.dll"
  File "${QTBIN_DIR}\MSVCP140_1.dll"
  File "${QTBIN_DIR}\VCRUNTIME140.dll"
  File "${QTBIN_DIR}\VCRUNTIME140_1.dll"
  File "${QTBIN_DIR}\Qt5Core.dll"
  File "${QTBIN_DIR}\Qt5Gui.dll"
  File "${QTBIN_DIR}\Qt5Widgets.dll"
  ; Install Qt5 plugins
  SetOutPath "$INSTDIR\_internal\PyQt5\Qt5\plugins\platforms"
  File "${QTPLUGINS_DIR}\platforms\qwindows.dll"
  SetOutPath "$INSTDIR\_internal\PyQt5\Qt5\plugins\styles"
  File "${QTPLUGINS_DIR}\styles\qwindowsvistastyle.dll"
  ; Install program and icon
  SetOutPath "$INSTDIR"
  File "${BUILDDIR}\chemcanvas.exe"
  File "${MUI_ICON}"
  ; Install shortcuts
  CreateShortCut "$SMPROGRAMS\${PROG_NAME}.lnk" "$INSTDIR\${PROG_EXEC}" "" "$INSTDIR\${PROG_ICON}"
  CreateShortCut "$DESKTOP\${PROG_NAME}.lnk" "$INSTDIR\${PROG_EXEC}" "" "$INSTDIR\${PROG_ICON}"
  ; Associate File Types
  ${registerExtension} "$INSTDIR\${PROG_EXEC}" ".ccdx" "ChemCanvas Drawing XML"
  ${registerExtension} "$INSTDIR\${PROG_EXEC}" ".mol" "MDL Molfile"
  ${registerExtension} "$INSTDIR\${PROG_EXEC}" ".sdf" "MDL SDfile"
  ${registerExtension} "$INSTDIR\${PROG_EXEC}" ".mrv" "Marvin Document"
  ${registerExtension} "$INSTDIR\${PROG_EXEC}" ".cdxml" "ChemDraw XML"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${PROG_EXEC}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PROG_ICON}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PROG_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PROG_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
SectionEnd


Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Do you really want to completely remove $(^Name)?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  ; Must remove uninstaller first
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\chemcanvas.exe"
  RMDir /r "$INSTDIR\_internal"
  ; Delete icon and shortcuts
  Delete "$DESKTOP\${PROG_NAME}.lnk"
  Delete "$SMPROGRAMS\${PROG_NAME}.lnk"
  Delete "$INSTDIR\${PROG_ICON}"

  RMDir "$INSTDIR"
  ; Unassociate File Types
  ${unregisterExtension} ".ccdx" "ChemCanvas Drawing XML"
  ${unregisterExtension} ".mol" "MDL Molfile"
  ${unregisterExtension} ".sdf" "Marvin Document"
  ${unregisterExtension} ".mrv" "Marvin Document"
  ${unregisterExtension} ".cdxml" "ChemDraw XML"

  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd
