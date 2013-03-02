import os
import re
import signal
from subprocess import Popen, PIPE

import sublime
import sublime_plugin

global buffer_state
global view_messages
global check_enabled

view_messages = {}
settings = sublime.load_settings("sublimetext_python_checker.sublime-settings")
check_enabled = settings.get('check_enabled', True)
buffer_state = {}


def set_status(view, state):
    buffer_state[view.id()] = state
    view.set_status('pthon_checker_status',
                    "pylint/pyflakes {0}".format('on' if state else 'off'))


class PythonCheckerCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global buffer_state
        state = not buffer_state.get(self.view.id(), False)

        if state:
            check_and_mark(self.view)
        else:
            self.view.erase_regions('python_checker_underlines')
            self.view.erase_regions('python_checker_outlines')
            self.view.erase_status("python_checker")

        set_status(self.view, state)


class PythonCheckerListener(sublime_plugin.EventListener):

    def is_active(self, view):
        global buffer_state
        return buffer_state.get(view.id(), False)

    def on_load(self, view):
        global check_enabled

        # enable/disable by default according to config
        set_status(view, check_enabled)
        if check_enabled:
            check_and_mark(view)

    def on_close(self, view):
        global buffer_state
        del buffer_state[view.id()]

    def on_activated(self, view):
        if self.is_active(view):
            signal.signal(signal.SIGALRM, lambda s, f: check_and_mark(view))
            signal.alarm(1)

    def on_deactivated(self, view):
        signal.alarm(0)

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
