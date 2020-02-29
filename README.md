# ndx-icephys-meta Extension for NWB:N

This extension implements the icephys extension proposal described [here](https://docs.google.com/document/d/1cAgsXv26BmQoVfa7Greyxs0oc4IGH-t5aJsm-AwUAAE/edit). The extension is intended to evaluate and explore the practical use of the proposed changes as well as to provide a reference implementation with the goal to ease integration of the proposed changes with NWB.

## Install

### pip install

The extension is available on pip and can be installed via:

```
pip install ndx-icephys-meta
```

The extension is also listed in the (NDX catalog)[https://nwb-extensions.github.io/]. See [here](https://github.com/nwb-extensions/ndx-icephys-meta-record) for the catalog metadata record.

### developer install

```
python setup.py develop
```
**NOTE:** The development version requires:
* [NeurodataWithoutBorders/pynwb#1200](https://github.com/NeurodataWithoutBorders/pynwb/pull/1200)
* [hdmf-dev/hdmf#301](https://github.com/hdmf-dev/hdmf/pull/301)

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

Examples for the Python extension are available at ``src/pynwb/examples``. The unit tests in ``src/pynwb/ndx_icephys_meta/test`` can also serve as additional examples.

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
electrode = nwbfile.create_icephys_electrode(
    name="elec0",
    description='a mock intracellular electrode',
    device=device)

# Create an ic-ephys stimulus
stimulus = VoltageClampStimulusSeries(
            name="stimulus",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=electrode,
            gain=0.02)

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
            resistance_comp_correction=70.0)

# (A) Add an intracellular recording to the file
#     NOTE: We can optionally define time-ranges for the stimulus/response via
#     the corresponding option _start_index and _index_count parameters.
#     NOTE: It is allowed to add a recording with just a stimulus or a response
#     NOTE: We can  add custom columns to any of our tables in steps (A)-(E)
ir_index = nwbfile.add_intracellular_recording(electrode=electrode,
                                               stimulus=stimulus,
                                               response=response)

# (B) Add a list of sweeps to the sweeps table
sweep_index = nwbfile.add_icephys_simultaneous_recording(recordings=[ir_index, ])

# (C) Add a list of simultaneous recordings table indices as a sequential recording
sequence_index = nwbfile.add_icephys_sequential_recording(
    simultaneous_recordings=[sweep_index, ],
    stimulus_type='square')

# (D) Add a list of sequential recordings table indices as a repetition
run_index = nwbfile.add_icephys_repetition(sequential_recordings=[sequence_index, ])

# (E) Add a list of repetition table indices as a experimental condition
nwbfile.add_icephys_experimental_condition(repetitions=[run_index, ])

# Write our test file
testpath = "test_icephys_file.h5"
with NWBHDF5IO(testpath, 'w') as io:
    io.write(nwbfile)

# Read the data back in
with NWBHDF5IO(testpath, 'r') as io:
    infile = io.read()
    print(infile)
```
