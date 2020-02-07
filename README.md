# ndx-icephys-meta Extension for NWB:N

This extension implements the icephys extension proposal described [here](https://docs.google.com/document/d/1cAgsXv26BmQoVfa7Greyxs0oc4IGH-t5aJsm-AwUAAE/edit). The extension is intended to evaluate and explore the practical use of the proposed changes as well as to provide a reference implementation with the goal to ease integration of the proposed changes with NWB.

## Install

```
python setup.py develop
```

The extension is now also available on pip and can be installed via:

```
pip install ndx-icephys-meta
```

## Examples

Examples for the Python extension are available at ``src/pynwb/examples``. The unit tests in ``src/pynwb/ndx_icephys_meta/test`` can serve as additional examples.

## Building the spec documentation

```
cd docs
make html
```

This generates the specification docs directly from the YAML specifciation in the ``spec`` folder. The generated docs are stored in ``/docs/build``

## Running the unit tests

```
python src/pynwb/ndx_icephys_meta/test/test_icephys.py
```

## Content

* ``spec/`` : YAML specification of the extension
* ``docs/`` : Sources for building the specification docs from the YAML spec
* ``src/spec/create_extension_spec.py`` : Python source file for creating the specification
* ``src/pynwb/`` : Sources for Python extensions and examples
    * ``ndx_icephys_meta`` : Python package with extensions to PyNWB for read/write of extension data
    * ``ndx_icephys_meta/test`` : Unit test for the Python extension
    * ``ndx_icephys_meta/icephys.py`` : PyNWB Container classes
    * ``ndx_icephys_meta/io/icephys.py`` : PyNWB ObjectMapper classes
    * ``examples`` : Examples illustrating the use of the extension in Python
    
## Making a release on PyPi

```
python setup.py sdist bdist_wheel
twine upload dist/*
```
