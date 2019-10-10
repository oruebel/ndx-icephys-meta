Overview
========

This specification extends the Neurodata Without Borders: Neurophysiology (NWB:N) Specification specifically in regard to intracellular electrophysiology data.

Please refer to the core NWB format specification for context and general guidelines: https://nwb-schema.readthedocs.io/en/latest/


Terminology:
------------

The keywords “MUST”, “MUST NOT”, “REQUIRED”, “SHALL”, “SHALL NOT”, “SHOULD”, “SHOULD NOT”, “RECOMMENDED”, “MAY”, and “OPTIONAL” in this document are to be interpreted as described in RFC2119.

The terminology that will be used includes the following:

* **Stimulus**: (or presentation) A time series representing voltage or current stimulation with a particular set of parameters
* **Response**: (or trace) A time series representing voltage or current recorded from a single cell using a single intracellular electrode
* **Sweep**: A group of stimuli presented and responses recorded simultaneously, possibly using multiple electrodes.
* **Stimulus Type**: (or protocol or template or stimulus template) A group of stimuli that differ by a set of parameters. Can be thought as a parameterized function, e.g. a square function of 1-second current injections of x0 to x1 pA in xstep increments, or a pulsed noise pattern with three pulses of random noise in a fixed timing, a random seed parameter, and a current offset parameter. An instantiation of a stimulus type with a particular set of parameter values is a stimulus.
* **Sweep Sequence**: A set of stimuli that are applied in sequence, often of the same stimulus type. Other groupings of sweeps into sequences are possible as well.
* **Run**: (or stimulus set repetition): A set of stimulus sequences that may be repeated
* **Condition:** An experimental condition that groups multiple repetitions together.


