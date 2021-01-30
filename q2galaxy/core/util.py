import re
import xml.dom.minidom as dom
import xml.etree.ElementTree as xml

import qiime2.sdk as sdk


def XMLNode(name_, _text=None, **attrs):
    e = xml.Element(name_, attrs)
    if _text is not None:
        e.text = _text
    return e


def write_tool(tool, filepath):
    xmlstr = dom.parseString(xml.tostring(tool)).toprettyxml(indent="   ")
    with open(filepath, 'w') as fh:
        fh.write(xmlstr)


def get_mystery_stew():
    from q2_mystery_stew.plugin_setup import create_plugin

    pm = sdk.PluginManager(add_plugins=False)

    test_plugin = create_plugin(ints=True)
    pm.add_plugin(test_plugin)

    return pm.get_plugin(id='mystery_stew')


# see: https://github.com/galaxyproject/galaxy/blob
#      /2f3096790d4a77ba75b651f4abc43c740687c1e1/lib/galaxy/util
#      /__init__.py#L527-L539
# AKA: galaxy.util:mapped_chars
_escaped = [
    # only `[]` is likely to come up, but better safe than sorry
    ('[', '__ob__'),
    (']', '__cb__'),
    ('>', '__gt__'),
    ('<', '__lt__'),
    ('\'', '__sq__'),
    ('"', '__dq__'),
    ('{', '__oc__'),
    ('}', '__cc__'),
    ('@', '__at__'),
    ('\n', '__cn__'),
    ('\r', '__cr__'),
    ('\t', '__tc__'),
    ('#', '__pd__')
]


def galaxy_esc(s):
    for char, esc in _escaped:
        s = s.replace(char, esc)
    return s


def galaxy_unesc(s):
    for char, esc in _escaped:
        s = s.replace(esc, char)
    return s


def pretty_fmt_name(format_obj):
    # from SO: https://stackoverflow.com/a/9283563/579416
    spaced = re.sub(
        r"""
        (            # start the group
            # alternative 1
        (?<=[a-z])  # current position is preceded by a lower char
                    # (positive lookbehind: does not consume any char)
        [A-Z]       # an upper char
                    #
        |   # or
            # alternative 2
        (?<!\A)     # current position is not at the beginning of the str
                    # (negative lookbehind: does not consume any char)
        [A-Z]       # an upper char
        (?=[a-z])   # matches if next char is a lower char
                    # lookahead assertion: does not consume any char
        )           # end the group
        """, r' \1', format_obj.__name__, flags=re.VERBOSE)

    final = []
    for token in spaced.split(' '):
        if token == 'Fmt':
            token = 'Format'
        elif token == 'Dir':
            token = 'Directory'

        final.append(token)

    return ' '.join(final)


def rst_header(header, level):
    fill = ['=', '-', '*', '^'][level-1]
    return '\n'.join(['', header, fill * len(header), ''])
