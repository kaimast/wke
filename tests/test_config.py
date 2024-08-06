'''
Unit tests for loading configurations
'''

# pylint: disable=missing-function-docstring,line-too-long

from wke.config import Configuration

def test_basic():
    config = Configuration('basic', base_path='test-files/configs')

    assert sorted(config.target_names) == sorted(['setup-rust', 'install-tokio', 'benchmark-tokio'])

    target = config.get_target("setup-rust")
    assert target.argument_names == ["channel", "profile"]
    assert target.get_default_value("channel") == "stable"

    target = config.get_target("install-tokio")
    assert target.command == '#! /bin/bash\necho "Just a test script"\n'

    target = config.get_target("benchmark-tokio")
    assert target.command == '#! /bin/env python3\nprint("Just another test script")\n'

    assert config.get_prelude_cmd('home-runner') == "export PATH=${PATH}:${HOME}/.local/bin:/usr/local/bin && export RUST_BACKTRACE=1 && "

def test_inherit():
    config = Configuration('inherit', base_path='test-files/configs')

    assert sorted(config.target_names) == sorted(['setup-rust', 'install-tokio', 'benchmark-tokio', 'install-smol', 'benchmark-smol'])

    # ensure arguments are overwritten
    target = config.get_target("setup-rust")
    assert target.argument_names == ["channel"]
    assert target.get_default_value("channel") == "nightly"

    # ensure we can still access the parents code properly
    target = config.get_target("install-tokio")
    assert target.command == '#! /bin/bash\necho "Just a test script"\n'

    target = config.get_target("benchmark-tokio")
    assert target.command == '#! /bin/env python3\nprint("Just another test script")\n'

    target = config.get_target("benchmark-smol")
    assert target.command == '#! /bin/env python3\nprint("Another script, but for smol")\n'

    assert config.get_prelude_cmd('home-runner') == "export PATH=${PATH}:${HOME}/.local/bin:/usr/local/bin && export RUST_BACKTRACE=1 && "
