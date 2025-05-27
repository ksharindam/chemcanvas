#!/bin/bash

check_dep()
{
  DEP=$1
  if [ -z $(which $DEP) ] ; then
    echo "Error : $DEP command not found"
    exit 0
  fi
}

check_dep appimagetool
check_dep linuxdeploy
check_dep gcc

MULTIARCH=`gcc -dumpmachine`
LIBDIR=lib/${MULTIARCH}
PYVERSION="3.7"

mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps
mkdir -p AppDir/usr/share/metainfo

cd AppDir

APPDIR=`pwd`

# copy executable and desktop file
cp ../../data/chemcanvas.desktop usr/share/applications/io.github.ksharindam.chemcanvas.desktop
cp ../../data/io.github.ksharindam.chemcanvas.metainfo.xml usr/share/metainfo
cp ../AppRun .
chmod +x AppRun

# create required directories
mkdir -p ${APPDIR}/usr/lib/python3.7
mkdir -p ${APPDIR}/usr/lib/python3/PyQt5

# copy main program
cp ../../chemcanvas.py usr/bin/chemcanvas
chmod +x usr/bin/chemcanvas
cp -r ../../chemcanvas usr/lib/python3
# copy python3 and python3-stdlib
cp /usr/bin/python3 usr/bin

cd /usr/lib/python3.7
cat ${APPDIR}/../python3.7-stdlib.txt | sed -e "s/x86_64-linux-gnu/${MULTIARCH}/" | xargs -I % cp -r --parents % ${APPDIR}/usr/lib/python3.7

# copy sip module
cd /usr/lib/python3/dist-packages
cp sipconfig*.py sip.cpython*.so sip.pyi ${APPDIR}/usr/lib/python3

# copy PyQt5 module
cd PyQt5
cp Qt.* QtCore.* QtGui.* QtWidgets.* QtPrintSupport.* __init__.py \
   ${APPDIR}/usr/lib/python3/PyQt5

cd $APPDIR

# ------- copy Qt5 Plugins ---------
QT_PLUGIN_PATH=${APPDIR}/usr/lib/qt5/plugins
cd /usr/${LIBDIR}/qt5/plugins/

# this is most necessary plugin for x11 support. without it application won't launch
mkdir -p ${QT_PLUGIN_PATH}/platforms
cp platforms/libqxcb.so ${QT_PLUGIN_PATH}/platforms

# using Fusion theme does not require bundling any style plugin

# for print support in linux
mkdir -p ${QT_PLUGIN_PATH}/printsupport
cp printsupport/libcupsprintersupport.so ${QT_PLUGIN_PATH}/printsupport

cd $APPDIR
# ----- End of Copy Qt5 Plugins ------

#cp /usr/${LIBDIR}/libssl.so.1.0.2 usr/lib
#cp /usr/${LIBDIR}/libcrypto.so.1.0.2 usr/lib


# Deploy dependencies
linuxdeploy --appdir .  --icon-file=../../data/chemcanvas.svg

# compile python bytecodes
find usr/lib -iname '*.py' -exec python3 -m py_compile {} \;

# dump build info
lsb_release -a > usr/share/BUILD_INFO
ldd --version | grep GLIBC >> usr/share/BUILD_INFO

cd ..

# fixes firejail permission issue
chmod -R 0755 AppDir


if [ "$MULTIARCH" = "x86_64-linux-gnu" ]; then
    appimagetool -u "zsync|https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas-x86_64.AppImage.zsync" AppDir
else
    appimagetool AppDir
fi
