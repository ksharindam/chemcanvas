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


### Features
* read and write support for SMILES format  
* In future more chemical file formats will be supported  
* Save to PNG, SVG and Editable SVG  
* Atom, Bond and other objects coloring support  


### Download
Download the precompiled packages from [releases page](https://github.com/ksharindam/chemcanvas/releases).  
For Windows download .exe package and install it (for Windows 7 and above).  
For Linux download .AppImage package, mark it executable, and double click to run.  

### Installation

If you wan to install using pip, first install these dependencies...  

* python3  
* python3-pyqt5  
* pytqt5-dev-tools  

Then inside data/ dir, exec compile_rc, and compile_ui. The UI files and resource files will be generated.  

Then inside project root directory, run following command..  
`$ sudo pip3 install .`  

To uninstall run..  
`$ sudo pip3 uninstall chemcanvas`    

### Usage

To run after installing, type command..  
`$ chemcanvas`  


If you want to run the program without/before installing, then  
Open terminal and change to project root directory and run  
`$ ./chemcanvas.py`  


### Screenshots

![Screenshot1](data/screenshots/Screenshot1.jpg)  


![Screenshot2](data/screenshots/Screenshot2.jpg)  


![Screenshot3](data/screenshots/Screenshot3.jpg)  

