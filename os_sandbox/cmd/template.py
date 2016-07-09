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
import yaml

from cliff import command
from cliff import lister
import slugify

from os_sandbox import conf
from os_sandbox import helpers
from os_sandbox import template


class TemplateList(lister.Lister):
    """Show a list of templates available on the sandbox host."""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(TemplateList, self).get_parser(prog_name)
        conf.add_common_args(parser)
        return parser

    def take_action(self, parsed_args):
        templates = []
        state_dir = helpers.ensure_state_dir(parsed_args)
        template_dir = os.path.join(state_dir, 'templates')
        for entry in os.listdir(template_dir):
            tpl_entry = os.path.join(template_dir, entry)
            if os.path.isdir(tpl_entry):
                templates.append(template.Template(parsed_args, entry))
        return (
            ('Name', 'Description', '# Nodes'),
            ((tpl.name, tpl.description, len(tpl.nodes))
             for tpl in templates)
        )


class TemplateShow(command.Command):
    """Show detailed information about a single template."""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(TemplateShow, self).get_parser(prog_name)
        conf.add_common_args(parser)
        parser.add_argument('name', help='Name of the template to show')
        return parser

    def take_action(self, parsed_args):
        templatees = []
        state_dir = helpers.ensure_state_dir(parsed_args)
        tpl_name = parsed_args.name
        tpl = template.Template(parsed_args, tpl_name)
        if not tpl.exists():
            msg = "A template with name {0} does not exist.".format(tpl_name)
            raise RuntimeError(msg)
            
        self.app.stdout.write('Name: ' + tpl.name + '\n')
        self.app.stdout.write('Description: ' + tpl.description + '\n')
        self.app.stdout.write('Networks:\n')
        for net_name, net_info in tpl.networks.items():
            self.app.stdout.write('  ' + net_name + ' (' + net_info['cidr'] + ')\n')
        self.app.stdout.write('Nodes:\n')
        for node in tpl.nodes:
            self.app.stdout.write('  ' + node['name'] + ' (' + ','.join(node['services']) + ')\n')
