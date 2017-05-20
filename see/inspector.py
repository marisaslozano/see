"""
Object inspector.

"""
import inspect
import sys
import textwrap

from . import output, term, tools
from .exceptions import SeeError
from .features import FEATURES, PY3


class DefaultArg(object):
    """
    A global instance of this class is used as the default argument to
    :func:`see.see`. This allows for a distinction between calling ``see()``
    without arguments and calling it with a falsey argument like ``see(None)``.
    """
    def __repr__(self):
        return 'anything'


DEFAULT_ARG = DefaultArg()


class Namespace(object):
    """
    An object that provides attribute access to its namespace.

    See also: ``types.SimpleNamespace`` in Python 3.
    """
    def __init__(self, namespace):
        self.__dict__.update(namespace)


class SeeResult(tuple):
    """
    Tuple-like output with a pretty string representation.
    """
    def __new__(cls, actions=None):
        return tuple.__new__(cls, actions or [])

    def __repr__(self):
        col_width = output.column_width(self)
        padded = [output.justify_token(tok, col_width) for tok in self]

        ps1 = getattr(sys, 'ps1', None)
        if ps1:
            get_len = output.display_len if PY3 else len
            indent = ' ' * get_len(ps1)
        else:
            indent = '    '

        return textwrap.fill(''.join(padded), term.line_width(),
                             initial_indent=indent,
                             subsequent_indent=indent)


# Get all the 'is' functions from the inspect module.
INSPECT_FUNCS = tuple((name, getattr(inspect, name))
                      for name in dir(inspect) if name.startswith('is'))


def see(obj=DEFAULT_ARG, pattern=None, r=None):
    """
    Inspect an object. Like the ``dir()`` builtin, but easier on the eyes.

    Keyword arguments (all optional):

    * ``obj`` -- the object to be inspected. If this is omitted, the objects
      in the current scope are shown instead.

    * ``pattern`` -- filter the results with a shell-style search pattern
      (e.g. ``'*len*'``).

    * ``r`` -- filter the results with a regular expression
      (e.g. ``'get|set'``).

    Some special symbols are included in the output:

    ``()``
        | Object is a function or may be called like a function.
        | Example: ``obj()``
    ``.*``
        | Object implements ``__getattr__``, so it may allow you to access
          attributes that are not defined.
        | Example: ``obj.anything``.
    ``[]``
        | Object supports the ``[]`` syntax.
        | Example: ``obj[index]``
    ``with``
        | Object can be used in a ``with`` statement.
        | Example: ``with obj as target``
    ``in``
        | Object supports the ``in`` operator.
        | Example: ``for item in obj``
    ``+``, ``-``, ``*``, etc.
        | Object supports these arithmetic operations.
        | Example: ``obj1 + obj2``
    ``+obj``, ``-obj``
        | Object supports the unary arithmetic operators ``+`` (positive)
          and ``-`` (negative) respectively.
        | Example: ``+1``, ``-1``
    ``~``
        | Object supports the bitwise invert operator ``~``.
        | Example: ``~1``

    The result is displayed in columns of text in the interpreter. It can also
    be accessed as a tuple of strings. For example::

        >>> result = see(obj)
        >>> print(result[0])  # print the first entry
        >>> for string in result:  # iterate over the results
        ...     print(string)

    """
    use_locals = obj is DEFAULT_ARG

    if use_locals:
        # Get the local scope from the caller's stack frame.
        # Typically this is the scope of an interactive Python session.
        obj = Namespace(inspect.currentframe().f_back.f_locals)

    actions = []
    attrs = dir(obj)

    if not use_locals:

        for name, func in INSPECT_FUNCS:
            if func(obj):
                actions.append(name)

        for feature in FEATURES:
            if feature.match(obj, attrs):
                actions.append(feature.symbol)

    for attr in filter(lambda a: not a.startswith('_'), attrs):
        try:
            prop = getattr(obj, attr)
        except (AttributeError, Exception):
            prop = SeeError()
        action = output.display_name(name=attr, obj=prop, local=use_locals)
        actions.append(action)

    if pattern is not None:
        actions = tools.filter_wildcard(actions, pattern)

    if r is not None:
        actions = tools.filter_regex(actions, r)

    return SeeResult(actions)
