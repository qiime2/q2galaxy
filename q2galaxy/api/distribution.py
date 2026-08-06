# ----------------------------------------------------------------------------
# Copyright (c) 2018-2026, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import shutil
from xml.sax.saxutils import quoteattr

import yaml

import qiime2.sdk as sdk


_TOOLS_DIR = 'tools'
_COLLECTIONS_DIR = 'tool_collections'
_SUITE_PREFIX = 'suite_qiime2__'


class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _created_or_updated(path):
    return 'updated' if os.path.exists(path) else 'created'


def _write_yaml_iter(data, path):
    status = _created_or_updated(path)
    with open(path, 'w') as fh:
        yaml.dump(data, fh, Dumper=_Dumper, default_flow_style=False,
                  sort_keys=False, allow_unicode=True)
    yield {'status': status, 'type': 'file', 'path': path}


def _ensure_gitkeep_iter(directory):
    os.makedirs(directory, exist_ok=True)
    if not os.listdir(directory):
        path = os.path.join(directory, '.gitkeep')
        with open(path, 'w'):
            pass
        yield {'status': 'created', 'type': 'file', 'path': path}


def _as_categories(value, context):
    if not isinstance(value, list) or not all(
            isinstance(category, str) for category in value):
        raise ValueError(f"{context} categories must be a list of strings.")
    return value


def _plugin_definition(value):
    if isinstance(value, str):
        return {'id': value}
    if not isinstance(value, dict) or not isinstance(value.get('id'), str):
        raise ValueError(
            "Each plugin must be an id or a mapping containing an id.")
    return value


def _environment_for(distro, container):
    if container is not None:
        return None, container

    distro_container = distro.get('container')
    if distro_container is not None:
        return None, distro_container

    # This keeps the existing galaxy-tools distros.yaml schema usable while
    # allowing new configurations to use the more direct `container` key.
    image = distro.get('default_docker_image')
    version = distro.get('default_version')
    if image is not None:
        if version is not None:
            image = f'{image}:{version}'
        return None, image

    return distro.get('metapackage'), None


def _remote_repository_url(repository_url, repository_branch, suite_name):
    return (f"{repository_url.rstrip('/')}/tree/{repository_branch}/"
            f"{_TOOLS_DIR}/{suite_name}")


def _plugin_shed(plugin, categories, owner, repository_url,
                 repository_branch):
    suite_name = _SUITE_PREFIX + plugin.id
    description = (f"Galaxy suite for QIIME 2 plugin: '{plugin.name}'."
                   f" {plugin.short_description}")
    # ToolShed copies this field into XML without consistently escaping it.
    description = quoteattr(description)[1:-1]

    return {
        'owner': owner,
        'type': 'unrestricted',
        'homepage_url': plugin.website,
        'remote_repository_url': _remote_repository_url(
            repository_url, repository_branch, suite_name),
        'categories': categories,
        'auto_tool_repositories': {
            'name_template': '{{ tool_id }}',
            'description_template': (
                "Galaxy tool for QIIME 2 action: '{{tool_name}}'."),
        },
        'suite': {
            'name': suite_name,
            'description': description,
            'long_description': plugin.description,
        },
    }


def _builtin_shed(distro_name, categories, owner, repository_url,
                  repository_branch):
    suite_name = f'suite_qiime2_{distro_name}__tools'
    description = ("Galaxy suite for QIIME 2 builtins for the "
                   f"'{distro_name}' distribution.")
    return {
        'owner': owner,
        'type': 'unrestricted',
        'homepage_url': 'https://qiime2.org',
        'remote_repository_url': _remote_repository_url(
            repository_url, repository_branch, suite_name),
        'categories': categories,
        'auto_tool_repositories': {
            'name_template': '{{ tool_id }}',
            'description_template': (
                "Galaxy tool for QIIME 2 builtin: '{{ tool_name }}'."),
        },
        'suite': {
            'name': suite_name,
            'description': description,
            'long_description': description,
        },
    }


def _collection_shed(distro, dependencies, owner):
    categories = []
    for dependency in dependencies:
        for category in dependency['categories']:
            if category not in categories:
                categories.append(category)

    suite_name = f"suite_qiime2_{distro['name']}"
    description = quoteattr(distro['description'])[1:-1]
    return {
        'owner': owner,
        'categories': categories,
        'suite': {
            'name': suite_name,
            'description': description,
            'include_repositories': [
                {'name': dependency['suite']['name'],
                 'owner': dependency['owner']}
                for dependency in dependencies
            ],
        },
    }


def _load_config(path):
    with open(path) as fh:
        config = yaml.safe_load(fh)

    if not isinstance(config, dict):
        raise ValueError("Distribution configuration must be a mapping.")
    distributions = config.get('distributions')
    if not isinstance(distributions, list) or not distributions:
        raise ValueError(
            "Distribution configuration must contain a non-empty "
            "'distributions' list.")
    return distributions


def _prepare_output_iter(output, clean):
    tools_dir = os.path.join(output, _TOOLS_DIR)
    collections_dir = os.path.join(output, _COLLECTIONS_DIR)
    if clean:
        for path in (tools_dir, collections_dir):
            if os.path.exists(path):
                shutil.rmtree(path)

    for path in (tools_dir, collections_dir):
        if not os.path.exists(path):
            os.makedirs(path)
            yield {'status': 'created', 'type': 'directory', 'path': path}


def template_distribution_iter(config, output, container=None, owner='q2d2',
                               repository_url=(
                                   'https://github.com/qiime2/galaxy-tools'),
                               repository_branch='main', clean=False):
    """Render a distribution's wrappers and ToolShed repository metadata.

    ``config`` accepts the existing galaxy-tools ``distros.yaml`` schema. A
    container supplied by the caller takes precedence over image information
    in that file, which lets release automation embed an immutable digest.
    """
    from q2galaxy.api import template_builtins_iter, template_plugin_iter

    distributions = _load_config(config)
    yield from _prepare_output_iter(output, clean)

    tools_dir = os.path.join(output, _TOOLS_DIR)
    collections_dir = os.path.join(output, _COLLECTIONS_DIR)
    plugin_manager = sdk.PluginManager()
    distro_names = set()

    for distro in distributions:
        if not isinstance(distro, dict):
            raise ValueError("Each distribution must be a mapping.")
        name = distro.get('name')
        description = distro.get('description')
        if not isinstance(name, str) or not isinstance(description, str):
            raise ValueError(
                "Each distribution requires string name and description "
                "fields.")
        if name in distro_names:
            raise ValueError(
                f"Distribution {name!r} is defined more than once.")
        distro_names.add(name)

        categories = _as_categories(
            distro.get('default_categories'), f"Distribution {name!r}")
        metapackage, image = _environment_for(distro, container)
        dependencies = []

        yield from template_builtins_iter(
            tools_dir, distro=name, metapackage=metapackage,
            container=image)
        builtin = _builtin_shed(
            name, categories, owner, repository_url, repository_branch)
        builtin_dir = os.path.join(tools_dir, builtin['suite']['name'])
        yield from _ensure_gitkeep_iter(
            os.path.join(builtin_dir, 'test-data'))
        yield from _write_yaml_iter(
            builtin, os.path.join(builtin_dir, '.shed.yml'))
        dependencies.append(builtin)

        plugin_definitions = distro.get('plugins')
        if plugin_definitions is None:
            plugin_definitions = [
                {'id': plugin.id}
                for plugin in sorted(plugin_manager.plugins.values(),
                                     key=lambda plugin: plugin.id)
                if plugin.actions
            ]
        if not isinstance(plugin_definitions, list):
            raise ValueError(
                f"Distribution {name!r} plugins must be a list.")

        for raw_plugin in plugin_definitions:
            definition = _plugin_definition(raw_plugin)
            plugin = plugin_manager.get_plugin(id=definition['id'])
            plugin_categories = _as_categories(
                definition.get('categories', categories),
                f"Plugin {plugin.id!r}")

            yield from template_plugin_iter(
                plugin, tools_dir, metapackage=metapackage,
                container=image)
            shed = _plugin_shed(
                plugin, plugin_categories, owner, repository_url,
                repository_branch)
            suite_dir = os.path.join(tools_dir, shed['suite']['name'])
            yield from _ensure_gitkeep_iter(
                os.path.join(suite_dir, 'test-data'))
            yield from _write_yaml_iter(
                shed, os.path.join(suite_dir, '.shed.yml'))
            dependencies.append(shed)

        collection = _collection_shed(distro, dependencies, owner)
        collection_dir = os.path.join(
            collections_dir, collection['suite']['name'])
        os.makedirs(collection_dir, exist_ok=True)
        yield from _write_yaml_iter(
            collection, os.path.join(collection_dir, '.shed.yml'))


def template_distribution(config, output, container=None, owner='q2d2',
                          repository_url=(
                              'https://github.com/qiime2/galaxy-tools'),
                          repository_branch='main', clean=False):
    for _ in template_distribution_iter(
            config, output, container=container, owner=owner,
            repository_url=repository_url,
            repository_branch=repository_branch, clean=clean):
        pass
