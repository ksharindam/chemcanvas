#!/bin/bash

check_dep()
{
  DEP=$1
  if [ -z $(which $DEP) ] ; then
    echo "Error : $DEP command not found"
    exit 1
  fi
}

check_dep appimagetool
check_dep linuxdeploy
check_dep pyuic5
check_dep pyinstaller


#MULTIARCH=`gcc -dumpmachine`

# enables running from different directory
AppDirParent="$(readlink -f "$(dirname "$0")")"
cd "$AppDirParent"

# generate resource and ui files
pyrcc5 -o ../chemcanvas/resources_rc.py ../data/resources.qrc
pyuic5 -o ../chemcanvas/ui_mainwindow.py ../data/mainwindow.ui
# run pyinstaller
pyinstaller ../Windows/chemcanvas.spec
rm -r build


mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/lib
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps
mkdir -p AppDir/usr/share/metainfo

cd AppDir

APPDIR=`pwd`

# copy executable and desktop file
cp ../../data/chemcanvas.desktop usr/share/applications/io.github.ksharindam.chemcanvas.desktop
cp ../../data/io.github.ksharindam.chemcanvas.metainfo.xml usr/share/metainfo
cp ../AppRun .
sed -i -e 's\^BIN=.*\BIN="usr/lib/chemcanvas/chemcanvas"\g' AppRun

# copy pyinstaller generated files
cp -r ../dist/chemcanvas usr/lib
# remove excess library files
rm -r usr/lib/chemcanvas/_internal/lib*.so.*
rm -r usr/lib/chemcanvas/_internal/PyQt5/Qt/plugins/*
rm -r usr/lib/chemcanvas/_internal/PyQt5/Qt/translations
# copy some required files we deleted earlier
#cp ../dist/chemcanvas/_internal/libpython* usr/lib/chemcanvas/_internal
# ------- copy Qt5 Plugins ---------
QT_PLUGIN_PATH=${APPDIR}/usr/lib/chemcanvas/_internal/PyQt5/Qt/plugins
QT_PLUGIN_SRC=${APPDIR}/../dist/chemcanvas/_internal/PyQt5/Qt/plugins
# this is most necessary plugin for x11 support. without it application won't launch
mkdir -p ${QT_PLUGIN_PATH}/platforms
cp ${QT_PLUGIN_SRC}/platforms/libqxcb.so ${QT_PLUGIN_PATH}/platforms

# Wayland support
#cp ${QT_PLUGIN_SRC}/platforms/libqwayland-generic.so ${QT_PLUGIN_PATH}/platforms
#cp -r ${QT_PLUGIN_SRC}/wayland-shell-integration ${QT_PLUGIN_PATH}
#cp -r ${QT_PLUGIN_SRC}/wayland-graphics-integration-client ${QT_PLUGIN_PATH}

# using Fusion theme does not require bundling any style plugin


# ----- End of Copy Qt5 Plugins ------

#cp /usr/lib/${MULTIARCH}/libssl.so.1.0.2 usr/lib
#cp /usr/lib/${MULTIARCH}/libcrypto.so.1.0.2 usr/lib

# cleanup
rm -r ${APPDIR}/../dist

# Deploy dependencies (--appimage-extract-and-run option is for docker)
linuxdeploy --appimage-extract-and-run --appdir .  --icon-file=../../data/chemcanvas.svg

# compile python bytecodes
#find usr/lib -iname '*.py' -exec python3 -m py_compile {} \;

# dump build info
#lsb_release -a > usr/share/BUILD_INFO
#ldd --version | grep GLIBC >> usr/share/BUILD_INFO
#python3 --version >> usr/share/BUILD_INFO

cd ..

# fixes firejail permission issue
chmod -R 0755 AppDir


#if [ "$MULTIARCH" = "x86_64-linux-gnu" ]; then
#    appimagetool -u "zsync|https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas-x86_64.AppImage.zsync" AppDir
appimagetool --appimage-extract-and-run AppDir

