from setuptools import setup
from setuptools.command.install import install
try:
    from setuptools.command.bdist_wheel import bdist_wheel
except:
    from wheel.bdist_wheel import bdist_wheel
from shutil import which
from subprocess import check_call
import platform


def prepare_install():
    """ preinstall codes to run"""
    if which("pyuic6"):
        check_call("pyuic6 -o ./chemcanvas/ui_mainwindow.py ./data/mainwindow.ui".split())
    else:
        check_call("pyuic5 -o ./chemcanvas/ui_mainwindow.py ./data/mainwindow.ui".split())

# allows to run commands before 'setup.py install' (used by dh-python)
class Install(install):
    def run(self):
        prepare_install()
        install.run(self)

# allows to run commands before building wheel
class BdistWheel(bdist_wheel):
    def finalize_options(self):
        prepare_install()
        bdist_wheel.finalize_options(self)


if platform.system()=='Linux':
    data_files = [('share/applications', ['data/chemcanvas.desktop']),
                ('share/icons/hicolor/scalable/apps', ['data/chemcanvas.svg']),
                ('share/mime/packages', ['data/chemcanvas-mime.xml'])]
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
    cmdclass = {'bdist_wheel': BdistWheel, 'install': Install},
    include_package_data=True,
    zip_safe=False
    )
