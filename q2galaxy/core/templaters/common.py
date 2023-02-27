# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import io
import hashlib
from textwrap import dedent

import qiime2
import qiime2.sdk as sdk

import q2galaxy
from q2galaxy.core.util import XMLNode, rst_header


def make_tool_id(plugin_id, action_id):
    return '__'.join(['qiime2', plugin_id, action_id])


def make_tool_name(plugin_id, action_id):
    return ' '.join(['qiime2', plugin_id.replace('_', '-'),
                     action_id.replace('_', '-')])


def make_tool_name_from_id(tool_id):
    _, plugin, action = tool_id.split('__')
    return make_tool_name(plugin, action)


def make_config():
    configfiles = XMLNode('configfiles')
    configfiles.append(XMLNode('inputs', name='inputs', data_style='paths'))
    return configfiles


def make_citations(plugin=None, action=None):
    citations_xml = XMLNode('citations')
    citations = []
    if action is not None:
        citations.extend(action.citations)
    if plugin is not None:
        citations.extend(plugin.citations)

    citations.extend(qiime2.__citations__)

    for idx, cite_record in enumerate(citations, 1):
        doi = cite_record.fields.get('doi')
        if doi is not None:
            citations_xml.append(XMLNode('citation', doi, type='doi'))
        else:
            with io.StringIO() as fh:
                sdk.Citations([(f'cite{idx}', cite_record)]).save(fh)
                citations_xml.append(XMLNode('citation', fh.getvalue(),
                                             type='bibtex'))

    return citations_xml


def make_requirements(conda_meta, *project_names):
    if len(project_names) == 1 and project_names[0] == 'q2-mystery-stew':
        pass

    requirements = XMLNode('requirements')
    if conda_meta.metapackage is None:
        requirements.append(
            XMLNode('requirement', 'q2galaxy',
                    type='package', version=q2galaxy.__version__))
    for dep, version in conda_meta.iter_deps(*project_names,
                                             include_self=True):
        r = XMLNode('requirement', dep, type='package', version=version)
        requirements.append(r)

    return requirements


def make_builtin_version(plugins):
    env_hash = 0
    for plugin in plugins:
        env_hash ^= int.from_bytes(
            hashlib.md5(f'{plugin.id}={plugin.version}'.encode()).digest(),
            'big')
    env_hash = env_hash.to_bytes(16, 'big').hex()[:8]  # use 4 bytes of hash
    local = 'dist.h' + env_hash
    if '+' in q2galaxy.__version__:
        local = '-' + local
    else:
        local = '+' + local

    return q2galaxy.__version__ + local


def make_formats_help(formats):
    help_ = rst_header('Formats:', 2)
    help_ += 'These formats have documentation available.\n'
    missing = []
    for format_ in formats:
        if format_.__doc__ is None:
            missing.append(format_)
            continue
        help_ += rst_header(format_.__name__, 3)
        help_ += dedent("    " + format_.__doc__)

    if missing:
        help_ += rst_header('Additional formats without documentation:', 3)
        for format_ in missing:
            help_ += f' - {format_.__name__}\n'

    return help_
