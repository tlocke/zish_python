import arrow
from decimal import Decimal
from base64 import b64decode, b64encode
from collections.abc import Mapping
from collections import namedtuple
from datetime import datetime as Datetime, timezone as Timezone
import re
from itertools import chain
import binascii


QUOTE = '"'
UTC_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class ZishException(Exception):
    pass


class ZishLocationException(ZishException):
    def __init__(self, line, character, message):
        super().__init__(
            "Problem at line " + str(line) + " and character " +
            str(character) + ": " + message)


# Single character tokens
TT_START_MAP = 0
TT_FINISH_MAP = 1
TT_COLON = 2
TT_COMMA = 3
TT_START_LIST = 4
TT_FINISH_LIST = 5
TT_START_SET = 6
TT_FINISH_SET = 7

# Delimited tokens
TT_BYTES = 8
TT_STRING = 9

TT_PRIMITIVE = 10  # General primitive type
TT_NO_DELIM = 11  # Non-delimited primitive

TT_TIMESTAMP = 12

# Comments
TT_COMMENT = 13  # Either inline or block
TT_INLINE_COMMENT = 14
TT_BLOCK_COMMENT = 15


def load(file_like):
    return loads(file_like.read())


def dump(obj, file_like):
    file_like.write(dumps(obj))


def loads(zish_str):
    tokens = lex(zish_str)
    token = next(tokens)
    return parse(token, tokens)


def parse(token, tokens):
    if token.token_type == TT_PRIMITIVE:
        return token.value

    elif token.token_type == TT_START_LIST:
        val = []
        token = next(tokens)
        while token.token_type != TT_FINISH_LIST:
            if token.token_type in (
                    TT_PRIMITIVE, TT_START_LIST, TT_START_MAP, TT_START_SET):
                val.append(parse(token, tokens))
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a primitive value here, but got '" +
                    token.value + "'")

            token = next(tokens)
            if token.token_type == TT_COMMA:
                token = next(tokens)
                if token.token_type == TT_FINISH_LIST:
                    raise ZishLocationException(
                        token.line, token.character,
                        "Trailing commas aren't allowed in Zish.")
            elif token.token_type == TT_FINISH_LIST:
                pass
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a ',' or a ']' here, but got '" + token.value +
                    "'")

        return tuple(val)

    elif token.token_type == TT_START_MAP:
        val = {}
        token = next(tokens)
        while token.token_type != TT_FINISH_MAP:

            if token.token_type == TT_PRIMITIVE:
                k = token.value
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a primitive value here, but got '" +
                    token.value + "'")

            token = next(tokens)
            if token.token_type != TT_COLON:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a ':' here, but got '" + str(token.value) + "'.")

            token = next(tokens)
            if token.token_type in (
                    TT_PRIMITIVE, TT_START_LIST, TT_START_MAP, TT_START_SET):
                val[k] = parse(token, tokens)
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a primitive or one of ('[', '{', '(') here, "
                    "but got '" + token.value + "'")

            token = next(tokens)
            if token.token_type == TT_COMMA:
                token = next(tokens)
                if token.token_type == TT_FINISH_MAP:
                    raise ZishLocationException(
                        token.line, token.character,
                        "Trailing commas aren't allowed in Zish.")
            elif token.token_type == TT_FINISH_MAP:
                pass
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a ',' or a '}' here, but got '" + token.value +
                    "'")
        return val

    elif token.token_type == TT_START_SET:
        val = set()
        token = next(tokens)
        while token.token_type != TT_FINISH_SET:
            if token.token_type in (TT_PRIMITIVE, TT_START_LIST, TT_START_SET):
                val.add(parse(token, tokens))
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a primitive value here, but got '" +
                    token.value + "'")

            token = next(tokens)
            if token.token_type == TT_COMMA:
                token = next(tokens)
                if token.token_type == TT_FINISH_SET:
                    raise ZishLocationException(
                        token.line, token.character,
                        "Trailing commas aren't allowed in Zish.")
            elif token.token_type == TT_FINISH_SET:
                pass
            else:
                raise ZishLocationException(
                    token.line, token.character,
                    "Expected a ',' or a ')' here, but got '" + token.value +
                    "'")
        return frozenset(val)
    else:
        raise ZishException("Don't recognize the token type: " + str(token))


ESCAPES = {
    '0': '\u0000',   # NUL
    'a': '\u0007',   # alert BEL
    'b': '\u0008',   # backspace BS
    't': '\u0009',   # horizontal tab HT
    'n': '\u000A',   # linefeed LF
    'f': '\u000C',   # form feed FF
    'r': '\u000D',   # carriage return CR
    'v': '\u000B',   # vertical tab VT
    '"': '\u0022',   # double quote
    "'": '\u0027',   # single quote
    '?': '\u003F',   # question mark
    '\\': '\u005C',  # backslash
    '/': '\u002F',   # forward slash
    '\u000D\u000A': '',  # empty string
    '\u000D': '',  # empty string
    '\u000A': ''}  # empty string


def unescape(escaped_str):
    i = escaped_str.find('\\')
    if i == -1:
        return escaped_str
    else:
        head_str = escaped_str[:i]
        tail_str = escaped_str[i+1:]
        for k, v in ESCAPES.items():
            if tail_str.startswith(k):
                return head_str + v + unescape(tail_str[len(k):])

        for prefix, digits in (('x', 2), ('u', 4), ('U', 8)):
            if tail_str.startswith(prefix):
                hex_str = tail_str[1:1 + digits]
                v = chr(int(hex_str, 16))
                return head_str + v + unescape(tail_str[1 + digits:])

        raise ZishException(
            "Can't find a valid string following the first backslash of '" +
            escaped_str + "'.")


def dumps(obj):
    return _dump(obj, '')


def _dump(obj, indent):
    if isinstance(obj, Mapping):
        new_indent = indent + '  '
        items = []
        for k, v in sorted(obj.items()):
            items.append(
                '\n' + new_indent + _dump(k, new_indent) + ': ' +
                _dump(v, new_indent))
        return '{' + ','.join(items) + '}'
    elif isinstance(obj, bool):
        return 'true' if obj else 'false'
    elif isinstance(obj, (list, tuple)):
        new_indent = indent + '  '
        b = ','.join('\n' + new_indent + _dump(v, new_indent) for v in obj)
        return '[' + b + ']'
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, float):
        val = str(obj)
        if 'e' not in val:
            return val + 'e0'
        else:
            return val
    elif isinstance(obj, Decimal):
        return str(obj).replace('e', 'd')
    elif obj is None:
        return 'null'
    elif isinstance(obj, str):
        return QUOTE + obj + QUOTE
    elif isinstance(obj, (bytes, bytearray)):
        return "'" + b64encode(obj).decode() + "'"
    elif isinstance(obj, Datetime):
        tzinfo = obj.tzinfo
        if tzinfo is None:
            return obj.isoformat() + '-00:00'
        elif tzinfo.utcoffset(obj) == Timezone.utc.utcoffset(obj):
            return obj.strftime(UTC_FORMAT)
        else:
            return obj.isoformat()
    elif isinstance(obj, (set, frozenset)):
        new_indent = indent + '  '
        b = ','.join('\n' + new_indent + _dump(v, new_indent) for v in obj)
        return '(' + b + ')'
    else:
        raise ZishException("Type " + str(type(obj)) + " not recognised.")


Token = namedtuple('Token', ['token_type', 'line', 'character', 'value'])


SINGLE_TOKENS = {
    '{': TT_START_MAP,
    '}': TT_FINISH_MAP,
    ':': TT_COLON,
    ',': TT_COMMA,
    '[': TT_START_LIST,
    ']': TT_FINISH_LIST,
    '(': TT_START_SET,
    ')': TT_FINISH_SET}


SPACE = {
    None,  # EOF
    '\u0009',  # tab
    '\u000A',  # line feed
    '\u000B',  # vertical tab
    '\u000C',  # form feed
    '\u000D',  # carriage return
    '\u0020'}  # space

NO_DELIM_END = set(SINGLE_TOKENS.keys()).union(SPACE, {'/'})

RE_INTEGER = re.compile(r'-?(0|[1-9]\d*)$', re.ASCII)
RE_FLOAT = re.compile(r'(-?(0|\d*)(\.\d*)?e[+\-]?\d+|[+\-]inf|nan)$', re.ASCII)
RE_DECIMAL = re.compile(r'-?(0|[1-9]\d*)(\.\d*)?(d[+\-]?\d+)?$', re.ASCII)
RE_TIMESTAMP = re.compile(
    r'\d\d\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T'
    r'([01]\d|2[0-3]):[0-5]\d:[0-5]\d(\.\d+)?'
    r'([zZ]|[+\-]([01]\d|2[0-3]):[0-5]\d)$',
    re.ASCII)


def lex(zish_str):
    in_token = False
    token_type = None
    payload = []
    line = 0
    character = -1
    token_line = token_character = None
    prev_c = None
    for c in chain(zish_str, (None,)):
        # print("character", c, token_type, "payload", payload)
        consumed = False

        # Set position
        if c == '\n':
            line += 1
            character = -1
        character += 1

        if in_token:
            if token_type == TT_STRING:
                if c == '"' and prev_c != '\\':
                    yield Token(
                        TT_PRIMITIVE, line, character,
                        unescape(''.join(payload)))
                    in_token = False
                    consumed = True
                elif c is None:
                    raise ZishLocationException(
                        token_line, token_character,
                        "Parsing a string but can't find the ending '\"'. " +
                        "The first part of the string is: " +
                        ''.join(payload)[:10])

                else:
                    payload.append(c)

            elif token_type == TT_BYTES:
                if c == "'":
                    try:
                        yield Token(
                            TT_PRIMITIVE, line, character,
                            b64decode(''.join(payload).strip(), validate=True))
                    except binascii.Error as e:
                        raise ZishLocationException(line, character, str(e))

                    in_token = False
                    consumed = True
                elif c is None:
                    raise ZishLocationException(
                        token_line, token_character,
                        "Parsing bytes but can't find the ending '\''. " +
                        "The first part of the bytes is: " +
                        ''.join(payload)[:10])
                else:
                    payload.append(c)

            elif token_type == TT_NO_DELIM:
                if c == 'T':
                    token_type = TT_TIMESTAMP
                    payload.append(c)

                elif c in NO_DELIM_END:
                    ustr = ''.join(payload)
                    if ustr == 'true':
                        yield Token(TT_PRIMITIVE, line, character, True)
                    elif ustr == 'false':
                        yield Token(
                            TT_PRIMITIVE, line, character, False)
                    elif ustr == 'null':
                        yield Token(TT_PRIMITIVE, line, character, None)
                    elif RE_INTEGER.match(ustr) is not None:
                        yield Token(
                            TT_PRIMITIVE, line, character, int(ustr))
                    elif RE_FLOAT.match(ustr) is not None:
                        yield Token(
                            TT_PRIMITIVE, line, character, float(ustr))
                    elif RE_DECIMAL.match(ustr) is not None:
                        yield Token(
                            TT_PRIMITIVE, line, character,
                            Decimal(ustr.replace('d', 'e')))
                    else:
                        raise ZishLocationException(
                            line, character, "The value " + ustr +
                            " is not recognized.")
                    in_token = False

                else:
                    payload.append(c)

            elif token_type == TT_TIMESTAMP:
                if c in ('z', 'Z'):
                    payload.append(c)
                    tstr = ''.join(payload)
                    if RE_TIMESTAMP.match(tstr) is not None:
                        try:
                            yield Token(
                                TT_PRIMITIVE, line, character,
                                arrow.get(tstr).datetime)
                        except arrow.parser.ParserError as e:
                            raise ZishLocationException(
                                line, character,
                                "Can't parse the timestamp '" +
                                tstr + "'.") from e
                    else:
                        raise ZishLocationException(
                            line, character, "The timestamp " + tstr +
                            " is not recognized.")
                    in_token = False
                    consumed = True

                elif payload.count(':') == 3 and c in NO_DELIM_END:
                    tstr = ''.join(payload)
                    if RE_TIMESTAMP.match(tstr) is not None:
                        try:
                            yield Token(
                                TT_PRIMITIVE, line, character,
                                arrow.get(tstr).datetime)
                        except arrow.parser.ParserError as e:
                            raise ZishLocationException(
                                line, character,
                                "Can't parse the timestamp '" +
                                tstr + "'.") from e
                    else:
                        raise ZishLocationException(
                            line, character, "The timestamp " + tstr +
                            " is not recognized.")
                    in_token = False
                elif c is None:
                    raise ZishLocationException(
                        line, character, "The timestamp " + ''.join(payload) +
                        " is malformed.")
                else:
                    payload.append(c)

            elif token_type == TT_COMMENT:
                if c == '/':
                    token_type = TT_INLINE_COMMENT
                elif c == '*':
                    token_type = TT_BLOCK_COMMENT
                else:
                    raise ZishLocationException(
                        line, character, "Expected a '/' or '*' here.")

            elif token_type == TT_INLINE_COMMENT:
                if c == '\n':
                    in_token = False
                    consumed = True

            elif token_type == TT_BLOCK_COMMENT:
                if c == '/' and prev_c == '*':
                    in_token = False
                    consumed = True

            else:
                raise Exception(
                    "Token type " + str(token_type) +
                    " not recognized. at character " + c)

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
            elif c == '/':
                token_type = TT_COMMENT
                in_token = True
                payload.clear()
            else:
                token_type = TT_NO_DELIM
                in_token = True
                payload.clear()
                payload.append(c)

        prev_c = c
