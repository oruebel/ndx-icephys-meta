# ndx-icephys-meta Extension for NWB:N

## Install

```
python setup.py develop
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

