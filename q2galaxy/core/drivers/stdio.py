# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import sys
import textwrap
import tempfile
import contextlib

import qiime2.util


GALAXY_TRIMMED_STRING_LEN = 255
# the width can be adjusted in the UI, but the default + kerning is about this
MISC_INFO_WIDTH = 37


@contextlib.contextmanager
def stdio_files():
    out = tempfile.NamedTemporaryFile(prefix='q2galaxy-stdout-', suffix='.log')
    err = tempfile.NamedTemporaryFile(prefix='q2galaxy-stderr-', suffix='.log')

    with out as out, err as err:
        yield (out, err)
        # Everything has gone well so far, print the final contents
        _print_stdio((out, err))


def error_handler(header=''):
    def _decorator(function):
        def wrapped(*args, _stdio=(None, None), **kwargs):
            try:
                out, err = _stdio
                with qiime2.util.redirected_stdio(stdout=out, stderr=err):
                    return function(*args, **kwargs)
            except Exception as e:
                lines = (header + str(e)).split('\n')  # respect newlines
                error_lines = []
                for line in lines:
                    error_lines.extend(textwrap.wrap(line, MISC_INFO_WIDTH))
                # Fill the TrimmedString(255) with empty characters. This will
                # be stripped in the UI, but will prevent other parts of stdio
                # from being sent by the API
                error_lines.append(" " * GALAXY_TRIMMED_STRING_LEN)
                # trailing sad face (prevent stderr from showing up
                # immediately after, doubling the error message)
                error_lines.append(":(")
                misc_info = '\n'.join(error_lines)

                print(misc_info, file=sys.stdout)
                print(misc_info, file=sys.stderr)
                _print_stdio(_stdio)

                raise  # finish with traceback and thus exit

        return wrapped
    return _decorator


def _print_stdio(stdio):
    out, err = stdio
    out.seek(0)
    err.seek(0)
    for line in out:  # loop, just in case it's very big (like MAFFT)
        print(line.decode('utf8'), file=sys.stdout, end='')

    for line in err:
        print(line.decode('utf8'), file=sys.stderr, end='')
