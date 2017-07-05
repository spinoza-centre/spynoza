import nipype.pipeline as pe
from nipype.interfaces.utility import Function

# ToDo: not use a mutable argument for sg_args


def _check_if_iterable(to_iter, arg):

    if not isinstance(arg, list):
        arg = [arg] * len(to_iter)

    return arg

fix_iterable = pe.Node(Function(input_names=['to_iter', 'arg'], output_names='arg_fixed',
                                function=_check_if_iterable), name='fix_iterable')
