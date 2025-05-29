![License](https://img.shields.io/github/license/ksharindam/chemcanvas)
![Release](https://img.shields.io/github/v/release/ksharindam/chemcanvas)
![Release Date](https://img.shields.io/github/release-date/ksharindam/chemcanvas)
![Downloads Total](https://img.shields.io/github/downloads/ksharindam/chemcanvas/total)
![Downloads Latest](https://img.shields.io/github/downloads/ksharindam/chemcanvas/latest/total)

# ChemCanvas

The most intuitive opensource 2D chemical drawing tool.  


### Description

This is targeted to be the most intuitive opensource 2D chemical drawing tool.  
You can draw organic chemical structures and reactions very easily and quickly.  

### Download

|      EXE      |     RPiOS     |    AppImage   |    Flatpak    |      Snap     |  
| ------------- | ------------- | ------------- | ------------- | ------------- |  
| ![EXE](https://github.com/ksharindam/chemcanvas-data/raw/main/icons/windows.png) | ![AppImage](https://github.com/ksharindam/chemcanvas-data/raw/main/icons/raspberry-pi.png) | ![AppImage](https://github.com/ksharindam/chemcanvas-data/raw/main/icons/appimage.png)  | ![Flatpak](https://github.com/ksharindam/chemcanvas-data/raw/main/icons/flatpak.png) | ![Snap](https://github.com/ksharindam/chemcanvas-data/raw/main/icons/snap.png) |  
| [Download](https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas.exe) | [Download](https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas-armhf.AppImage) | [Download](https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas-x86_64.AppImage)  | [Download](https://github.com/ksharindam/chemcanvas/releases/latest/download/ChemCanvas.flatpak) | [Download](https://github.com/ksharindam/chemcanvas/releases/latest/download/chemcanvas_0.7.28_amd64.snap) |  

Run the AppImage package by marking it executable, and then double click.  
View changelog in [releases page](https://github.com/ksharindam/chemcanvas/releases).  

To install snap package  
`sudo snap install ./chemcanvas*.snap`  

To install the flatpak package  
`flatpak install ChemCanvas.flatpak`  

Run flatpak with...  
`flatpak run io.github.ksharindam.chemcanvas`  

### Features
* Import from and export to SMILES, MDL Molefile, Marvin Document (MRV), ChemDraw XML (CDXML)  
* In future more chemical file formats will be supported  
* Save to PNG, SVG and Editable SVG  
* Many bond types including wavy bond, Cis/Trans, Bold double, Any Bond etc.  
* Atom, Bond and other objects coloring support  
* Aromaticity detection and add delocalization ring  


### Installation (PIP)

If you want to install using pip, first install these dependencies...  

* python3 (>=3.7)  
* python3-pyqt5  
* pytqt5-dev-tools (to generate ui and resource file)  

Inside project root directory, run following commands..  
`sudo pip3 install .`  

To uninstall run..  
`$ sudo pip3 uninstall chemcanvas`    



### Screenshots

![Screenshot1](https://github.com/ksharindam/chemcanvas-data/raw/main/Screenshots/screenshot1.png)  


![Screenshot2](https://github.com/ksharindam/chemcanvas-data/raw/main/Screenshots/screenshot2.png)  


![Screenshot3](https://github.com/ksharindam/chemcanvas-data/raw/main/Screenshots/screenshot3.png)  

