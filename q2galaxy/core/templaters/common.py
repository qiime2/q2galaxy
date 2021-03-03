# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import io
import hashlib

import qiime2
import qiime2.sdk as sdk

import q2galaxy
from q2galaxy.core.util import XMLNode


def make_tool_id(plugin_id, action_id):
    return '_'.join(['qiime2',
                     plugin_id.replace('_', '-'),
                     action_id.replace('_', '-')])


def make_tool_name(plugin_name, action_id):
    return ' '.join(['qiime2', plugin_name, action_id.replace('_', '-')])


def make_tool_name_from_id(tool_id):
    _, plugin, action = tool_id.split('_')
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
        with io.StringIO() as fh:
            sdk.Citations([(f'cite{idx}', cite_record)]).save(fh)
            citations_xml.append(XMLNode('citation', fh.getvalue(),
                                         type='bibtex'))

    return citations_xml


def make_requirements(conda_meta, *project_names):
    # HACK:
    # use a single environment when templating instead of following the full
    # trail. An exception to this is q2-mystery-stew
    if len(project_names) == 1 and project_names[0] == 'q2-mystery-stew':
        pass
    else:
        pm = sdk.PluginManager()
        project_names = [p.project_name for p in pm.plugins.values()]
    requirements = XMLNode('requirements')
    for dep, version in conda_meta.iter_deps(*project_names,
                                             include_self=True):
        r = XMLNode('requirement', dep, type='package', version=version)
        requirements.append(r)

    requirements.append(XMLNode('requirement', 'q2galaxy',
                                type='package', version=q2galaxy.__version__))
    return requirements


def make_builtin_version(plugins):
    env_hash = 0
    for plugin in plugins:
        env_hash ^= int.from_bytes(
            hashlib.md5(f'{plugin.id}={plugin.version}'.encode()).digest(),
            'big')
    env_hash = env_hash.to_bytes(16, 'big').hex()[:8]  # use 4 bytes of hash
    return f'{q2galaxy.__version__}+dist.h{env_hash}'
