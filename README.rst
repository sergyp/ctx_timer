Contextual timer
================

The library ctx_timer usefull to duration measure of python code execution.

You can touch this project at github repository <>.

Features:

- use timer as context manager
- use timer as decorator of functions or methods 
- simple usage of timer as separately object with .start() and .stop() methods
- multi laps support
- support of logging or echo to:
  - standard python logging library
  - stdout, stderr, file or other way, that supported stream-like interface
  - nothing - fully silent mode (by default)
- customizable templates of echo messages
- human readable ergonomic string representation
- timer name support
- simple statistic:
  - summary duration
  - total average lap duration
  - total max/min lap duration
  - summary duration of last N laps
  - average duration of last N laps


TODO: Basic usage examples


----

This is the README file for the project.

The file should use UTF-8 encoding and be written using `reStructuredText
<http://docutils.sourceforge.net/rst.html>`_. It
will be used to generate the project webpage on PyPI and will be displayed as
the project homepage on common code-hosting services, and should be written for
that purpose.
