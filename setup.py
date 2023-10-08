from setuptools import setup
import platform
from chemcanvas import __version__, AUTHOR_NAME, AUTHOR_EMAIL

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
    version=__version__,
    description='Most intuitive and powerful opensource 2D chemical drawing tool',
    long_description=readme(),
    long_description_content_type = 'text/markdown',
    keywords='chemistry science drawing cheminformatics',
    url='http://github.com/ksharindam/chemcanvas',
    author=AUTHOR_NAME,
    author_email=AUTHOR_EMAIL,
    license='GNU GPLv3',
    #install_requires=['PyQt5',],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Chemistry',
    ],
    packages=['chemcanvas'],
    entry_points={
      'gui_scripts': ['chemcanvas=chemcanvas.main:main'],
    },
    data_files = data_files,
    include_package_data=True,
    zip_safe=False
    )
