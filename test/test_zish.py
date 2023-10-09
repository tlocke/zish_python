import binascii

from base64 import b64decode
from collections import OrderedDict
from datetime import datetime as Datetime, timedelta as Timedelta, timezone as Timezone
from decimal import Decimal
from io import StringIO

import pytest

from zish import ZishException, ZishLocationException, core, dump, dumps, load, loads


def test_load():
    assert load(StringIO("{}")) == {}


def test_dump():
    f = StringIO()
    dump({}, f)
    assert f.getvalue() == "{}"


# For Python version >= 3.10 there are various differences
try:
    result_excess_data = b64decode(
        "VG8gaW5maW5pdHkuLi4gYW5kIGJleW9uZCE==", validate=True
    )
except binascii.Error:
    result_excess_data = ZishLocationException(1, 42, "Excess data after padding")

try:
    b64decode("VG8gaW5maW5pdHku=Li4gYW5kIGJleW9uZCE=", validate=True)
except binascii.Error as e:
    msg_discontinuous = str(e)

try:
    b64decode("dHdvIHBhZGRpbmc_gY2hhcmFjdGVycw=", validate=True)
except binascii.Error as e:
    msg_only_b64 = str(e)


@pytest.mark.parametrize(
    "zish_str,pyth",
    [
        #
        # Timestamp
        #
        # Error: Seconds are not optional
        (
            "2007-02-23T12:14Z",
            ZishLocationException(
                1, 18, "The timestamp 2007-02-23T12:14Z is not recognized."
            ),
        ),
        # A timestamp with millisecond precision and PST local time
        (
            "2007-02-23T12:14:33.079-08:00",
            Datetime(
                2007, 2, 23, 12, 14, 33, 79000, tzinfo=Timezone(Timedelta(hours=-8))
            ),
        ),
        # The same instant in UTC ("zero" or "zulu")
        (
            "2007-02-23T20:14:33.079Z",
            Datetime(2007, 2, 23, 20, 14, 33, 79000, tzinfo=Timezone.utc),
        ),
        # The same instant, with explicit local offset
        (
            "2007-02-23T20:14:33.079+00:00",
            Datetime(
                2007, 2, 23, 20, 14, 33, 79000, tzinfo=Timezone(Timedelta(hours=0))
            ),
        ),
        # The same instant, with unknown local offset
        (
            "2007-02-23T20:14:33.079-00:00",
            Datetime(
                2007, 2, 23, 20, 14, 33, 79000, tzinfo=Timezone(Timedelta(hours=0))
            ),
        ),
        # Happy New Year in UTC, unknown local offset
        ("2007-01-01T00:00:00-00:00", Datetime(2007, 1, 1, tzinfo=Timezone.utc)),
        # Error: Must have a time
        (
            "2007-01-01",
            ZishLocationException(1, 12, "The value 2007-01-01 is not recognized."),
        ),
        # The same value, different syntax.
        # Shouldn't actually be an error, but arrow says it is.
        (
            "2007-01-01T",
            ZishLocationException(1, 13, "The timestamp 2007-01-01T is malformed."),
        ),
        # The same instant, with months precision, unknown local offset
        # Shouldn't actually be an error, but arrow says it is.
        (
            "2007-01T",
            ZishLocationException(1, 10, "The timestamp 2007-01T is malformed."),
        ),
        # The same instant, with years precision, unknown local offset
        # Shouldn't actually be an error, but arrow says it is.
        ("2007T", ZishLocationException(1, 7, "The timestamp 2007T is malformed.")),
        # Error: Must have a time part
        (
            "2007-02-23",
            ZishLocationException(1, 12, "The value 2007-02-23 is not recognized."),
        ),
        # Error: Must have seconds
        (
            "2007-02-23T00:00Z",
            ZishLocationException(
                1, 18, "The timestamp 2007-02-23T00:00Z is not recognized."
            ),
        ),
        # Error: Must have seconds
        (
            "2007-02-23T00:00+00:00",
            ZishLocationException(
                1, 24, r"The timestamp 2007-02-23T00:00\+00:00 is malformed."
            ),
        ),
        # The same instant, with seconds precision
        ("2007-02-23T00:00:00-00:00", Datetime(2007, 2, 23, tzinfo=Timezone.utc)),
        # Not a timestamp, but an int
        ("2007", 2007),
        # ERROR: Must end with 'T' if not whole-day precision, this results
        # as an invalid-numeric-stopper error
        (
            "2007-01",
            ZishLocationException(1, 9, "The value 2007-01 is not recognized."),
        ),
        # ERROR: Must have at least one digit precision after decimal point.
        (
            "2007-02-23T20:14:33.Z",
            ZishLocationException(
                1, 22, "The timestamp 2007-02-23T20:14:33.Z is not recognized."
            ),
        ),
        #
        # Null Values
        #
        ("null", None),
        #
        # Booleans
        #
        ("true", True),
        ("false", False),
        #
        # Integers
        #
        # Zero.  Surprise!
        ("0", 0),
        # ...the same value with a minus sign
        ("-0", 0),
        # A normal int
        ("123", 123),
        # Another negative int
        ("-123", -123),
        # Error: An int can't be denoted in hexadecimal
        ("0xBeef", ZishLocationException(1, 8, "The value 0xBeef is not recognized.")),
        # Error: An int can't be denoted in binary
        ("0b0101", ZishLocationException(1, 8, "The value 0b0101 is not recognized.")),
        # Error: An int can't have underscores
        ("1_2_3", ZishLocationException(1, 7, "The value 1_2_3 is not recognized.")),
        # Error: An int can't be denoted in hexadecimal with underscores
        (
            "0xFA_CE",
            ZishLocationException(1, 9, "The value 0xFA_CE is not recognized."),
        ),
        # Error: An int can't be denoted in binary with underscores
        (
            "0b10_10_10",
            ZishLocationException(1, 12, "The value 0b10_10_10 is not recognized."),
        ),
        # ERROR: leading plus not allowed
        ("+1", ZishLocationException(1, 4, r"The value \+1 is not recognized.")),
        # ERROR: leading zeros not allowed (no support for octal notation)
        ("0123", ZishLocationException(1, 6, "The value 0123 is not recognized.")),
        # ERROR: trailing underscore not allowed
        ("1_", ZishLocationException(1, 4, "The value 1_ is not recognized.")),
        # ERROR: consecutive underscores not allowed
        ("1__2", ZishLocationException(1, 6, "The value 1__2 is not recognized.")),
        # ERROR: underscore can only appear between digits (the radix prefix is
        # not a digit)
        ("0x_12", ZishLocationException(1, 7, "The value 0x_12 is not recognized.")),
        # ERROR: ints cannot start with underscores
        ("_1", ZishLocationException(1, 4, "The value _1 is not recognized.")),
        #
        # Real Numbers
        #
        # Type is decimal
        ("0.123", Decimal("0.123")),
        # Type is decimal
        ("-0.12e4", Decimal("-0.12e4")),
        # ERROR: Exponent not denoted by 'd'
        ("0d0", ZishLocationException(1, 5, "The value 0d0 is not recognized.")),
        # Zero with uppercase 'E' in exponent.
        ("0E0", Decimal(0)),
        # Zero as decimal
        ("0e0", Decimal("0")),
        # Error: Zero as decimal can't have uppercase 'D' in exponent.
        ("0D0", ZishLocationException(1, 5, "The value 0D0 is not recognized.")),
        #   ...the same value with different notation
        ("0.", Decimal("0")),
        # Negative zero float   (distinct from positive zero)
        ("-0e0", Decimal(-0)),
        # Error: Negative zero decimal with 'd' in expenent.
        ("-0d0", ZishLocationException(1, 6, "The value -0d0 is not recognized.")),
        #   ...the same value with different notation
        ("-0.", Decimal("-0")),
        # Decimal maintains precision: -0. != -0.0
        ("-0e-1", Decimal("-0.0")),
        # Error: Decimal can't have underscores
        (
            "123_456.789_012",
            ZishLocationException(
                1, 17, "The value 123_456.789_012 is not recognized."
            ),
        ),
        # ERROR: underscores may not appear next to the decimal point
        (
            "123_._456",
            ZishLocationException(1, 11, "The value 123_._456 is not recognized."),
        ),
        # ERROR: consecutive underscores not allowed
        (
            "12__34.56",
            ZishLocationException(1, 11, "The value 12__34.56 is not recognized."),
        ),
        # ERROR: trailing underscore not allowed
        (
            "123.456_",
            ZishLocationException(1, 10, "The value 123.456_ is not recognized."),
        ),
        # ERROR: underscore after negative sign not allowed
        (
            "-_123.456",
            ZishLocationException(1, 11, "The value -_123.456 is not recognized."),
        ),
        # ERROR: the symbol '_123' followed by an unexpected dot
        (
            "_123.456",
            ZishLocationException(1, 10, "The value _123.456 is not recognized."),
        ),
        #
        # Strings
        #
        # An empty string value
        ('""', ""),
        # A normal string
        ('" my string "', " my string "),
        # Contains one double-quote character
        ('"\\""', '"'),
        # Contains one unicode character
        (r'"\uABCD"', "\uABCD"),
        # ERROR: Invalid blob
        (
            "xml::\"<e a='v'>c</e>\"",
            ZishLocationException(1, 5, "The value xml is not recognized."),
        ),
        # Set with one element
        (
            '( "hello\rworld!"  )',
            ZishLocationException(1, 3, r"The value \( is not recognized."),
        ),
        # The exact same set
        (
            '("hello world!")',
            ZishLocationException(1, 9, r'The value \("hello is not recognized.'),
        ),
        # This Zish value is a string containing three newlines. The serialized
        # form's first newline is escaped into nothingness.
        (
            r'''"\
The first line of the string.
This is the second line of the string,
and this is the third line.
"''',
            """The first line of the string.
This is the second line of the string,
and this is the third line.
""",
        ),
        #
        # Blobs
        #
        # A valid blob value with zero padding characters.
        (
            """'
+AB/
'""",
            b64decode("+AB/"),
        ),
        # A valid blob value with one required padding character.
        (
            "'VG8gaW5maW5pdHkuLi4gYW5kIGJleW9uZCE='",
            b64decode("VG8gaW5maW5pdHkuLi4gYW5kIGJleW9uZCE="),
        ),
        # ERROR: Incorrect number of padding characters.
        (
            "' VG8gaW5maW5pdHkuLi4gYW5kIGJleW9uZCE== '",
            result_excess_data,
        ),
        # ERROR: Padding character within the data.
        (
            "' VG8gaW5maW5pdHku=Li4gYW5kIGJleW9uZCE= '",
            ZishLocationException(1, 42, msg_discontinuous),
        ),
        # A valid blob value with two required padding characters.
        (
            "' dHdvIHBhZGRpbmcgY2hhcmFjdGVycw== '",
            b64decode("dHdvIHBhZGRpbmcgY2hhcmFjdGVycw=="),
        ),
        # ERROR: Invalid character within the data.
        (
            "' dHdvIHBhZGRpbmc_gY2hhcmFjdGVycw= '",
            ZishLocationException(1, 37, msg_only_b64),
        ),
        #
        # Maps
        #
        # An empty Map value
        ("{ }", {}),
        # Map with two fields
        ('{ "first" : "Tom" , "last": "Riddle" }', {"first": "Tom", "last": "Riddle"}),
        # Nested map
        (
            '{"center":{"x":1.0, "y":12.5}, "radius":3}',
            {"center": {"x": 1.0, "y": 12.5}, "radius": 3},
        ),
        # Multiple top-level values
        (
            "{} 3",
            ZishLocationException(
                1,
                6,
                "Multiple top-level Zish values aren't allowed. For example, "
                "at the top level you can't have a map followed by another "
                "map.",
            ),
        ),
        # Map with only opening brace
        (
            "{",
            ZishLocationException(
                1,
                2,
                r"After this opening '\{', a key or a closing '\}' was "
                "expected, but reached the end of the document instead.",
            ),
        ),
        # Map with only opening brace and value
        (
            '{ "Etienne"',
            ZishLocationException(
                1,
                12,
                "After this key, a ':' was expected, but reached the end of "
                "the document instead.",
            ),
        ),
        # Trailing comma is invalid in Zish (like JSON)
        ("{ x:1, }", ZishLocationException(1, 5, "The value x is not recognized.")),
        # A map value containing a field with an empty name
        ('{ "":42 }', {"": 42}),
        # ERROR: repeated name 'x'
        (
            '{ "x":1, "x":null }',
            ZishLocationException(1, 19, "Duplicate map keys aren't allowed: 'x'"),
        ),
        # ERROR: missing field between commas
        (
            '{ "x":1, , }',
            ZishLocationException(1, 11, "The token type 3 isn't recognized."),
        ),
        # ERROR: Integer after value in a map
        (
            '{ "x": 1 4 }',
            ZishLocationException(1, 12, r"Expected a ',' or a '\}' here, but got '4'"),
        ),
        #
        # Lists
        #
        # An empty list value
        ("[]", []),
        # List of three ints
        ("[1, 2, 3]", [1, 2, 3]),
        # List of an int and a string
        ('[ 1 , "two" ]', [1, "two"]),
        # Nested list
        ('["a" , ["b"]]', ["a", ["b"]]),
        # Trailing comma is valid in Zish (unlike JSON)
        (
            "[ 1.2, ]",
            [Decimal("1.2")],
        ),
        # ERROR: missing element between commas
        (
            "[ 1, , 2 ]",
            ZishLocationException(1, 7, "Expected a value here, but got ','"),
        ),
        # Input string ending in a newline
        ("{}\n", {}),
        # Check good error for string that isn't finished
        (
            '"',
            ZishLocationException(
                1,
                2,
                "Parsing a string but can't find the ending '\"'. The first "
                "part of the string is: ",
            ),
        ),
        # Check good error for map when ':' is expected.
        (
            '{"num" 1}',
            ZishLocationException(1, 10, "Expected a ':' here, but got '1'."),
        ),
        # Error: List can't be a key in a map.
        (
            '{["num", 1]: 1}',
            ZishLocationException(1, 3, "A list can't be a key in a map."),
        ),
        # Invalid token after beginning of map.
        ("{:: 1}", ZishLocationException(1, 3, "The token type 2 isn't recognized.")),
        # Error: Empty string
        ("", ZishException("No Zish value found.")),
        # Input string ending in a U+00A0
        ("{}\u00A0", {}),
    ],
)
def test_loads(zish_str, pyth):
    if isinstance(pyth, ZishLocationException):
        with pytest.raises(ZishLocationException, match=str(pyth)):
            loads(zish_str)
    elif isinstance(pyth, ZishException):
        with pytest.raises(ZishException):
            loads(zish_str)
    else:
        assert loads(zish_str) == pyth


@pytest.mark.parametrize(
    "pyth,zish_str",
    [
        (
            {
                "title": "A Hero of Our Time",
                "read_date": Datetime(2017, 7, 16, 14, 5, tzinfo=Timezone.utc),
                "would_recommend": True,
                "description": None,
                "number_of_novellas": 5,
                "price": Decimal("7.99"),
                "weight": 6.88,
                "key": b"kshhgrl",
                "tags": ["russian", "novel", "19th centuary"],
            },
            """{
  "description": null,
  "key": 'a3NoaGdybA==',
  "number_of_novellas": 5,
  "price": 7.99,
  "read_date": 2017-07-16T14:05:00Z,
  "tags": [
    "russian",
    "novel",
    "19th centuary",
  ],
  "title": "A Hero of Our Time",
  "weight": 6.88,
  "would_recommend": true,
}""",
        ),
        ((), "[]"),
        (set(), "[]"),
        (0.000001, "1e-06"),
        (Decimal("0E-8"), "0E-8"),
        (
            OrderedDict(((1, 2), ("three", "four"))),
            """{
  1: 2,
  "three": "four",
}""",
        ),
        ('k"sdf', '"k\\"sdf"'),
    ],
)
def test_dumps(pyth, zish_str):
    assert dumps(pyth) == zish_str


@pytest.mark.parametrize(
    "pyth,zish_str",
    [(0e0, "0.0"), (float("-INF"), "-inf"), (float("+inFinity"), "+inf")],
)
def test_dump_float(pyth, zish_str):
    assert core._dump_float(pyth) == zish_str


@pytest.mark.parametrize(
    "pyth,zish_str",
    [('k"sdf', '"k\\"sdf"')],
)
def test_dump_str(pyth, zish_str):
    assert core._dump_str(pyth) == zish_str


def test_dumps_unrecognised_type():
    class TestClass:
        pass

    with pytest.raises(
        ZishException,
        match="Type <class "
        "'test_zish.test_dumps_unrecognised_type.<locals>.TestClass'> not recognised.",
    ):
        dumps(TestClass())
