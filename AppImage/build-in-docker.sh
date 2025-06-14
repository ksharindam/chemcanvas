#! /bin/bash

set -euxo pipefail

image=ubuntu:20.04

case "$ARCH" in
    x86_64)
        platform=linux/amd64
        ;;
    armhf)
        platform=linux/arm/v7
        ;;
    aarch64)
        platform=linux/arm64/v8
        ;;
    *)
        echo "unknown architecture: $ARCH"
        exit 2
        ;;
esac


repo_root="$(readlink -f "$(dirname "${BASH_SOURCE[0]}")"/..)"

# run the build with the current user to
#   a) make sure root is not required for builds
#   b) allow the build scripts to "mv" the binaries into the /out directory
uid="$(id -u)"

# make sure Docker image is up to date
#docker pull "$image"

docker run \
    --platform "$platform" \
    --rm \
    -i \
    -e ARCH \
    -e OUT_UID="$uid" \
    -v "$repo_root":/source \
    -v "$PWD":/out \
    -w /out \
    "$image" \
    sh <<\EOF

set -eux

apt update
# prevent tzdata from asking timezone during install
DEBIAN_FRONTEND=noninteractive TZ="Asia/Kolkata" apt install -y tzdata
apt install -y python3-pyqt5 pyqt5-dev-tools python3 python3-pip wget file

# pyinstaller from PyPi does not ship with armhf bootloader
wget -q "https://github.com/ksharindam/chemcanvas-data/releases/download/continuous/pyinstaller-6.14.1-py3-none-any.whl"
pip3 install ./pyinstaller*.whl

wget -q "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
wget -q "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage"


chmod 755 *.AppImage
mv appimagetool*AppImage /usr/bin/appimagetool
mv linuxdeploy*AppImage /usr/bin/linuxdeploy

bash -eux /source/AppImage/appimage_gen.sh

chown "$OUT_UID" ChemCanvas*.AppImage

EOF
