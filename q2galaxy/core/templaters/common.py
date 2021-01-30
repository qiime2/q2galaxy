import io

import qiime2
import qiime2.sdk as sdk

import q2galaxy
from q2galaxy.core.util import XMLNode


def make_tool_id(plugin_id, action_id):
    return '.'.join(['q2', plugin_id, action_id])


def make_tool_name(plugin_name, action_id):
    return ' '.join(['qiime2', plugin_name, action_id.replace('_', '-')])


def make_tool_name_from_id(tool_id):
    _, plugin, action = tool_id.split('.')
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


def make_requirements(conda_meta, project_name):
    requirements = XMLNode('requirements')
    for dep, version in conda_meta.iter_deps(project_name, include_self=True):
        r = XMLNode('requirement', dep, type='package', version=version)
        requirements.append(r)

    requirements.append(XMLNode('requirement', 'q2galaxy',
                                type='package', version=q2galaxy.__version__))
    return requirements
