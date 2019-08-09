# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Launch applications utilities."""

# yapf: disable

# Standard library imports
import codecs
import glob
import os
import subprocess

# Local imports
from navigator_updater.config import (HOME_PATH, LAUNCH_SCRIPTS_PATH, LINUX,
                                      MAC, WIN)
from navigator_updater.utils.logs import logger

# yapf: enable

if WIN:
    import ctypes


def get_scripts_path(
    root_prefix, prefix, default_scripts_path=LAUNCH_SCRIPTS_PATH
):
    """Return the launch scripts path."""
    # Normalize slashes
    scripts_path = default_scripts_path
    root_prefix = root_prefix.replace('\\', '/')
    prefix = prefix.replace('\\', '/')
    default_scripts_path = default_scripts_path.replace('\\', '/')
    if root_prefix != prefix:
        scripts_path = os.path.join(
            default_scripts_path, prefix.split('/')[-1]
        )
    return scripts_path


def get_quotes(prefix):
    """Return quotes if needed for spaces on prefix."""
    return '"' if ' ' in prefix and '"' not in prefix else ''


def remove_package_logs(
    root_prefix, prefix, default_scripts_path=LAUNCH_SCRIPTS_PATH
):
    """Try to remove output, error logs for launched applications."""
    scripts_p = get_scripts_path(
        root_prefix, prefix, default_scripts_path=default_scripts_path
    )
    if not os.path.isdir(scripts_p):
        return

    scripts_p = scripts_p if scripts_p[-1] == os.sep else scripts_p + os.sep
    files = glob.glob(scripts_p + '*.txt')
    for file_ in files:
        log_path = os.path.join(scripts_p, file_)
        try:
            os.remove(log_path)
        except Exception:
            pass


def get_package_logs(
    package_name,
    prefix=None,
    root_prefix=None,
    id_=None,
    default_scripts_path=LAUNCH_SCRIPTS_PATH,
):
    """Return the package log names for launched applications."""
    scripts_path = get_scripts_path(
        root_prefix, prefix, default_scripts_path=default_scripts_path
    )
    if os.path.isdir(scripts_path):
        files = os.listdir(scripts_path)
    else:
        files = []

    if id_ is None:
        for i in range(1, 10000):
            stdout_log = "{package_name}-out-{i}.txt".format(
                package_name=package_name, i=i
            )
            stderr_log = "{package_name}-err-{i}.txt".format(
                package_name=package_name, i=i
            )
            if stdout_log not in files and stderr_log not in files:
                id_ = i
                break
    else:
        stdout_log = "{package_name}-out-{i}.txt".format(
            package_name=package_name, i=id_
        )
        stderr_log = "{package_name}-err-{i}.txt".format(
            package_name=package_name, i=id_
        )

    if prefix and root_prefix:
        stdout_log_path = os.path.join(scripts_path, stdout_log)
        stderr_log_path = os.path.join(scripts_path, stderr_log)
    else:
        stdout_log_path = stdout_log
        stderr_log_path = stderr_log

    return stdout_log_path, stderr_log_path, id_


def is_program_installed(basename):
    """
    Return program absolute path if installed in PATH.

    Otherwise, return None
    """
    for path in os.environ["PATH"].split(os.pathsep):
        abspath = os.path.join(path, basename)
        if os.path.isfile(abspath):
            return abspath


def create_app_run_script(
    command,
    package_name,
    prefix,
    root_prefix,
    suffix,
    default_scripts_path=LAUNCH_SCRIPTS_PATH,
):
    """Create the script to run the application and activate th eenvironemt."""
    # qtpy is adding this to env on startup and this is messing qtconsole
    # and other apps on other envs with different versions of QT
    if 'QT_API' in os.environ:
        os.environ.pop('QT_API')

    package_name = package_name or 'app'

    scripts_path = get_scripts_path(
        root_prefix, prefix, default_scripts_path=default_scripts_path
    )

    if not os.path.isdir(scripts_path):
        os.makedirs(scripts_path)
    fpath = os.path.join(scripts_path, '{0}.{1}'.format(package_name, suffix))

    # Try to clean log files
    remove_package_logs(root_prefix=root_prefix, prefix=prefix)

    # Create the launch script
    if WIN:
        codepage = str(ctypes.cdll.kernel32.GetACP())
        cp = 'cp' + codepage
        with codecs.open(fpath, "w", cp) as f:
            f.write(command)
    else:
        # Unicode is disabled on unix systems until properly fixed!
        # Using normal open and not codecs.open
        # cp = 'utf-8'
        with open(fpath, "w") as f:
            f.write(command)

    os.chmod(fpath, 0o777)

    return fpath


def get_command_on_win(
    prefix,
    command,
    package_name,
    root_prefix,
    environment=None,
    default_scripts_path=LAUNCH_SCRIPTS_PATH,
    non_conda=False,
):
    """Generate command to run on win system and enforce env activation."""
    stdout_log_path, stderr_log_path, id_ = get_package_logs(
        package_name,
        root_prefix=root_prefix,
        prefix=prefix,
        default_scripts_path=default_scripts_path,
    )
    quote = get_quotes(prefix)
    quote_logs = get_quotes(stdout_log_path)
    quoted_command = parse_command_args(command, prefix)

    codepage = str(ctypes.cdll.kernel32.GetACP())
    # Call is needed to avoid the batch script from closing after running
    # the first (environment activation) line
    prefix = prefix.replace('\\', '/')
    cmd = (
        'chcp {CODEPAGE}\n'
        'call {QUOTE}{CONDA_ROOT_PREFIX}/Scripts/activate{QUOTE} '
        '{QUOTE}{CONDA_PREFIX}{QUOTE}\n'
        '{COMMAND} '
        '>{QUOTE_LOGS}{OUT}{QUOTE_LOGS} 2>{QUOTE_LOGS}{ERR}{QUOTE_LOGS}\n'
    ).format(
        CODEPAGE=codepage,
        CONDA_PREFIX=prefix,
        CONDA_ROOT_PREFIX=root_prefix,  # Activate only exist now on root env
        COMMAND=quoted_command,
        QUOTE=quote,
        QUOTE_LOGS=quote_logs,
        OUT=stdout_log_path,
        ERR=stderr_log_path,
    )
    cmd = cmd.replace('/', '\\')  # Turn slashes back to windows standard

    suffix = 'bat'
    fpath = create_app_run_script(
        cmd,
        package_name,
        prefix,
        root_prefix,
        suffix,
    )
    CREATE_NO_WINDOW = 0x08000000
    popen_dict = {
        'creationflags': CREATE_NO_WINDOW,
        'shell': True,
        'cwd': HOME_PATH,
        'env': environment,
        'args': fpath,
        'id': id_,
        'cmd': cmd,
    }
    return popen_dict


def parse_command_args(command, prefix):
    new_args = []
    for cmd in command:
        if cmd == 'open':
            new_args.append('open')
        elif '${PREFIX}' in cmd:
            new_arg = cmd.replace('${PREFIX}', prefix)
            new_args.append(new_arg)
        else:
            new_args.append(cmd)

    # Add quotes to command
    final_args = []
    for new_arg in new_args:
        arg_quotes = get_quotes(new_arg)
        new_arg = arg_quotes + new_arg + arg_quotes
        final_args.append(new_arg)

    quoted_command = ' '.join(final_args)
    return quoted_command


def get_command_on_unix(
    prefix,
    command,
    package_name,
    root_prefix,
    environment=None,
    default_scripts_path=LAUNCH_SCRIPTS_PATH,
    non_conda=False,
):
    """Generate command to run on unix system and enforce env activation."""
    quoted_command = parse_command_args(command, prefix)
    stdout_log_path, stderr_log_path, id_ = get_package_logs(
        package_name,
        root_prefix=root_prefix,
        prefix=prefix,
        default_scripts_path=default_scripts_path,
    )
    quote = get_quotes(prefix)
    quote_logs = get_quotes(stdout_log_path)

    cmd = (
        '#!/usr/bin/env bash\n'
        'source {QUOTE}{CONDA_ROOT_PREFIX}/bin/activate{QUOTE} '
        '{QUOTE}{CONDA_PREFIX}{QUOTE}\n'
        '{COMMAND} '
        '>{QUOTE_LOGS}{OUT}{QUOTE_LOGS} 2>{QUOTE_LOGS}{ERR}{QUOTE_LOGS}\n'
    ).format(
        CONDA_PREFIX=prefix,
        CONDA_ROOT_PREFIX=root_prefix,  # Activate only exist now on root env
        COMMAND=quoted_command,
        QUOTE=quote,
        QUOTE_LOGS=quote_logs,
        OUT=stdout_log_path,
        ERR=stderr_log_path,
    )
    suffix = 'sh'
    fpath = create_app_run_script(
        cmd,
        package_name,
        prefix,
        root_prefix,
        suffix,
        default_scripts_path=default_scripts_path,
    )
    popen_dict = {
        'shell': False,
        'cwd': HOME_PATH,
        'env': environment,
        'args': fpath,
        'id': id_,
        'cmd': cmd,
    }
    return popen_dict


def launch(
    prefix,
    command,
    leave_path_alone,
    working_directory=HOME_PATH,
    package_name=None,
    root_prefix=None,
    environment=None,
    non_conda=False,
):
    """Handle launching commands from projects."""
    logger.debug(str((prefix, command)))
    new_command = []
    for cmd in command:
        new_cmd = cmd.replace('\\', '/')
        new_command.append(new_cmd)
    prefix = prefix.replace('\\', '/')
    root_prefix = root_prefix.replace('\\', '/')

    pid = -1

    # if os.name == 'nt' and not leave_path_alone:
    #     command = command.replace('/bin', '/Scripts')

    if MAC or LINUX:
        popen_dict = get_command_on_unix(
            prefix=prefix,
            command=new_command,
            package_name=package_name,
            root_prefix=root_prefix,
            environment=environment,
            non_conda=non_conda,
        )

    else:
        popen_dict = get_command_on_win(
            prefix=prefix,
            command=new_command,
            package_name=package_name,
            root_prefix=root_prefix,
            environment=environment,
            non_conda=non_conda,
        )

    args = popen_dict.pop('args')
    id_ = popen_dict.pop('id')
    cmd = popen_dict.pop('cmd')
    cmd
    p = subprocess.Popen(args, **popen_dict).pid
    pid = p, id_
    return pid
