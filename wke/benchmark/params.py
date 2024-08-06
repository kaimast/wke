''' This is part of the benchmark scripts. See __init__.py for more details. '''

# pylint: disable=too-few-public-methods,fixme,too-many-arguments

from typing import Any
from copy import deepcopy

class ParameterError(Exception):
    ''' Errors generated while dealing with experiment parameters '''

class Parameter:
    ''' Describes a parameter that can be configured / is configured during an experiment run '''

    def __init__(self, name: str, config):
        if isinstance(config, Parameter):
            self._name = config.name
            self._default = config.default_value
            self._value = config.value
        elif isinstance(config, dict):
            if "default" not in config:
                raise ParameterError(f'Parameter "{name}" is missing default value')
            assert "default" in config

            self._name = name
            self._default = config["default"]
            self._value = config["default"]

            if "about" in config:
                self._about = config["about"]
            else:
                print(f'No description given for parameter "{name}". '
                       'Add an "about"-field to fix this.')
                self._about = "No description."
        else:
            print(f'Parameter "{name}" is using old format. '
                  'Please define a dict with "default" and "about" instead.')
            self._name = name
            self._default = config
            self._value = config
            self._about = "No description."

    @property
    def name(self):
        ''' The name of this parameter '''
        return self._name

    @property
    def default_value(self):
        ''' The default value to use if nothing specified by the experiment '''
        return self._default

    @property
    def value(self):
        ''' The value this parameter is (currently) set to '''
        return self._value

    @value.setter
    def value(self, new_val):
        ''' Sets the value of this parameter '''
        if self.type == bool:
            value = value.lower() == 'true' or value == '1'
        elif self.type in [int, float]:
            # Allow simple integer/float conversion
            value = self.type(new_val)
        elif not isinstance(new_val, self.type):
            raise ParameterError(
                f'Cannot set parameter "{self.name}" to `{new_val}`: '
                f'Incompatible type. '
                f'Default type is {self.type_name} (value=`{self.default_value}`), '
                f'not {type(new_val).__name__}.')

        print(f'🔬 Setting "{self.name}" to value `{new_val}`, '
              f'was {self.value} (type: {self.type_name})')
        self._value = new_val

    @property
    def about(self):
        ''' Gives a description of what this parameter is used for '''
        return self._about

    @property
    def type(self):
        ''' Type to use for this config value. (Based on the default) '''
        return type(self._default)

    @property
    def type_name(self):
        ''' Human-readble name of the type of this config value. (Based on the default) '''
        return self.type.__name__


def parse_parameters(parameters: dict[str, Any]) -> dict[str, Parameter]:
    ''' Convert parameters defined by the user to our internal format '''
    result = {}
    for (name, param_config) in parameters.items():
        result[name] = Parameter(name, param_config)
    return result

def into_parameter_values(parameters: dict[str, Parameter]) -> dict[str, Any]:
    ''' Creates a dict of the current values of the parameters '''
    result = {}
    for (name, param) in parameters.items():
        result[name] = param.value
    return result

class LinearSteps:
    ''' Steps through a range '''

    def __init__(self, key: str, start: int, end: int, step_size: int):
        print(f'🔬 Stepping through values from {start} to {end}'
              f' for "{key}" (step_size: {step_size})')

        if step_size == 0:
            raise ParameterError("Step size cannot be zero")

        self._start = start
        self._pos = start
        self._end = end
        self._key = key
        self._reverse = start > end
        self._step_size = step_size

    def key(self) -> str:
        ''' Get the key associated with these steps '''
        return self._key

    def is_subparams(self):
        ''' These are basic steps subparameters '''
        return False

    def next(self) -> dict[str,int] | None:
        ''' Get the next value in the sequence '''

        # end is inclusive
        if self._reverse:
            if self._pos >= self._end:
                value = self._pos
                self._pos -= self._step_size
                return { self._key: value }
        else:
            if self._pos <= self._end:
                value = self._pos
                self._pos += self._step_size
                return { self._key: value }

        return None

    def is_reverse(self) -> bool:
        ''' Are we stepping through the line in reverse? '''
        return self._reverse

    def reset(self):
        ''' Reset steps for next iteration '''

        self._pos = self._start


class ExponentialSteps:
    ''' Steps through an exponentional range '''

    def __init__(self, key: str, base: int, start: int, end: int, step_size: int):
        print(f'🔬 Stepping through values from {base}^{start} to {base}^{end}'
              f' for "{key}" step_size: {step_size})')

        if step_size == 0:
            raise ParameterError("Step size cannot be zero")

        self._start = start
        self._pos = start
        self._base = base
        self._end = end
        self._key = key
        self._reverse = start > end
        self._step_size = step_size

    def key(self) -> str:
        ''' Get the key associated with these steps '''
        return self._key

    def is_subparams(self):
        ''' These are basic steps subparameters '''
        return False

    def next(self) -> dict[str,int] | None:
        ''' Get the next value in the sequence '''

        # end is inclusive
        if self._reverse:
            if self._pos >= self._end:
                value = self._base**self._pos
                self._pos -= self._step_size
                return { self._key: value }
        else:
            if self._pos <= self._end:
                value = self._base**self._pos
                self._pos += self._step_size
                return { self._key: value }

        return None

    def is_reverse(self) -> bool:
        ''' Are we stepping through the line in reverse? '''
        return self._reverse

    def reset(self):
        ''' Reset steps for next iteration '''

        self._pos = self._start

class ListSteps:
    ''' Steps through a list '''

    def __init__(self, key: str, steps, param_type):
        print(f'🔬 Stepping "{key}" through list {steps}')

        self._pos = 0
        self._steps = steps
        self._key = key
        self._param_type = param_type

    def key(self) -> str:
        ''' Get the key associated with these steps '''
        return self._key

    def is_subparams(self):
        ''' These are basic steps subparameters '''
        return False

    def next(self) -> dict[str, Any] | None:
        ''' Get the next value in the list '''

        if self._pos < len(self._steps):
            value = self._steps[self._pos]
            self._pos += 1
            return {self._key: self._param_type(value)}
        return None

    def reset(self):
        ''' Reset steps for next iteration '''

        self._pos = 0

class ParameterSet:
    '''
    Keeps track of a set of parameters: constants and variables
    ParameterSet allows to step through all experiment configurations
    '''

    def __init__(self, steps: list, variables: set[str], base_config: dict[str, Any]):
        if "sub-parameters" in variables:
            raise ParameterError('Variables cannot have special name "sub-parameters"')

        self._steps = steps
        self._variables = variables
        self._at_start = True
        self._at_end = False
        self._base_config = base_config

        # Maintain a dedicated "subconfiguration" for each steps
        # Makes it easier to track where changes are coming from
        self._sub_configs = []
        for step in self._steps:
            first_values = step.next()
            self._sub_configs.append(first_values)

    def get_variables(self) -> set[str]:
        ''' Get all variables for these Parameters '''
        return self._variables

    def current(self) -> dict[str, Any]:
        '''
        Get the current configuration from this set of parameters.
        Does not advance the position within the parameter set
        '''
        assert not self._at_end
        return self._generate_config()

    def next(self) -> dict[str, Any] | None:
        ''' Get the next configuration from this set of parameters '''

        # At end?
        if self._at_end:
            return None

        if len(self._steps) == 0:
            self._at_end = True
            return self._generate_config()

        if self._at_start:
            self._at_start = False
            return self._generate_config()

        pos = len(self._steps)-1
        changed = False

        while not changed:
            next_values = self._steps[pos].next()
            if next_values:
                changed = True
                self._sub_configs[pos] = next_values

            # At end?
            if not changed and pos == 0:
                self._at_end = True
                return None

            if not changed:
                # move up
                pos -= 1

        assert changed

        # If we moved up, move down again
        pos += 1
        while pos < len(self._steps):
            self._steps[pos].reset()
            next_values = self._steps[pos].next()
            assert next_values
            self._sub_configs[pos] = next_values
            pos += 1

        return self._generate_config()

    def _generate_config(self) -> dict[str, Any]:
        ''' Combines all subconfigs with the base config '''

        config = deepcopy(self._base_config)
        for sconfig in self._sub_configs:
            for key, param in sconfig.items():
                config[key] = param

        for key in config:
            #FIXME this should always be a parameter
            if isinstance(config[key], Parameter):
                config[key] = config[key].value

        return config

    def at_end(self) -> bool:
        ''' Is there another step or are we done? '''
        return self._at_end

    def reset(self):
        ''' Reset the parameters to initial state '''
        for (pos, step) in enumerate(self._steps):
            step.reset()
            self._sub_configs[pos] = step.next()
        self._at_start = True
        self._at_end = False

class SubparamSteps:
    ''' Steps through sets of parameters '''
    def __init__(self, subparams: list[ParameterSet]):
        self._subparams = subparams
        self._pos = 0

    def is_subparams(self):
        ''' These are subparameters '''
        return True

    def reset(self):
        ''' Reset steps to starting state '''
        self._pos = 0
        for subparams in self._subparams:
            subparams.reset()

    def get_variables(self) -> set[str]:
        ''' Get all variables for these subparameter steps '''
        result = set()
        for params in self._subparams:
            result.update(set(params.current().keys()))
        return result

    def next(self) -> dict[str, Any] | None:
        ''' Get the next configuration '''

        # Fetch from the current subparameters or move to the next
        while self._pos < len(self._subparams):
            config = self._subparams[self._pos].next()
            if config:
                return config
            self._pos += 1

        # At end
        assert self._pos == len(self._subparams)
        return None
