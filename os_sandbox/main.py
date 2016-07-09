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

import logging
import os
import sys

from cliff import app
from cliff import commandmanager

from os_sandbox import conf
from os_sandbox import helpers

VERSION = '0.1'
DESCRIPTION = 'Create an OpenStack sandbox'


class _bcolors:
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class OsSandboxApp(app.App):

    CONSOLE_MESSAGE_FORMAT = conf.DEFAULT_LOG_FORMAT

    def __init__(self):
        super(OsSandboxApp, self).__init__(
                description=DESCRIPTION,
                version=VERSION,
                command_manager=commandmanager.CommandManager('os_sandbox'),
                deferred_help=True,
        )

    def initialize_app(self, argv):
        self.LOG.debug('Initializing app.')

    def prepare_to_run_command(self, cmd):
        self.LOG.debug("Preparing to run command '%s", cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug("Cleaning up after running command '%s'",
                       cmd.__class__.__name__)
        if err:
            self.LOG.debug('Got error: %s', err)

    def console_wrapped(self, msg, newline=False, wrap_length=70):
        s = "%%-%ds" % wrap_length
        s = s % msg
        nl = '\n' if newline else ''
        self.stdout.write(s + nl)
        self.stdout.flush()

    def console_ok(self, newline=True):
        nl = '\n' if newline else ''
        self.stdout.write("[" + _bcolors.OKGREEN + "OK" + _bcolors.ENDC + "]" + nl)
        self.stdout.flush()

    def console_yes(self):
        self.stdout.write("yes\n")
        self.stdout.flush()

    def console_no(self):
        self.stdout.write("no\n")
        self.stdout.flush()

    def console_fail(self):
        self.stdout.write("[" + _bcolors.FAIL + "FAIL" + _bcolors.ENDC + "]\n")
        self.stdout.flush()


def main(argv=sys.argv[1:]):
    sand_app = OsSandboxApp()
    return sand_app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
