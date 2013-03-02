# Python PEP-8 and PyFlakes checker for SublimeText 2 editor

This project is a plugin for [SublimeText 2](http://www.sublimetext.com/2) text editor.
It checks all python files you opening and editing through two popular Python checkers - [pep8](http://pypi.python.org/pypi/pep8)
and [PyFlakes](http://pypi.python.org/pypi/pyflakes).

## Installation

Go to your Packages dir (Sublime Text 2 -> Preferences -> Browse Packages). Clone this repository into Packages subdirectory:

    git clone git://github.com/vorushin/sublimetext_python_checker.git

From SublimeText 2 -> Preferences -> Package Settings, select `sublime_python_checker`. Add something like this:

```
{
    "highlight_color": "keyword",
    "python_syntax_checkers": [
            ["/usr/bin/pep8", []],
            ["/usr/bin/pyflakes", []]
    ]
}
```
You should replace `keyword` with a theme style of your preference.

The first parameter in a `python_syntax_checkers` entry is the path to command, the second one an optional list of arguments. E.g. if you want to disable line length checking in pep8, you should set the second parameter to ['--ignore=E501'].

You can also set syntax checkers using sublimetext settings (per file, global,
per project, ...):
<pre>
    "settings":
    {
        "python_syntax_checkers":
        [
            ["/usr/bin/pep8", ["--ignore=E501,E128,E221"] ]
        ]
    }
</pre>

These will have precedence over plugin-level settings.

Restart SublimeText 2 and open some *.py file to see check results. You can see additional information in python console of your editor (go View -> Show Console).

## Why not sublimelint

Before creating this project I used [sublimelint](https://github.com/lunixbochs/sublimelint), which is multilanguage
checker/linter. I described pros and cons of both below.

### sublimelint
- can't use your Python version or your virtualenv
- don't check with pep8
- do checks on every edit
- do checks for Python (derivative of pyflakes), PHP, Perl, Ruby
- works on Windows/Linux/MacOSX

### sublimetext_python_checker
- can use your version of Python and your virtualenv
- do checks only on opening and saving files
- works only on Linux and Mac OS X
- checks only Python files
- checks with pep8 and pyflakes
- all this in a few screens of code
