# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json

import click

import qiime2.sdk as sdk

from q2galaxy.core.drivers import action_runner, builtin_runner, get_version
from q2galaxy.api import (template_plugin_iter, template_all_iter,
                          template_builtins_iter)
from q2galaxy.core.util import galaxy_ui_var, get_mystery_stew, galaxy_unesc

_OUTPUT_DIR = click.Path(file_okay=False, dir_okay=True, exists=True)


def _echo_status(status):
    line = json.dumps(status)
    if status['status'] == 'error':
        click.secho(line, fg='red', err=True)
    elif status['status'] == 'created':
        click.secho(line, fg='green')
    else:
        click.secho(line, fg='yellow')


@click.group()
def root():
    pass


@root.group()
def template():
    pass


@template.command()
@click.argument('plugin', type=str)
@click.argument('output', type=_OUTPUT_DIR)
def plugin(plugin, output):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin)
    for status in template_plugin_iter(plugin, output):
        _echo_status(status)


@template.command()
@click.argument('output', type=_OUTPUT_DIR)
def builtins(output):
    for status in template_builtins_iter(output):
        _echo_status(status)


@template.command()
@click.argument('output', type=_OUTPUT_DIR)
def all(output):
    for status in template_all_iter(output):
        _echo_status(status)


@template.command()
@click.argument('output', type=_OUTPUT_DIR)
@click.pass_context
def tests(ctx, output):
    test_plugin = get_mystery_stew()
    ctx.invoke(plugin, plugin=test_plugin.id, output=output)


@root.command()
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs', type=click.Path(file_okay=True, dir_okay=False,
                                          exists=True))
def run(plugin, action, inputs):
    with open(inputs, 'r') as fh:
        config = _clean_inputs(json.load(fh))
    if plugin == 'tools':
        builtin_runner(action, config)
    else:
        action_runner(plugin, action, config)


def _clean_inputs(inputs):
    cleaned = {}

    for key, value in inputs.items():
        if type(value) is list:
            input_ = []

            for elem in value:
                if type(elem) is dict:
                    input_.extend(_clean_inputs(elem).values())
                else:
                    input_.append(elem)

            if input_ == [None]:
                input_ = None

            cleaned[key] = input_
            continue
        # smash together nested dictionaries which are a consequence of
        # UI nesting
        if key.startswith(galaxy_ui_var()):
            if type(value) is dict:
                cleaned.update(_clean_inputs(value))
            continue
        if type(value) == str:
            # Galaxy seems to escape certain strings. For instance, the where
            # clause from filter-table filter-samples in moving pictures goes
            # from "[body-site]='gut'"
            # to "__dq____ob__body-site__cb__=__sq__gut__sq____dq__".
            # This needs to be undone, so we replace that here:
            cleaned[key] = galaxy_unesc(value)
        else:
            cleaned[key] = value
    return cleaned


@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    print('%s version %s' % (plugin, get_version(plugin)))


if __name__ == '__main__':
    root()
