import json

import click

from .run import action_runner, get_version

from .template import template_all


@click.group()
def root():
    pass


@root.group()
def template():
    pass


@template.command()
def plugin():
    pass


@template.command()
@click.argument('output', type=click.Path(file_okay=False, dir_okay=True,
                                          exists=True))
def all(output):
    template_all(output)


@template.command()
def tests():
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


