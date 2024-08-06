# pylint: disable=fixme,too-many-branches,too-many-locals,too-many-arguments

''' Helper methods for wke '''

def bash_wrap(cmds):
    ''' Turn a list of commands into a bash script '''
    return "#! /bin/bash\n" + ' && '.join(cmds)
