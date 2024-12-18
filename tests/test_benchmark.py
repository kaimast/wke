'''
Unit tests for the benchmark scripts
'''

# pylint: disable=missing-function-docstring

from wke.benchmark.params import ParameterSet, LinearSteps, ListSteps, SubparamSteps


def test_linear_steps():
    steps = LinearSteps("foo", 2, 6, 3)

    assert steps.next()["foo"] == 2
    assert steps.next()["foo"] == 5
    assert steps.next() is None


def test_reverse_linear_steps():
    steps = LinearSteps("foo", 6, 2, 3)

    assert steps.is_reverse()

    assert steps.next()["foo"] == 6
    assert steps.next()["foo"] == 3
    assert steps.next() is None


def test_list_steps():
    steps = ListSteps("foo", ["bar", "baz"], str)

    assert steps.next()["foo"] == 'bar'
    assert steps.next()["foo"] == 'baz'
    assert steps.next() is None


def test_params():
    variables = ["foo", "bar"]

    step1 = LinearSteps("foo", 2, 6, 3)
    step2 = ListSteps("bar", ['x', 'z'], str)
    default_config = {"foo": 9, "bar": "a"}

    params = ParameterSet([step1, step2], variables, default_config)

    assert not params.at_end()

    config = params.next()
    assert config["foo"] == 2
    assert config["bar"] == 'x'

    config = params.next()
    assert config["foo"] == 2
    assert config["bar"] == 'z'

    config = params.next()
    assert config["foo"] == 5
    assert config["bar"] == 'x'

    config = params.next()
    assert config["foo"] == 5
    assert config["bar"] == 'z'

    config = params.next()
    assert config is None
    assert params.at_end()


def test_subparams():
    variables = ["foo", "bar"]
    default_config = {"foo": 9, "bar": "q"}
    step1 = LinearSteps("foo", 2, 6, 3)
    params1 = ParameterSet([step1], variables, {})

    step2 = ListSteps("bar", ['x', 'z'], str)
    params2 = ParameterSet([step2], variables, {})

    ssteps = SubparamSteps([params1, params2])
    params = ParameterSet([ssteps], variables, default_config)

    # Here params1 overwrites 'foo'
    config = params.next()
    assert config["foo"] == 2
    assert config["bar"] == 'q'

    config = params.next()
    assert config["foo"] == 5
    assert config["bar"] == 'q'

    # Now params2 overwrites 'bar'
    config = params.next()
    assert config["foo"] == 9
    assert config["bar"] == 'x'

    config = params.next()
    assert config["foo"] == 9
    assert config["bar"] == 'z'

    config = params.next()
    assert config is None
    assert params.at_end()
