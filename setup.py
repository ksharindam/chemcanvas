from setuptools import setup
from wheel.bdist_wheel import bdist_wheel
#from setuptools.command.bdist_wheel import bdist_wheel
from subprocess import check_call
import platform

# allows to run commands before building wheel
class BdistWheel(bdist_wheel):
    def finalize_options(self):
        check_call("pyrcc5 -o ./chemcanvas/resources_rc.py ./data/resources.qrc".split())
        check_call("pyuic5 -o ./chemcanvas/ui_mainwindow.py ./data/mainwindow.ui".split())
        bdist_wheel.finalize_options(self)

def readme():
    with open('README.md') as f:
        return f.read()

if platform.system()=='Linux':
    data_files = [('share/applications', ['data/chemcanvas.desktop']),
                ('share/icons', ['data/chemcanvas.svg'])]
else:
    data_files = []

setup(
    name='chemcanvas',
    #version="0.8.0",
    packages=['chemcanvas'],
    entry_points={
      'gui_scripts': ['chemcanvas=chemcanvas.main:main'],
    },
    data_files = data_files,
    cmdclass = {'bdist_wheel': BdistWheel},
    include_package_data=True,
    zip_safe=False
    )
