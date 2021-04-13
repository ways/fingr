"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='fingr',
    version='1',
    description='Finger server, serving weather forecast based on location input',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/ways/fingr',

    author='Lars Falk-Petersen',
    author_email='dev@falkp.no',

    license='GPLv3+',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: System Administrators',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        # Specify the Python versions you support here.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        "Topic :: System :: Networking",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: Internet :: Finger",
    ],
    keywords='finger weather',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[''],
    python_requires='>=3.8',
    test_suite = 'tests',
)

