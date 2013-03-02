import re
import signal
from subprocess import Popen, PIPE

import sublime
import sublime_plugin

global view_messages
global enabled_by_default

view_messages = {}
settings = sublime.load_settings("sublimetext_python_checker.sublime-settings")
enabled_by_default = settings.get('enabled_by_default', True)


def set_status(view, state):
    view.set_status('pthon_checker_status',
                    "pylint/pyflakes {0}".format('on' if state else 'off'))


class PythonCheckerListener(sublime_plugin.EventListener):

    def is_active(self, view):
        return view.settings().get('python_checking')

    def is_python_buffer(self, view):
        return 'python' in view.settings().get('syntax').lower()

    def on_toggle(self, view):
        state = view.settings().get('python_checking')

        set_status(view, state)

        if state:
            check_and_mark(view)
        else:
            view.erase_regions('python_checker_underlines')
            view.erase_regions('python_checker_outlines')
            view.erase_status("python_checker")

    def on_load(self, view):
        global enabled_by_default

        if not self.is_python_buffer(view):
            return

        # enable/disable by default according to config
        view.settings().set('python_checking', enabled_by_default)
        set_status(view, enabled_by_default)
        view.settings().add_on_change('python_checking',
                                      lambda: self.on_toggle(view))

        if enabled_by_default:
            signal.signal(signal.SIGALRM, lambda s, f: check_and_mark(view))
            signal.alarm(1)

    def on_post_save(self, view):
        if self.is_active(view):
            check_and_mark(view)

    def on_selection_modified(self, view):
        global view_messages

        if self.is_active(view):
            lineno = view.rowcol(view.sel()[0].end())[0]
            if view.id() in view_messages and lineno in view_messages[view.id()]:
                view.set_status('python_checker', view_messages[view.id()][lineno])
            else:
                view.erase_status('python_checker')


def check_and_mark(view):

    view_settings = view.settings()

    if not 'python' in view_settings.get('syntax').lower():
        return
    if not view.file_name():  # we check files (not buffers)
        return

    checkers = view_settings.get('python_syntax_checkers',
        settings.get('python_syntax_checkers', {}))

    messages = []
    for checker, args in checkers:
        checker_messages = []
        try:
            p = Popen([checker, view.file_name()] + args, stdout=PIPE,
                      stderr=PIPE)
            stdout, stderr = p.communicate(None)
            checker_messages += parse_messages(stdout)
            checker_messages += parse_messages(stderr)
            for line in checker_messages:
                print "[%s] %s:%s:%s %s" % (
                    checker.split('/')[-1], view.file_name(),
                    line['lineno'] + 1, line['col'] + 1, line['text'])
            messages += checker_messages
        except OSError:
            print "Checker could not be found:", checker

    outlines = [view.full_line(view.text_point(m['lineno'], 0))
                for m in messages]
    view.erase_regions('python_checker_outlines')
    view.add_regions('python_checker_outlines',
                     outlines,
                     settings.get('highlight_color', 'keyword'))

    underlines = []
    for m in messages:
        if m['col']:
            a = view.text_point(m['lineno'], m['col'])
            underlines.append(sublime.Region(a, a))

    view.erase_regions('python_checker_underlines')
    view.add_regions('python_checker_underlines',
                     underlines,
                     settings.get('highlight_color', 'keyword'))

    line_messages = {}
    for m in (m for m in messages if m['text']):
        if m['lineno'] in line_messages:
            line_messages[m['lineno']] += ';' + m['text']
        else:
            line_messages[m['lineno']] = m['text']

    global view_messages
    view_messages[view.id()] = line_messages


def parse_messages(checker_output):
    '''
    Examples of lines in checker_output

    pep8 on *nix
    /Users/vorushin/Python/answers/urls.py:24:80: E501 line too long \
    (96 characters)

    pyflakes on *nix
    /Users/vorushin/Python/answers/urls.py:4: 'from django.conf.urls.defaults \
    import *' used; unable to detect undefined names

    pyflakes, invalid syntax message (3 lines)
    /Users/vorushin/Python/answers/urls.py:14: invalid syntax
    dict_test = {key: value for (key, value) in [('one', 1), ('two': 2)]}
                                                                    ^

    pyflakes on Windows
    c:\Python26\Scripts\pildriver.py:208: 'ImageFilter' imported but unused
    '''

    pep8_re = re.compile(r'.*:(\d+):(\d+):\s+(.*)')
    pyflakes_re = re.compile(r'.*:(\d+):\s+(.*)')

    messages = []
    for i, line in enumerate(checker_output.splitlines()):
        if pep8_re.match(line):
            lineno, col, text = pep8_re.match(line).groups()
        elif pyflakes_re.match(line):
            lineno, text = pyflakes_re.match(line).groups()
            col = 1
            if text == 'invalid syntax':
                col = invalid_syntax_col(checker_output, i)
        else:
            continue
        messages.append({'lineno': int(lineno) - 1,
                         'col': int(col) - 1,
                         'text': text})

    return messages


def invalid_syntax_col(checker_output, line_index):
    '''
    For error messages like this:

    /Users/vorushin/Python/answers/urls.py:14: invalid syntax
    dict_test = {key: value for (key, value) in [('one', 1), ('two': 2)]}
                                                                    ^
    '''
    for line in checker_output.splitlines()[line_index + 1:]:
        if line.startswith(' ') and line.find('^') != -1:
            return line.find('^')
