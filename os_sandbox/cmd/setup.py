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
import logging
import os
import textwrap

from cliff import command

from os_sandbox import conf
from os_sandbox import image
from os_sandbox import helpers
from os_sandbox import template


class Setup(command.Command):
    """
    Initialize os-sandbox, ensure all directories exist and create sample
    templates.
    """

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Setup, self).get_parser(prog_name)
        conf.add_common_args(parser)
        return parser

    def take_action(self, parsed_args):
        self._ensure_paths(parsed_args)
        self._ensure_base_images(parsed_args)
        self._ensure_starter_templates(parsed_args)

    def _ensure_paths(self, parsed_args):
        state_dir = parsed_args.state_dir

        msg = "Checking state dir {0} exists ... "
        msg = msg.format(state_dir)
        self.app.console_wrapped(msg)

        if os.path.exists(state_dir):
            self.app.console_yes()
            msg = "Checking state dir {0} is group writeable ... "
            msg = msg.format(state_dir)
            self.app.console_wrapped(msg)
            if helpers.is_writeable(state_dir):
                self.app.console_yes()
            else:
                self.app.console_no()
                # If the state_dir is owned by the current group, then
                # just modify the permissions to be writeable.
                msg = "Checking state dir {0} is owned by current group ... "
                msg = msg.format(state_dir)
                self.app.console_wrapped(msg)
                if helpers.owned_by_current(state_dir):
                    self.app.console_yes()
                    msg = ("Changing permissions of state dir {0} to be "
                           "writeable ... ")
                    msg = msg.format(state_dir)
                    self.app.console_wrapped(msg)
                    helpers.set_writeable(state_dir)
                    self.app.console_ok()
                else:
                    self.app.console_no()
                    msg = ("Changing ownership of state dir {0} to current "
                           "user/group ... ")
                    msg = msg.format(state_dir)
                    self.app.console_wrapped(msg)
                    helpers.set_owner_current(state_dir)
                    self.app.console_ok()
        else:
            self.app.console_no()

            msg = "Creating state dir {0} with mode 0755 ... "
            msg = msg.format(state_dir)
            self.app.console_wrapped(msg)

            helpers.create_writeable_dir(state_dir)
            self.app.console_ok()

        for d in ('sandboxes', 'templates', 'images'):
            dir_path = os.path.join(state_dir, d)
            msg = "Checking {0} dir {1} exists ... "
            msg = msg.format(d, dir_path)
            self.app.console_wrapped(msg)
            if os.path.exists(dir_path):
                self.app.console_yes()
            else:
                self.app.console_no()
                os.mkdir(dir_path, 0755)

                msg = "Creating {0} dir {1} with mode 0755 ... "
                msg = msg.format(d, dir_path)
                self.app.console_wrapped(msg)
                self.app.console_ok()

    def _ensure_base_images(self, parsed_args):
        state_dir = parsed_args.state_dir

        msg = "Checking base images exist ... "
        self.app.console_wrapped(msg)

        for img_name in ('ubuntu',):
            img = image.Image(parsed_args, img_name)
            if img.exists():
                self.app.console_yes()
            else:
                self.app.console_no()

                msg = "Creating base {0} image (this can take some time) ... "
                msg = msg.format(img_name)
                self.app.console_wrapped(msg)
                retcode, out, err = img.create()
                if retcode == 0:
                    self.app.console_ok()
                else:
                    self.app.console_fail(self.app)
                    raise RuntimeError(err)

    def _ensure_starter_templates(self, parsed_args):
        state_dir = parsed_args.state_dir

        starters = {
            'all-in-one': {
                'full_name': 'All-in-one',
                'description': "A single VM housing all OpenStack and "
                               "infrastructure services.",
                'networks': {
                    'mgmt': {
                        'cidr': '192.168.10.1/24',
                    },
                    'private': {
                        'cidr': '192.168.20.1/24',
                    },
                    'public': {
                        'cidr': '192.168.30.1/24',
                    },
                },
                'nodes': [
                    {
                        'image': 'ubuntu',
                        'name': 'aio',
                        'resources': {
                            'ram_mb': 1024,
                            'vcpu': 2,
                            'disk_gb': 10,
                        },
                        'services': [
                            'controller',
                            'compute',
                        ],

                    },
                ],
            },
            'multi-one-control': {
                'full_name': 'Multi-node, Single controller',
                'description': "A set of 3 VMs with a single controller VM "
                               "and two compute VMs.",
                'networks': {
                    'mgmt': {
                        'cidr': '192.168.10.1/24',
                    },
                    'private': {
                        'cidr': '192.168.20.1/24',
                    },
                    'public': {
                        'cidr': '192.168.30.1/24',
                    },
                },
                'nodes': [
                    {
                        'image': 'ubuntu',
                        'name': 'controller',
                        'resources': {
                            'ram_mb': 1024,
                            'vcpu': 2,
                            'disk_gb': 10,
                        },
                        'services': [
                            'controller',
                        ],

                    },
                    {
                        'image': 'ubuntu',
                        'name': 'compute1',
                        'resources': {
                            'ram_mb': 1024,
                            'vcpu': 2,
                            'disk_gb': 10,
                        },
                        'services': [
                            'compute',
                        ],

                    },
                    {
                        'image': 'ubuntu',
                        'name': 'compute2',
                        'resources': {
                            'ram_mb': 1024,
                            'vcpu': 2,
                            'disk_gb': 10,
                        },
                        'services': [
                            'compute',
                        ],

                    },
                ],
            },
        }

        for tpl_name, tpl_conf in starters.items():
            tpl = template.Template(parsed_args, tpl_name)
            msg = "Checking {0} starter template exists ... "
            msg = msg.format(tpl_name)
            self.app.console_wrapped(msg)

            if tpl.exists():
                self.app.console_yes()
            else:
                self.app.console_no()

                msg = "Creating {0} starter template ... "
                msg = msg.format(tpl_name)
                self.app.console_wrapped(msg)

                tpl.create(**tpl_conf)

                self.app.console_ok()
