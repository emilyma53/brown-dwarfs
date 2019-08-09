# -*- coding: utf-8 -*-
"""Navigator Exceptions and Exception handling module."""

# Standard library imports
from traceback import format_exc


def display_qt_error_box(error, traceback):
    """Display a Qt styled error message box."""
    from anaconda_navigator.widgets.dialogs import MessageBoxError
    text = (
        'An unexpected error occurred on Navigator start-up<br>'
        '{error}'.format(error=error)
    )
    trace = '{trace}'.format(trace=traceback)
    print(text)
    print(trace)
    msg_box = MessageBoxError(
        title='Navigator Start Error',
        text=text,
        error=trace,
        report=False,  # Disable reporting on github
        learn_more=None,
    )
    msg_box.setFixedWidth(600)
    return msg_box.exec_()


def display_browser_error_box(error, traceback):
    """Display a new browser window with an error description."""
    template = '''
    <html>
    <head>
      <title>Navigator Error</title>
    </head>
    <body>
      <div>
        <h1>Navigator Error</h1>
        <p>An unexpected error occurred on Navigator start-up</p>
        <h2>Report</h2>
        <p>Please report this issue in the anaconda
          <a href="https://github.com/continuumio/anaconda-issues">
            issue tracker
          </a>
        </p>
      </div>
      <div>
        <h2>Main Error</h2>
        <p><pre>{error}</pre></p>
        <h2>Traceback</h2>
        <p><pre>{trace}</pre></p>
      </div>
    </body>
    </html>
    '''
    try:
        from urllib import pathname2url  # Python 2.x
    except Exception:
        from urllib.request import pathname2url  # Python 3.x

    import tempfile
    temppath = tempfile.mktemp(suffix='.html')
    with open(temppath, 'w') as f:
        f.write(template.format(error=error, trace=traceback))

    url = 'file:{}'.format(pathname2url(temppath))

    import webbrowser
    webbrowser.open_new_tab(url)


def exception_handler(func, *args, **kwargs):
    """Handle global application exceptions and display information."""
    try:
        return_value = func(*args, **kwargs)
        if isinstance(return_value, int):
            return return_value
    except Exception as e:
        return handle_exception(e)


def try_func(func, *args, **kwargs):
    try:
        value = func(*args, **kwargs)
        return value
    except Exception as e:
        return handle_exception(e)


def handle_exception(error):
    """This will provide a dialog for the user with the error found."""
    traceback = format_exc()

    # Try using a Qt message box, if that fails
    try:
        display_qt_error_box(error, traceback)
    except Exception:
        # If that fails try to write a temp html file
        try:
            display_browser_error_box(error, traceback)
        except Exception:
            print(traceback)
