#!/usr/bin/env python
from __future__ import print_function
import os
import io
import sys


p_logos = [""" 
 ___  ____ _    _   _ ___  _  _ ____ _  _ _  _ ____ 
 |__] |  | |     \_/  |__] |__| |___ |\/| |  | [__  
 |    |__| |___   |   |    |  | |___ |  | |__| ___] 
                                                   
                     _......._
                 .-'.'.'.'.'.'.`-.
               .'.'.'.'.'.'.'.'.'.`.
              /.'.'               '.\  
              |.'    _.--...--._     |
              \    `._.-.....-._.'   /
              |     _..- .-. -.._   |
           .-.'    `.   ((@))  .'   '.-.
          ( ^ \      `--.   .-'     / ^ )
           \  /         .   .       \  /
           /          .'     '.  .-    \  
          ( _.\    \ (_`-._.-'_)    /._\)
           `-' \   ' .--.          / `-'
               |  / /|_| `-._.'\   |
               |   |       |_| |   /-.._
           _..-\   `.--.______.'  |
                \       .....     |
                 `.  .'      `.  /
                   \           .'
                    `-..___..-`

          One eye makes for shallow bugs.

""",
]


sys.path.insert(0, '')
import polyphemus.version
sys.path.pop(0)

INFO = {
    'version': polyphemus.version.polyphemus_version,
}

dir_name = os.path.dirname(os.path.abspath(__file__))
fname = os.path.join(dir_name, 'docs', 'index.rst')
with io.open(fname, 'r') as f:
    long_desc = f.read()

long_desc = "\n".join([l for l in long_desc.splitlines() if ":ref:" not in l])
long_desc = "\n".join([l for l in long_desc.splitlines()
                       if ".. toctree::" not in l])
long_desc = "\n".join([l for l in long_desc.splitlines()
                       if ":maxdepth:" not in l])

def setup():
    try:
        from setuptools import setup as setup_
        have_setuptools = True
    except ImportError:
        from distutils.core import setup as setup_
        have_setuptools = False

    scripts_dir = os.path.join(dir_name, 'scripts')
    scripts_dir = 'scripts'
    if os.name == 'nt':
        scripts = [os.path.join(scripts_dir, f)
                   for f in os.listdir(scripts_dir)]
    else:
        scripts = [os.path.join(scripts_dir, f)
                   for f in os.listdir(scripts_dir)
                   if not f.endswith('.bat')]
    packages = ['polyphemus']
    pack_dir = {'polyphemus': 'polyphemus',}
    pack_data = {'polyphemus': ['templates/*.html'],}
    setup_kwargs = {
        "name": "polyphemus",
        "version": INFO['version'],
        "description": 'polyphemus',
        "author": 'Anthony Scopatz',
        "author_email": 'scopatz@gmail.com',
        "url": 'http://polyphemus.org/',
        "packages": packages,
        "package_dir": pack_dir,
        "package_data": pack_data,
        "scripts": scripts,
        "description": "A BaTLaB itegration service for repo hosting sites "
                       "like GitHub.",
        "long_description": long_desc,
        "download_url": ("https://github.com/polyphemus-ci/polyphemus/"
            "zipball/{0}.{1}").format(*polyphemus.version.polyphemus_version_info[:2]),
        "classifiers": [
            "License :: OSI Approved :: BSD License",
            "Intended Audience :: Developers",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 3",
            "Topic :: Utilities",
            "Topic :: Software Development :: Build Tools",
            "Topic :: Software Development :: Quality Assurance",
            "Topic :: Software Development :: Testing", 
            ],
        "data_files": [("", ['license']),],
        "zip_safe": False,
        #"include_package_data": True,
        }
    if have_setuptools:
        setup_kwargs['install_requires'] = [
            'Flask >= 0.10.1',
            'paramiko >= 1.10.0',
            'github3.py >= 0.7.1',
            ]
    # changing dirs for virtualenv
    cwd = os.getcwd()
    os.chdir(dir_name)
    setup_(**setup_kwargs)
    os.chdir(cwd)

def main_body():
    print(p_logos[0])
    setup()

def final_message(success=True):
    if success:
        return
    msg = "\n\nCURRENT INFO:\n"
    for k, v in sorted(INFO.items()):
        msg += "  {0} = {1}\n".format(k, repr(v))
    print(msg)

def main():
    success = False
    try:
        main_body()
        success = True
    finally:
        final_message(success)

if __name__ == "__main__":
    main()
