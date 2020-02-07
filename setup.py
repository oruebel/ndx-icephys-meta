# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages
from shutil import copy2

try:
    with open('README.rst', 'r') as fp:
        readme = fp.read()
except:
    readme = ""

setup_args = {
    'name': 'ndx-icephys-meta',
    'version': '0.1.0',
    'description': 'Implement proposal for hierarchical metadata structure for intracellular electrophysiology data ',
    'long_description': readme,
    'long_description_content_type': 'text/x-rst; charset=UTF-8',
    'author': ' Oliver Ruebel, Ryan Ly, Benjamin Dichter, Thomas Braun, Andrew Tritt',
    'author_email': 'oruebel@lbl.gov',
    'url': '',
    'license': 'BSD 3-Clause',
    'install_requires': [
        'pynwb'
    ],
    'packages': find_packages('src/pynwb'),
    'package_dir': {'': 'src/pynwb'},
    'package_data': {'ndx_icephys_meta': [
        'spec/ndx-icephys-meta.namespace.yaml',
        'spec/ndx-icephys-meta.extensions.yaml',
    ]},
    'classifiers': [
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
    ],
    'zip_safe': False
}


def _copy_spec_files(project_dir):
    ns_path = os.path.join(project_dir, 'spec', 'ndx-icephys-meta.namespace.yaml')
    ext_path = os.path.join(project_dir, 'spec', 'ndx-icephys-meta.extensions.yaml')

    dst_dir = os.path.join(project_dir, 'src', 'pynwb', 'ndx_icephys_meta', 'spec')
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)

    copy2(ns_path, dst_dir)
    copy2(ext_path, dst_dir)


if __name__ == '__main__':
    _copy_spec_files(os.path.dirname(__file__))
    setup(**setup_args)
