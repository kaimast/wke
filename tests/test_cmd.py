'''
Integration tests for the command line commands
'''

import json

from subprocess import call, check_output

CMD = ["python", "-m", "wke.bin.cmd"]


def call_cmd(args):
    return call(CMD + args)


def check_cmd_output(args):
    return check_output(CMD + args)


def test_run_all():
    res = call_cmd(["run", "basic", "all", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res == 0


def test_run_one():
    res = call_cmd(["run", "basic", "node2", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res == 0


def test_run_range():
    res = call_cmd(["run", "basic", "[1:3]", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res == 0


def test_run_invalid_selector():
    res = call_cmd(["run", "basic", "[", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res != 0


def test_run_invalid_range():
    res = call_cmd(["run", "basic", "[2:1]", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res != 0


def test_run_invalid_node():
    res = call_cmd(["run", "basic", "node_42", "install-tokio",
                    "--dry-run", "--cwd=test-files/configs"])
    assert res != 0


def test_show_config():
    output = check_cmd_output(["show-config", "basic", "--json",
                    "--cwd=test-files/configs"])
    res = json.loads(output)

    expected = {
        'default-prelude': 'home-runner',
        'ubuntu': {
            'required-packages': ['htop', 'nload']
        },
        'preludes': {
            'home-runner': "Sets up $PATH to point to ~/.local/bin",
        },
        'targets': {
            'install-packages': 'Install the required debian packages',
            'install-tokio': 'No description',
            'benchmark-tokio': 'No description',
            'setup-rust': 'Install the rust toolchain',
        }
    }

    assert res == expected


def test_show_config_verbose():
    output = check_cmd_output(["show-config", "basic", "--json",
                    "--cwd=test-files/configs", "--verbose"])
    res = json.loads(output)

    expected = {
        'default-prelude': 'home-runner',
        'ubuntu': {
            'required-packages': ['htop', 'nload']
        },
        'preludes': {
            'home-runner': "Sets up $PATH to point to ~/.local/bin",
        },
        'targets': {
            'install-packages': {
                'about': 'Install the required debian packages',
                'options': []
            },
            'install-tokio': {
                'about': 'No description',
                'options': []
            },
            'benchmark-tokio': {
                'about': 'No description',
                'options': [
                    {'name': 'num-operations', 'required': False,
                     'default-value': 10000}
                ]
            },
            'setup-rust': {
                'about': 'Install the rust toolchain',
                'options': [
                    {'name': 'channel', 'required': False, 'default-value': 'stable'},
                    {'name': 'profile', 'required': False, 'default-value': 'minimal'}
                ]
            }
        }
    }

    assert res == expected
