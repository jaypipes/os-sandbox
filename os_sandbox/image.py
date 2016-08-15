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

import json
import os
import subprocess

from os_sandbox import helpers


class Image(object):

    def __init__(self, parsed_args, name, file_format='qcow2'):
        if name.endswith(file_format):
            name = name.rstrip('.' + file_format)
        self.name = name
        self.images_base_dir = os.path.join(parsed_args.state_dir, 'images')
        self.image_path = os.path.join(self.images_base_dir,
                                     name + '.' + file_format)
        if os.path.exists(self.image_path):
            self._fill()

    def _fill(self):
        cmd = ('qemu-img', 'info', '--output=json', self.image_path)
        try:
            output = helpers.execute(*cmd)
        except subprocess.CalledProcessError as err:
            raise RuntimeError(err)

        img_info = json.loads(output)
        self.file_format = img_info['format']
        self.virtual_size_bytes = img_info['virtual-size']
        self.disk_size_bytes = img_info['actual-size']

    def exists(self):
        return os.path.exists(self.image_path)

    def create(self, distro='ubuntu', image_size_gb=10, file_format='qcow2'):
        """Uses disk-image-create to create a new disk image.
        
        :returns a tuple containing (returncode, out, err)
        """
        # NOTE(jaypipes): Unfortunately, disk-image-create always tacks on
        # the file format to the output image filename, so we need to only
        # pass the path up to the name of the image and not the file format
        # extension.
        out_path = os.path.join(self.images_base_dir, self.name)
        args = [
            'disk-image-create',
            '-o ' + out_path,
            '-t ' + file_format,
            '--image-size=%d' % image_size_gb,
            distro,
            'vm',
            'cloud-init-nocloud',  # Avoid delay polling for EC2 metadata
            'pip-and-virtualenv',
            'local-config',  # Inject the local user's SSH keys
        ]
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        dib_out, dib_err = p.communicate()
        return p.returncode, dib_out, dib_err
