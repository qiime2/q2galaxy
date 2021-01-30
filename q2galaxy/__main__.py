import json

import click

import qiime2.sdk as sdk

from q2galaxy.core.drivers import action_runner, builtin_runner, get_version
from q2galaxy.api import (template_plugin_iter, template_all_iter,
                          template_builtins_iter)
from q2galaxy.core.util import get_mystery_stew, galaxy_unesc

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
def tools(output):
    for status in template_builtins_iter():
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
        config = json.load(fh)

    # Galaxy seems to escape certain strings. For instance, the where clause
    # from filter-table filter-samples in moving pictures goes from
    # "[body-site]='gut'"
    # to
    # __dq____ob__body-site__cb__=__sq__gut__sq____dq__.
    # This needs to be undone, so we replace that here:
    for key, value in config.items():
        if type(value) == str:
            config[key] = galaxy_unesc(value)

    if plugin == 'tools':
        builtin_runner(action, config)
    else:
        action_runner(plugin, action, config)


@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    print('%s version %s' % (plugin, get_version(plugin)))


if __name__ == '__main__':
    root()
