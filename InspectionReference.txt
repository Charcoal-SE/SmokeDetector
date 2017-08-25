*** This document details the different suppressed Code Inspections for PyCharm IDE in this project.

PyBroadException: This suppresses the "Overly broad exception" warning message in PyCharm IDE.  This is normally
triggered by `except:` or `except Exception` where it catches all exceptions instead of the bare minimum needed
to be captured.

PyMissingTypeHints: This suppresses the warning about type hints not being defined for a given function.

PyClassHasNoInit: In Python theory, any user-made classes should have an `__init__` so when the class is called
it can be initialized.  This is fine, however it doesn't apply for some cases where we don't actually *call*
the class itself.  This suppresses the warnings about missing __init__ for a given class.

PyPackageRequirements: For every `import` statement that doesn't pull in from the standard libraries, the package
being imported should be specified in the requirements.txt file.  There are cases, however, where a module name
for import is an alias of another, and therefore IDEs don't always pick up on that.  This suppresses the error
alerts about something not being in the package requirements.

PyProtectedMember: For any call to a class or object, when someone reaches into the class and does something like
`class._function()`, the underscore before it indicates a 'protected' member of that class.  The warning thrown
in PyCharm indicates that we're accessing a protected member and we may run into undesired behavior.  This
suppresses that warning.

PyUnresolvedReferences: This error-level alert indicates that we're referencing something that isn't actually
defined in the parent object.  With certain types of objects, this warning auto-suppresses, but with others it
doesn't.  This suppresses the notice about this.

PyUnusedLocal: This is a note that a variable is defined but not used in a given local-scope for a function. This
suppresses the notice.

PyTypeChecker: Part of type hinting is to tell the IDE what types are expected.  When a type being passed by the
code doesn't match the specified type hint, this throws an error alert in code inspection indicating there's a
type mismatch.  Sometimes these're bugs in PyCharm, sometimes they're coder errors, but this suppresses the alert.

PyIncorrectDocstring: Where we use strings, we sometimes have """ around them.  This is used only for docstrings,
and if it doesn't fit into the accepted format of docstrings, this error triggers.  This suppresses that inspection.

PyDeprecation:  This is a warning about a module or function being deprecated but not removed from the Python
codebase.  This suppresses the deprecated function / package warnings.

PyCompatibility:  This identifies compatibility issues between different Python versions and the code being used.
teward currently checks against 3.5 and 3.6.  This suppresses the compatibility notices.

PyRedundantParentheses: This suppresses warnings about unnecessary parentheses.  For example: `if (foo == bar)`
can be rewritten without the parentheses to be `if foo == bar`.  This suppresses warnings about redundant parentheses.

PyUnboundLocalVariable: This error warning comes up when we are potentially calling a variable that has not yet
been declared.  This suppresses that warning.

PyShadowing[Builtins|Names]: This indicates when we shadow other variable names, or built-ins, in Python.
As such, this warns about shadowing other names that already exist, or shadowing built-ins which should not
be shadowed.

PyRedeclaration: This indicates a case where we already declared a variable and then are *redeclaring* it.
Usually this shouldn't be done, so it gives a warning because we don't want odd behavior.  This suppresses the
warnings for this case.

PyPep8Naming: This stylistic warning triggers when a function or variable name violates PEP8 naming standards.
This suppresses the warnings.

PyMethodParameters: This warning happens when the method parameters aren't used anywhere.  We have a few cases
of this, and this suppresses this warning.