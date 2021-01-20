import json

import click

import qiime2.sdk as sdk

from q2galaxy.core.driver import action_runner, builtin_runner, get_version
from q2galaxy.api import template_plugin_iter, template_all_iter
# from q2galaxy.core.templating import template_builtins
from q2galaxy.core.util import get_mystery_stew

_OUTPUT_DIR = click.Path(file_okay=False, dir_okay=True, exists=True)


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
    # template_builtins()
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin)
    for status in template_plugin_iter(plugin, output):
        line = json.dumps(status)
        if status['status'] == 'error':
            click.secho(line, fg='red', err=True)
        elif status['status'] == 'created':
            click.secho(line, fg='green')
        else:
            click.secho(line, fg='yellow')


@template.command()
@click.argument('output', type=_OUTPUT_DIR)
def all(output):
    # template_builtins()
    for status in template_all_iter(output):
        line = json.dumps(status)
        if status['status'] == 'error':
            click.secho(line, fg='red', err=True)
        elif status['status'] == 'created':
            click.secho(line, fg='green')
        else:
            click.secho(line, fg='yellow')


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

    # Something to do with jsonizing strings kinda butchers them. For
    # instance, the where clause from filter-table filter-samples in moving
    # pictures goes from
    # "[body-site]='gut'"
    # to
    # __dq____ob__body-site__cb__=__sq__gut__sq____dq__.
    # This obviously needs to be undone at some point for the  query to
    # actually work. This is probably not the way to do it. I don't know much
    # about json, but I can probably find a cleaner way to undo this
    for key, value in config.items():
        if type(value) == str:
            config[key] = value.replace('__sq__', "'").replace('__dq__', '"') \
                .replace('__ob__', '[').replace('__cb__', ']')

    if plugin == 'builtin':
        builtin_runner(action, config)
    else:
        action_runner(plugin, action, config)


@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    print('%s version %s' % (plugin, get_version(plugin)))


if __name__ == '__main__':
    root()
