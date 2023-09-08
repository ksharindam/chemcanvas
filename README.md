# ChemCanvas

The best opensource 2D chemical drawing tool.  

It is under active development.


### Description

This is targeted to be the most intuitive opensource 2D chemical drawing tool.  
You can draw organic chemical structures and reactions very easily and quickly.  


### Features
* read and write support for SMILES format  
* In future more chemical file formats will be supported  
* Save to PNG, SVG and Editable SVG  
* Atom, Bond and other objects coloring support  


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
Open terminal and change to chemcanvas/ directory and run  
`$ ./main.py`  
 
