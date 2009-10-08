import re

LWS = "(?:\r\n)?[ \t]+"
CTL_RANGE = "\x00-\x1f\x7f"
CTL = r"[%s]" % CTL_RANGE
SEPARATORS_RANGE = re.escape(r"()<>@,;:\"/[]?={}"+" \t")

# any character except CTLs or separators
TOKEN = r"[^%s%s]+" % (CTL_RANGE, SEPARATORS_RANGE)

QUOTED_PAIR = r"\\."
QDTEXT = r'[^"]'
QUOTED_STRING = r'"(?:%s|%s)*"' % (QDTEXT,QUOTED_PAIR)

PARAMETER = "(%s)=(%s)" % (TOKEN, "(?:%s|%s)" % (TOKEN, QUOTED_STRING))

def parseMediaType(value):
    TYPE = r"((%s)/(%s))" % (TOKEN, TOKEN)

    parts = re.split(r"\s*;\s*", value)
    type_match = re.match(TYPE, parts[0])
    if type_match == None:
        raise Exception("Cannot parse media type")

    result = {
        "media_type": type_match.group(1),
        "type": type_match.group(2),
        "subtype": type_match.group(3),
        "params": {}
    }

    for param_str in parts[1:]:
        param_match = re.match(PARAMETER, param_str)
        if param_match != None:
            result['params'][param_match.group(1)] = param_match.group(2)

    return result

print parseMediaType("foo/bar")
print parseMediaType("foo/bar; charset=baz")
print parseMediaType("application/json; charset=UTF-8")
print parseMediaType('application/json; charset="UTF-8"')
