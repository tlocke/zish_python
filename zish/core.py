import binascii
import re

from base64 import b64decode, b64encode
from collections import namedtuple
from collections.abc import Mapping
from datetime import datetime as Datetime, timezone as Timezone
from decimal import Decimal
from itertools import chain

import dateutil.parser


QUOTE = '"'
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ZishException(Exception):
    pass


class ZishLocationException(ZishException):
    def __init__(self, line, character, description):
        super().__init__(
            f"Problem at line {line} and character {character}: {description}"
        )
        self.description = description
        self.line = line
        self.character = character


# Single character tokens
TT_START_MAP = 0
TT_FINISH_MAP = 1
TT_COLON = 2
TT_COMMA = 3
TT_START_LIST = 4
TT_FINISH_LIST = 5

# Delimited tokens
TT_BYTES = 6
TT_STRING = 7

TT_PRIMITIVE = 8  # General primitive type
TT_NO_DELIM = 9  # Non-delimited primitive

TT_TIMESTAMP = 10

TT_COMMENT = 11


def load(file_like):
    return loads(file_like.read())


def dump(obj, file_like):
    file_like.write(dumps(obj))


def loads(zish_str):
    tokens = lex(zish_str)
    try:
        result = parse(next(tokens), tokens)
    except StopIteration:
        raise ZishException("No Zish value found.")
    try:
        token = next(tokens)
        raise ZishLocationException(
            token.line,
            token.character,
            "Multiple top-level Zish values aren't allowed. For example, at the top "
            "level you can't have a map followed by another map.",
        )
    except StopIteration:
        return result


def parse(token, tokens):
    if token.token_type == TT_PRIMITIVE:
        return token.value

    elif token.token_type == TT_START_LIST:
        val = []
        token = next(tokens)
        while token.token_type != TT_FINISH_LIST:
            if token.token_type in (TT_PRIMITIVE, TT_START_LIST, TT_START_MAP):
                val.append(parse(token, tokens))
            else:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"Expected a value here, but got '{token.value}'.",
                )

            token = next(tokens)
            if token.token_type == TT_COMMA:
                token = next(tokens)

            elif token.token_type == TT_FINISH_LIST:
                pass

            else:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"Expected a ',' or a ']' here, but got '{token.value}'.",
                )

        return val

    elif token.token_type == TT_START_MAP:
        val = {}

        try:
            token = next(tokens)
        except StopIteration:
            raise ZishLocationException(
                token.line,
                token.character,
                "After this opening '{', a key or a closing '}' was expected, but "
                "reached the end of the document instead.",
            )

        while token.token_type != TT_FINISH_MAP:
            if token.token_type == TT_PRIMITIVE:
                if token.value is None:
                    raise ZishLocationException(
                        token.line, token.character, "null can't be a key in a map."
                    )
                k = parse(token, tokens)
            elif token.token_type == TT_START_LIST:
                raise ZishLocationException(
                    token.line, token.character, "A list can't be a key in a map."
                )
            elif token.token_type == TT_START_MAP:
                raise ZishLocationException(
                    token.line, token.character, "A map can't be a key in a map."
                )
            else:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"The token type {token.token_type} isn't recognized.",
                )

            try:
                token = next(tokens)
            except StopIteration:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    "After this key, a ':' was expected, but reached the end of the "
                    "document instead.",
                )

            if token.token_type != TT_COLON:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"Expected a ':' here, but got '{token.value}'.",
                )

            try:
                token = next(tokens)
            except StopIteration:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    "After this ':', a value was expected, but reached the end of the "
                    "document instead.",
                )

            if token.token_type in (TT_PRIMITIVE, TT_START_LIST, TT_START_MAP):
                if k in val:
                    raise ZishLocationException(
                        token.line,
                        token.character,
                        f"Duplicate map keys aren't allowed: '{k}'.",
                    )
                val[k] = parse(token, tokens)
            else:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"Expected a value here, but got a '{token.value}' instead.",
                )

            try:
                token = next(tokens)
            except StopIteration:
                raise ZishException(
                    "Reached the end of the document without a map being closed with "
                    "a '}'."
                )

            if token.token_type == TT_COMMA:
                try:
                    token = next(tokens)
                except StopIteration:
                    raise ZishLocationException(
                        token.line,
                        token.character,
                        "After this ',' a value was expected, but reached the end of "
                        "the document instead.",
                    )

            elif token.token_type == TT_FINISH_MAP:
                pass
            else:
                raise ZishLocationException(
                    token.line,
                    token.character,
                    f"Expected a ',' or a '}}' here, but got '{token.value}'.",
                )
        return val

    else:
        raise ZishException(f"Don't recognize the token type: {token}.")


ESCAPES = {
    "0": "\u0000",  # NUL
    "a": "\u0007",  # alert BEL
    "b": "\u0008",  # backspace BS
    "t": "\u0009",  # horizontal tab HT
    "n": "\u000A",  # linefeed LF
    "f": "\u000C",  # form feed FF
    "r": "\u000D",  # carriage return CR
    "v": "\u000B",  # vertical tab VT
    '"': "\u0022",  # double quote
    "'": "\u0027",  # single quote
    "?": "\u003F",  # question mark
    "\\": "\u005C",  # backslash
    "/": "\u002F",  # forward slash
    "\u000D\u000A": "",  # empty string
    "\u000D": "",  # empty string
    "\u000A": "",
}  # empty string


def unescape(escaped_str):
    i = escaped_str.find("\\")
    if i == -1:
        return escaped_str
    else:
        head_str = escaped_str[:i]
        tail_str = escaped_str[i + 1 :]
        for k, v in ESCAPES.items():
            if tail_str.startswith(k):
                return head_str + v + unescape(tail_str[len(k) :])

        for prefix, digits in (("x", 2), ("u", 4), ("U", 8)):
            if tail_str.startswith(prefix):
                hex_str = tail_str[1 : 1 + digits]
                v = chr(int(hex_str, 16))
                return head_str + v + unescape(tail_str[1 + digits :])

        raise ZishException(
            f"Can't find a valid string following the first backslash of "
            f"'{escaped_str}'."
        )


def dumps(obj):
    return _dump(obj, "")


_repr_float = repr
float_plus_inf = float("+inf")
float_minus_inf = float("-inf")
float_nan = float("nan")


def _dump_float(obj):
    if obj == float_plus_inf:
        return "+inf"
    elif obj == float_minus_inf:
        return "-inf"
    elif obj == float_nan:
        return "nan"
    else:
        return _repr_float(obj)


def _dump_str(obj):
    qstr = obj.replace("\\", "\\\\").replace('"', '\\"')
    return f"{QUOTE}{qstr}{QUOTE}"


def _dump(obj, indent):
    if isinstance(obj, Mapping):
        new_indent = f"{indent}  "
        items = []

        item_gen = obj.items()
        try:
            item_gen = sorted(item_gen)
        except TypeError:
            pass

        for k, v in item_gen:
            items.append(
                f"\n{new_indent}{_dump(k, new_indent)}: {_dump(v, new_indent)},"
            )
        if len(items) == 0:
            return "{}"
        else:
            return "{" + "".join(items) + "\n" + indent + "}"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (list, tuple)):
        new_indent = indent + "  "
        b = "".join(f"\n{new_indent}{_dump(v, new_indent)}," for v in obj)
        return "[]" if len(b) == 0 else f"[{b}\n{indent}]"
    elif isinstance(obj, (set, frozenset)):
        ni = f"{indent}  "
        b = "".join(f"\n{ni}{_dump(v, ni)}," for v in sorted(obj))
        return "[]" if len(b) == 0 else f"[{b}\n{indent}]"
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, float):
        return _dump_float(obj)
    elif isinstance(obj, Decimal):
        return str(obj)
    elif obj is None:
        return "null"
    elif isinstance(obj, str):
        return _dump_str(obj)
    elif isinstance(obj, (bytes, bytearray)):
        return f"'{b64encode(obj).decode()}'"
    elif isinstance(obj, Datetime):
        tzinfo = obj.tzinfo
        if tzinfo is None:
            return f"{obj.isoformat()}-00:00"
        elif tzinfo.utcoffset(obj) == Timezone.utc.utcoffset(obj):
            return obj.strftime(UTC_FORMAT)
        else:
            return obj.isoformat()
    else:
        raise ZishException(f"Type {type(obj)} not recognised.")


Token = namedtuple("Token", ["token_type", "line", "character", "value"])


SINGLE_TOKENS = {
    "{": TT_START_MAP,
    "}": TT_FINISH_MAP,
    ":": TT_COLON,
    ",": TT_COMMA,
    "[": TT_START_LIST,
    "]": TT_FINISH_LIST,
}


SPACE = {
    None,  # EOF
    "\u0009",  # tab
    "\u000A",  # line feed
    "\u000B",  # vertical tab
    "\u000C",  # form feed
    "\u000D",  # carriage return
    "\u0020",
    "\u00A0",  # NO-BREAK SPACE
}  # space

NO_DELIM_END = set(SINGLE_TOKENS.keys()).union(SPACE, {"/"})

RE_INTEGER = re.compile(r"-?(0|[1-9]\d*)$", re.ASCII)
RE_DECIMAL = re.compile(r"-?(0|[1-9]\d*)(\.\d*)?([eE][+\-]?\d+)?$", re.ASCII)
RE_TIMESTAMP = re.compile(
    r"\d\d\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T"
    r"([01]\d|2[0-3]):[0-5]\d:[0-5]\d(\.\d+)?"
    r"([zZ]|[+\-]([01]\d|2[0-3]):[0-5]\d)$",
    re.ASCII,
)


def lex(zish_str):
    in_token = False
    token_type = None
    payload = []
    line = character = 1
    token_line = token_character = None
    prev_c = None
    for c in chain(zish_str, (None,)):
        # print("character", c, token_type, "payload", payload)
        consumed = False

        # Set position
        if c == "\n":
            line += 1
            character = 1
        character += 1

        if in_token:
            if token_type == TT_STRING:
                if c == '"' and prev_c != "\\":
                    yield Token(
                        TT_PRIMITIVE, line, character, unescape("".join(payload))
                    )
                    in_token = False
                    consumed = True
                elif c is None:
                    raise ZishLocationException(
                        token_line,
                        token_character,
                        f"Parsing a string but can't find the ending '\"'. The first "
                        f'part of the string is: {"".join(payload)[:10]}',
                    )

                else:
                    payload.append(c)

            elif token_type == TT_BYTES:
                if c == "'":
                    try:
                        yield Token(
                            TT_PRIMITIVE,
                            line,
                            character,
                            b64decode("".join(payload).strip(), validate=True),
                        )
                    except binascii.Error as e:
                        raise ZishLocationException(line, character, str(e))

                    in_token = False
                    consumed = True
                elif c is None:
                    raise ZishLocationException(
                        token_line,
                        token_character,
                        f"Parsing bytes but can't find the ending '''. The first part "
                        f'of the bytes is: {"".join(payload)[:10]}',
                    )
                else:
                    payload.append(c)

            elif token_type == TT_NO_DELIM:
                if c == "T":
                    token_type = TT_TIMESTAMP
                    payload.append(c)

                elif c in NO_DELIM_END:
                    ustr = "".join(payload)
                    if ustr == "true":
                        yield Token(TT_PRIMITIVE, line, character, True)
                    elif ustr == "false":
                        yield Token(TT_PRIMITIVE, line, character, False)
                    elif ustr == "null":
                        yield Token(TT_PRIMITIVE, line, character, None)
                    elif RE_INTEGER.match(ustr) is not None:
                        yield Token(TT_PRIMITIVE, line, character, int(ustr))
                    elif RE_DECIMAL.match(ustr) is not None:
                        yield Token(TT_PRIMITIVE, line, character, Decimal(ustr))
                    else:
                        raise ZishLocationException(
                            line, character, f"The value {ustr} is not recognized."
                        )
                    in_token = False

                else:
                    payload.append(c)

            elif token_type == TT_TIMESTAMP:
                if c in ("z", "Z"):
                    payload.append(c)
                    tstr = "".join(payload)
                    if RE_TIMESTAMP.match(tstr) is not None:
                        try:
                            yield Token(
                                TT_PRIMITIVE,
                                line,
                                character,
                                dateutil.parser.parse(tstr),
                            )
                        except dateutil.parser.ParserError as e:
                            raise ZishLocationException(
                                line,
                                character,
                                f"Can't parse the timestamp '{tstr}'.",
                            ) from e
                    else:
                        raise ZishLocationException(
                            line,
                            character,
                            f"The timestamp {tstr} is not recognized.",
                        )
                    in_token = False
                    consumed = True

                elif payload.count(":") == 3 and c in NO_DELIM_END:
                    tstr = "".join(payload)
                    if RE_TIMESTAMP.match(tstr) is not None:
                        try:
                            yield Token(
                                TT_PRIMITIVE,
                                line,
                                character,
                                dateutil.parser.parse(tstr),
                            )
                        except dateutil.parser.ParserError as e:
                            raise ZishLocationException(
                                line,
                                character,
                                f"Can't parse the timestamp '{tstr}'.",
                            ) from e
                    else:
                        raise ZishLocationException(
                            line,
                            character,
                            f"The timestamp {tstr} is not recognized.",
                        )
                    in_token = False
                elif c is None:
                    raise ZishLocationException(
                        line,
                        character,
                        f'The timestamp {"".join(payload)} is malformed.',
                    )
                else:
                    payload.append(c)

            elif token_type == TT_COMMENT:
                if c == "/" and prev_c == "*":
                    if len(payload) > 2:
                        in_token = False
                        consumed = True
                    else:
                        raise ZishException(
                            "You can't have a comment that's '/*/', an empty comment "
                            "is '/**/'."
                        )
                elif prev_c == "/" and len(payload) == 1 and c != "*":
                    raise ZishLocationException(
                        line, character, "A comment starts with a '/*'."
                    )
                elif c is None:
                    raise ZishException(
                        "Reached the end of the document without the comment being "
                        "closed with a '*/'"
                    )
                else:
                    payload.append(c)

            else:
                raise Exception(
                    f"Token type {token_type} not recognized at character {c}."
                )

        if not in_token and not consumed:
            if c in SPACE:
                pass
            elif c in SINGLE_TOKENS:
                yield Token(SINGLE_TOKENS[c], line, character, c)
            elif c == '"':
                token_type = TT_STRING
                in_token = True
                token_line = line
                token_character = character
                payload.clear()
            elif c == "'":
                token_type = TT_BYTES
                in_token = True
                token_line = line
                token_character = character
                payload.clear()
            elif c == "/":
                token_type = TT_COMMENT
                in_token = True
                payload.clear()
                payload.append(c)
            else:
                token_type = TT_NO_DELIM
                in_token = True
                payload.clear()
                payload.append(c)

        prev_c = c
