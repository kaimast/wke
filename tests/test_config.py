'''
Unit tests for loading configurations
'''

from wke.config import Configuration


def test_basic():
    config = Configuration('basic', base_path='test-files/configs')

    assert sorted(config.target_names) == \
        sorted(['setup-rust', 'install-tokio', 'benchmark-tokio'])

    target = config.get_target("setup-rust")
    assert target.option_names == ["channel", "profile"]
    assert target.get_option('channel').choices == ['stable', 'nightly']
    assert target.get_option("channel").default_value == "stable"

    target = config.get_target("install-tokio")
    assert target.command == '#! /bin/bash\necho "Just a test script"\n'

    target = config.get_target("benchmark-tokio")
    assert target.command == '#! /bin/env python3\nprint("Just another test script")\n'

    expected = ("export PATH=${PATH}:${HOME}/.local/bin:/usr/local/bin && "
                "export RUST_BACKTRACE=1 && ")
    assert config.get_prelude_cmd('home-runner') == expected


def test_inherit():
    config = Configuration('inherit', base_path='test-files/configs')

    expected = sorted(['setup-rust', 'install-tokio', 'benchmark-tokio',
        'install-smol', 'benchmark-smol'])
    assert sorted(config.target_names) == expected

    # ensure options are overwritten
    target = config.get_target("setup-rust")
    assert target.option_names == ["channel"]
    assert target.get_option("channel").default_value == "nightly"

    # ensure we can still access the parents code properly
    target = config.get_target("install-tokio")
    assert target.command == '#! /bin/bash\necho "Just a test script"\n'

    target = config.get_target("benchmark-tokio")
    assert target.command == '#! /bin/env python3\nprint("Just another test script")\n'

    target = config.get_target("benchmark-smol")
    assert target.command == \
        '#! /bin/env python3\nprint("Another script, but for smol")\n'

    expected = ("export PATH=${PATH}:${HOME}/.local/bin:/usr/local/bin && "
                "export RUST_BACKTRACE=1 && ")
    assert config.get_prelude_cmd('home-runner') == expected
