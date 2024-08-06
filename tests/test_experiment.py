''' This contains tests loading experiments from a toml file '''

# pylint: disable=missing-function-docstring

from wke.benchmark import parse_toml
from wke.benchmark.params import ParameterSet, parse_parameters, into_parameter_values

def test_parse_parameters():
    params_in = {
        "workload": "", "num-txns": 0, "worker-type": ""
    }
    params_out = into_parameter_values(parse_parameters(params_in))

    assert params_in == params_out

def test_basic():
    params = parse_parameters({
        "workload": "", "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/basic.toml", params)
    (steps, variables, _hill_climb, _name, num_iterations, _plots) = result

    assert len(steps) == 1
    assert variables == {"worker-type"}
    assert num_iterations == 2

    worker_type = steps[0]
    assert worker_type.next()["worker-type"] == "docker"
    assert worker_type.next()["worker-type"] == "open-lambda"
    assert worker_type.next()["worker-type"] == "faasm"
    assert worker_type.next() is None

    worker_type.reset()
    assert worker_type.next()["worker-type"] == "docker"

def test_exponential_steps():
    params = parse_parameters({
        "workload": "", "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/exponential-range.toml", params)
    (steps, variables, _hill_climb, _name, num_iterations, _plots) = result

    assert len(steps) == 1
    assert variables == {"num-txns"}
    assert num_iterations == 5

    worker_type = steps[0]
    assert worker_type.next()["num-txns"] == 100
    assert worker_type.next()["num-txns"] == 10000
    assert worker_type.next()["num-txns"] == 1000000
    assert worker_type.next()["num-txns"] == 100000000
    assert worker_type.next()["num-txns"] == 10000000000
    assert worker_type.next() is None

    worker_type.reset()
    assert worker_type.next()["num-txns"] == 100

def test_subparams():
    params = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/subparams.toml", params)
    (steps, variables, _hill_climb, _name, num_iterations, _plots) = result

    assert len(steps) == 1
    assert variables == {"worker-type", "num-clients", "num-txns"}
    assert num_iterations == 2

    config = steps[0].next()
    assert config == { 'num-clients': 10,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = steps[0].next()
    assert config == {'num-clients': 10,
                      'num-txns': 200, 'worker-type': 'docker' }

    config = steps[0].next()
    assert config == {'num-clients': 20,
                      'num-txns': 1000, 'worker-type': 'open-lambda' }

    config = steps[0].next()
    assert config == {'num-clients': 20,
                      'num-txns': 2000, 'worker-type': 'open-lambda' }

    config = steps[0].next()

    assert config is None

def test_subparams_nested():
    params = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/subparams_nested.toml", params)
    (steps, variables, _hill_climb, _name, _num_iterations, _plots) = result

    assert len(steps) == 1
    assert variables == {"worker-type", "num-clients", "num-txns"}

    config = steps[0].next()
    assert config == {'num-clients': 10,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = steps[0].next()
    assert config == {'num-clients': 10,
                      'num-txns': 200, 'worker-type': 'docker' }

    config = steps[0].next()
    assert config == {'num-clients': 20,
                      'num-txns': 1000, 'worker-type': 'open-lambda' }

    config = steps[0].next()

    assert config is None

def test_single_subparam():
    ''' Check that having only a single subparameter works'''

    params = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/single_subparam.toml", params)
    (steps, variables, _hill_climb, _name, _num_iteations, _plots) = result

    assert len(steps) == 1
    assert variables == {"worker-type", "num-clients", "num-txns"}

    config = steps[0].next()
    assert config == {'num-clients': 20,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = steps[0].next()
    assert config == {'num-clients': 100,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = steps[0].next()

    assert config is None

def test_subparams_and_range():
    base_config = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/subparams_and_range.toml", base_config)
    (steps, variables, _hill_climb, _name, _num_iterations, _plots) = result

    assert len(steps) == 2
    assert variables == {"worker-type", "num-clients", "num-txns"}

    params = ParameterSet(steps, variables, base_config)

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 200, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 100, 'worker-type': 'open-lambda' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 200, 'worker-type': 'open-lambda' }

    config = params.next()

    assert config is None

def test_subparams_and_range_flipped():
    ''' Same as 4 but order is flipped '''

    base_config = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/subparams_and_range_flipped.toml", base_config)
    (steps, variables, _hill_climb, _name, _num_iterations, _plots) = result

    assert len(steps) == 2
    assert variables == {"worker-type", "num-clients", "num-txns"}

    params = ParameterSet(steps, variables, base_config)

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 100, 'worker-type': 'open-lambda' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 200, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 200, 'worker-type': 'open-lambda' }

    config = params.next()

    assert config is None

def test_multi_subparams():
    base_config = parse_parameters({
        "workload": "", "num-clients": 0, "num-txns": 0, "worker-type": ""
    })
    result = parse_toml("./test-files/experiments/multi_subparams.toml", base_config)
    (steps, variables, _hill_climb, _name, _num_iterations, _plots) = result

    assert len(steps) == 2
    assert variables == {"worker-type", "num-clients", "num-txns"}

    params = ParameterSet(steps, variables, base_config)

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 100, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 10,
                      'num-txns': 200, 'worker-type': 'docker' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 100, 'worker-type': 'open-lambda' }

    config = params.next()
    assert config == { 'workload': 'hello-world', 'num-clients': 20,
                      'num-txns': 200, 'worker-type': 'open-lambda' }

    config = params.next()

    assert config is None
