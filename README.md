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


## Example

The following shows a simple example. The steps with (A) - (E) in the comments are the main new steps for this extension. The other parts of the code are standard NWB code.

```python
from datetime import datetime
from dateutil.tz import tzlocal
import numpy as np
from pynwb.icephys import VoltageClampStimulusSeries, VoltageClampSeries
from pynwb import NWBHDF5IO
from ndx_icephys_meta.icephys import ICEphysFile  # Import the extension

# Create an ICEphysFile
nwbfile = ICEphysFile(session_description='my first recording',
                      identifier='EXAMPLE_ID',
                      session_start_time=datetime.now(tzlocal()))

# Add a device
device = nwbfile.create_device(name='Heka ITC-1600')

# Add an intracellular electrode
electrode = nwbfile.create_ic_electrode(name="elec0",
                                        description='a mock intracellular electrode',
                                        device=device)

# Create an ic-ephys stimulus
stimulus = VoltageClampStimulusSeries(
            name="stimulus",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=electrode,
            gain=0.02,
            sweep_number=15)

# Create an ic-response
response = VoltageClampSeries(
            name='response',
            data=[0.1, 0.2, 0.3, 0.4, 0.5],
            conversion=1e-12,
            resolution=np.nan,
            starting_time=123.6,
            rate=20e3,
            electrode=electrode,
            gain=0.02,
            capacitance_slow=100e-12,
            resistance_comp_correction=70.0,
            sweep_number=15)

# (A) Add an intracellular recording to the file
nwbfile.add_intracellular_recording(electrode=electrode,
                                    stimulus=stimulus,
                                    response=response)

# (B) Add a list of sweeps to the sweeps table
nwbfile.add_ic_sweep(recordings=[0])

# (C) Add a list of sweep table indices as a sweep sequence
nwbfile.add_ic_sweep_sequence(sweeps=[0])

# (D) Add a list of sweep sequence table indices as a run
nwbfile.add_ic_run(sweep_sequences=[0])

# (E) Add a list of run table indices as a condition
nwbfile.add_ic_condition(runs=[0])

# Write our test file
testpath = "test_icephys_file.h5"
with NWBHDF5IO(testpath, 'w') as io:
    io.write(nwbfile)

# Read the data back in
with NWBHDF5IO(testpath, 'r') as io:
    infile = io.read()
    print(infile)
```
