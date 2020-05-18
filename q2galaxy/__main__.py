import json

import click

import qiime2.sdk as sdk

from q2galaxy.core.driver import action_runner, get_version
from q2galaxy.api import template_plugin_iter, template_all_iter


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
def tests(output):
    pass


@root.command()
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs', type=click.Path(file_okay=True, dir_okay=False,
                                          exists=True))
def run(plugin, action, inputs):
    with open(inputs, 'r') as fh:
        config = json.load(fh)
    action_runner(plugin, action, config)


@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    print('%s version %s' % (plugin, get_version(plugin)))


if __name__ == '__main__':
    root()
