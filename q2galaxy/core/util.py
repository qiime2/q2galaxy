import xml.etree.ElementTree as xml

import qiime2.sdk as sdk


def XMLNode(name_, _text=None, **attrs):
    e = xml.Element(name_, attrs)
    if _text is not None:
        e.text = _text
    return e


def get_mystery_stew():
    from q2_mystery_stew.plugin_setup import create_plugin

    pm = sdk.PluginManager(add_plugins=False)

    test_plugin = create_plugin(ints=True)
    pm.add_plugin(test_plugin)

    return pm.get_plugin(id='mystery_stew')
