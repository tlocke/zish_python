====
Zish
====

A Python library for the `Zish format <https://github.com/tlocke/zish>`_, released under
the `MIT-0 licence <https://choosealicense.com/licenses/mit-0/>`_.

.. image:: https://github.com/tlocke/zish_python/workflows/zish_python/badge.svg
   :alt: Build Status

.. contents:: Table of Contents
   :depth: 2
   :local:

Installation
------------

- Create a virtual environment: ``python3 -m venv venv``
- Activate the virtual environment: ``source venv/bin/activate``
- Install: ``pip install zish``


Quickstart
----------

To go from a Python object to an Zish string use ``zish.dumps``. To go from a Zish
string to a Python object use ``zish.loads``. Eg.

>>> from zish import loads, dumps
>>> from datetime import datetime, timezone
>>> from decimal import Decimal
>>>
>>> # Take a Python object
>>> book = {
...     'title': 'A Hero of Our Time',
...     'read_date': datetime(2017, 7, 16, 14, 5, tzinfo=timezone.utc),
...     'would_recommend': True,
...     'description': None,
...     'number_of_novellas': 5,
...     'price': Decimal('7.99'),
...     'weight': 6.88,
...     'key': b'kshhgrl',
...     'tags': ['russian', 'novel', '19th century']}
>>>
>>> # Output it as an Zish string
>>> zish_str = dumps(book)
>>> print(zish_str)
{
  "description": null,
  "key": 'a3NoaGdybA==',
  "number_of_novellas": 5,
  "price": 7.99,
  "read_date": 2017-07-16T14:05:00Z,
  "tags": [
    "russian",
    "novel",
    "19th century",
  ],
  "title": "A Hero of Our Time",
  "weight": 6.88,
  "would_recommend": true,
}
>>>
>>> # Load the Zish string, to give us back the Python object
>>> reloaded_book = loads(zish_str)
>>> 
>>> # Print the title
>>> print(reloaded_book['title'])
A Hero of Our Time

.. table:: Python To Zish Type Mapping

   +-----------------------+-----------------------------------------------------------+
   | Python Type           | Zish Type                                                 |
   +=======================+===========================================================+
   | bool                  | bool                                                      |
   +-----------------------+-----------------------------------------------------------+
   | int                   | integer                                                   |
   +-----------------------+-----------------------------------------------------------+
   | str                   | string                                                    |
   +-----------------------+-----------------------------------------------------------+
   | datetime.datetime     | timestamp                                                 |
   +-----------------------+-----------------------------------------------------------+
   | dict                  | map                                                       |
   +-----------------------+-----------------------------------------------------------+
   | decimal.Decimal       | decimal                                                   |
   +-----------------------+-----------------------------------------------------------+
   | float                 | decimal                                                   |
   +-----------------------+-----------------------------------------------------------+
   | bytearray             | bytes                                                     |
   +-----------------------+-----------------------------------------------------------+
   | bytes                 | bytes                                                     |
   +-----------------------+-----------------------------------------------------------+
   | list                  | list                                                      |
   +-----------------------+-----------------------------------------------------------+
   | tuple                 | list                                                      |
   +-----------------------+-----------------------------------------------------------+


Running The Tests
-----------------

- Change to the ``zish`` directory: ``cd zish``
- Create a virtual environment: ``python3 -m venv venv``
- Activate the virtual environment: ``source venv/bin/activate``
- Install tox: ``pip install tox``
- Run tox: ``tox``


README.rst
----------

This file is written in the `reStructuredText
<https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_ format. To generate an
HTML page from it, do:

- Activate the virtual environment: ``source venv/bin/activate``
- Install ``Sphinx``: ``pip install Sphinx``
- Run ``rst2html.py``: ``rst2html.py README.rst README.html``


Making A New Release
--------------------

Run ``tox`` to make sure all tests pass, then update the 'Release Notes' section then
do::

  git tag -a x.y.z -m "version x.y.z"
  rm -r dist
  python -m build
  twine upload --sign dist/*


Release Notes
-------------

Version 0.1.11 (2023-10-09)
```````````````````````````

- Fix bug where ``dump()`` didn't escape ``"`` and ``\\`` properly.

- Remove support for Python 3.7 and add support for Python 3.11.


Version 0.1.10 (2022-10-29)
```````````````````````````

- Switch to MIT-0 licence.

- Make the U+00A0 NO-BREAK SPACE character whitespace

- Better error message when ``dump()`` encounters an unrecognised type.


Version 0.1.9 (2021-04-05)
``````````````````````````

- Allow trailing commas in maps and lists.


Version 0.1.8 (2020-06-25)
``````````````````````````

- Make `dumps` sort the `set` type before outputing as a list.


Version 0.1.7 (2020-02-11)
``````````````````````````

- Use 1-based line and character numbers, rather than zero-based.

- Arrow time library upgraded.

- Line and character numbers now available in errors


Version 0.1.6 (2018-11-12)
``````````````````````````

- Better error message when parsing an empty string.


Version 0.1.5 (2018-10-30)
``````````````````````````

- Fix new Flake8 errors.


Version 0.1.4 (2018-10-30)
``````````````````````````

- Better error message if there's a duplicate key in a map.


Version 0.1.3 (2018-10-30)
``````````````````````````

- An exception is thrown if there's a duplicate key in a map.


Version 0.1.2 (2018-09-04)
``````````````````````````

- Change formatting for map and list in dumps. The trailing } and ] are now on a line
  down and at the original index.


Version 0.1.1 (2018-03-13)
``````````````````````````

- A decimal with an uppercase 'E' in the exponent wasn't being recognized.


Version 0.1.0 (2018-01-29)
``````````````````````````

- A map key can't be null, following change in spec.


Version 0.0.26 (2018-01-29)
```````````````````````````

- Remove '//' as a comment, following change in spec.

- Allow 'e' and 'E' in the exponent of a decimal, following change in spec.


Version 0.0.25 (2018-01-12)
```````````````````````````

- Better error message when the end of the document is reached without a map being
  closed.


Version 0.0.24 (2018-01-11)
```````````````````````````

- Fix bug where an integer after a value (and before a ',' or '}') in a map doesn't
  give a good error.


Version 0.0.23 (2018-01-09)
```````````````````````````

- A map key can't now be a list or a map.


Version 0.0.22 (2018-01-08)
```````````````````````````

- A map key can now be of any type.

- The 'set' type has been removed from Zish.

- Zish now recognizes the full set of Unicode EOL sequences.

- The 'float' type has been removed from Zish.

- Fixed bug when sorting map with keys of more than one type.


Version 0.0.21 (2018-01-04)
```````````````````````````

- Give a better error if the end of the document is reached before a map is completed.


Version 0.0.20 (2018-01-04)
```````````````````````````

- Give an error if there are multiple top-level values, rather than silently truncating.


Version 0.0.19 (2017-09-27)
```````````````````````````

- Decimal exponent dumped as ``E`` rather than ``d``.


Version 0.0.18 (2017-09-12)
```````````````````````````

- Add tests for float formatting.


Version 0.0.17 (2017-09-12)
```````````````````````````

- Tighten up parsing of container types.
- Make sure floats are formatted without an uppercase E.


Version 0.0.16 (2017-09-06)
```````````````````````````

- Allow lists and sets as keys.


Version 0.0.15 (2017-09-05)
```````````````````````````

- Fixed map parsing bug where an error wasn't reported properly if it was expecting a
  ``:`` but got an integer.


Version 0.0.14 (2017-09-05)
```````````````````````````

- Fixed bug where sets couldn't be formatted.


Version 0.0.13 (2017-08-30)
```````````````````````````

- Performance improvement.


Version 0.0.12 (2017-08-30)
```````````````````````````

- Add Travis configuration.


Version 0.0.11 (2017-08-30)
```````````````````````````

- Give a better error message if a string isn't closed.


Version 0.0.10 (2017-08-29)
```````````````````````````

- New native parser that doesn't use antlr. It's about twice as fast.


Version 0.0.9 (2017-08-24)
``````````````````````````

- Fix bug where ``int`` was being parsed as ``Decimal``.
- Make bytes type return a ``bytes`` rather than a ``bytearray``.


Version 0.0.8 (2017-08-24)
``````````````````````````

- Container types aren't allowed as map keys.

- Performance improvements.


Version 0.0.7 (2017-08-22)
``````````````````````````

- Fix bug with UTC timestamp formatting.


Version 0.0.6 (2017-08-22)
``````````````````````````

- Fix bug in timestamp formatting.

- Add note about comments.


Version 0.0.5 (2017-08-18)
``````````````````````````

- Fix bug where ``dumps`` fails for a ``tuple``.


Version 0.0.4 (2017-08-15)
``````````````````````````

- Simplify integer types.


Version 0.0.3 (2017-08-09)
``````````````````````````

- Fixed bug where interpreter couldn't find the ``zish.antlr`` package in eggs.

- Removed a few superfluous escape sequences.


Version 0.0.2 (2017-08-05)
``````````````````````````

- Now uses RFC3339 for timestamps.


Version 0.0.1 (2017-08-03)
``````````````````````````

- Fix bug where an EOF could cause an infinite loop.


Version 0.0.0 (2017-08-01)
``````````````````````````

- First public release. Passes all the tests.
