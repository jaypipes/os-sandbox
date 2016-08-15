# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import errno
import grp
import os
import pwd
import stat
import subprocess

import six


def get_current_groupname():
    """Returns the group name of the user currently executing the program."""
    return grp.getgrgid(os.getgid())[0]


def owned_by_current(path):
    """Returns True if the supplied path is owned by the current group,
    otherwise False.

    :param path: Pathname to check.
    """
    st = os.stat(path)
    return st.st_gid == os.getgid() and st.st_uid == os.getuid()


def is_writeable(path):
    """Returns True if the path is writeable by the current user and group,
    otherwise False.

    :param path: Pathname to check.
    """
    st = os.stat(path)
    return ((st.st_mode & (stat.S_IWGRP | stat.S_IWUSR))
            == (stat.S_IWGRP | stat.S_IWUSR))


def set_writeable(path):
    """Sets the path to be writeable by the current user and group.

    :param path: Pathname to modify.
    """
    st = os.stat(path)
    cur_st = st.st_mode
    try:
        os.chmod(path, cur_st | stat.S_IWGRP | stat.S_IWUSR)
    except OSError as err:
        if err.errno == errno.EPERM:
            # Need to sudo this up and grant group writeable
            args = ('sudo', 'chmod', 'g+rw,u+rw', path)
            subprocess.check_call(args)


def set_owner_current(path):
    """Recursively set ownership of supplied path to current user and group.

    :param path: Pathname to modify.
    """
    st = os.stat(path)
    owner_uid = os.getuid()
    group_gid = os.getgid()
    try:
        os.chown(path, owner_uid, group_gid)
    except OSError as err:
        if err.errno == errno.EPERM:
            # Need to sudo this up and grant group ownership
            args = ('sudo', 'chown', '-R',
                    '%d:%d' % (owner_uid, group_gid), path)
            subprocess.check_call(args)


def create_writeable_dir(path):
    """Creates the directory, making it group writeable and owned by the
    current group. If the current user doesn't have permissions to create the
    path, then we use sudo to escalate privileges.

    :param path: Pathname to modify.
    """
    try:
        os.mkdir(path, 0755)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EPERM):
            # Need to sudo this up and try again
            args = ('sudo', 'mkdir', path)
            subprocess.check_call(args)
            st = os.stat(path)
            owner_uid = os.getuid()
            group_gid = os.getgid()
            args = ('sudo', 'chown', '-R',
                    '%d:%d' % (owner_uid, group_gid), path)
            subprocess.check_call(args)
            set_writeable(path)
            

def ensure_state_dir(parsed_args):
    """Returns the state directory or raises an exception if it
    does not exist.

    :param parsed_args: Arguments returned from get_parser()
    :raises RuntimeError if the state directory doesn't exist or
            is not a directory.or the current group doesn't have
            write permissions on it
    :returns state directory for os-sandbox
    """
    state_dir = parsed_args.state_dir
    if not os.path.exists(state_dir):
        msg = ("State dir '{0}' doesn't exist. Please create it or run "
               "`os-sandbox setup [--state-dir]`.").format(state_dir)
        raise RuntimeError(msg)

    if not os.path.isdir(state_dir):
        msg = ("State dir '{0}' exists but is not a directory. "
               "Please use a different state directory.").format(state_dir)
        raise RuntimeError(msg)

    if not is_writeable(state_dir):
        msg = ("State dir '{0}' exists  but is not group writeable "
               "Please run `os-sandbox setup` or use a different state "
               "directory.").format(state_dir)
        raise RuntimeError(msg)

    return state_dir


def ascii_text(subject):
    """
    Returns a `six.text_type` that has been encoded with ascii codec.
    """
    if not isinstance(subject, six.string_types):
        msg = "Must be a bytestring or unicode object."
        raise TypeError(msg)

    if isinstance(subject, six.text_type):
        res = subject
    else:
        # Must be a PY2 basestring, so encode with ascii codec
        try:
            res = six.text_type(subject, 'ascii')
        except:
            msg = "Unable to encode {0} into ascii bytestring."
            raise TypeError(msg.format(subject))

    return res.encode('ascii')


def ascii_bytes(subject):
    """
    Returns a `six.binary_type` that has been decoded with ascii codec.
    """
    return ascii_text(subject).decode('ascii')


def utf8_text(subject):
    """
    Returns a `six.text_type` that has been encoded in UTF-8.
    """
    if not isinstance(subject, six.string_types):
        msg = "Must be a UTF-8 bytestring or unicode object."
        raise TypeError(msg)

    if isinstance(subject, six.text_type):
        res = subject
    else:
        # Must be a PY2 basestring, so convert into a unicode
        try:
            res = six.text_type(subject, 'utf-8')
        except UnicodeEncodeError:
            msg = "Unable to encode {0} into UTF-8 bytestring."
            raise TypeError(msg.format(subject))
    
    return res.encode('utf-8') 


def utf8_bytes(subject):
    """
    Returns a `six.binary_type` that has been decoded using UTF-8 codec.
    """
    return utf8_text(subject).decode('utf-8')


def execute(*args):
    return utf8_text(subprocess.check_output(args))


def human_bytes(size):
    """
    Returns a string with X GB, MB, KB depending on whether supplied size is
    greater than KB, MB, or GB.
    """
    if size > (1024 * 1024 * 1024):
        return "%d GB" % (size / (1024 * 1024 * 1024))
    if size > (1024 * 1024):
        return "%d MB" % (size / (1024 * 1024))
    elif size > (1024):
        return "%d KB" % (size / (1024))
    else:
        return "%d B" % size
