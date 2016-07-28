# os-sandbox - OpenStack Sandbox

OpenStack Sandbox is a utility for quickly creating isolated virtualized
multi-node environments running OpenStack and other infrastructure services.

## Terminology

* **sandbox host**: The machine on which `os-sandbox` is installed
* **sandbox**: A set of virtual machines running an isolated deployment of
               OpenStack on the sandbox host.
* **template**: A topology of nodes to run in a sandbox.

## Installation

**NOTE**: Before installing `os-sandbox` you will need to ensure a number of
underlying packages are installed on your system. For Debian-based systems, you
can do this using `apt-get install`:

```bash
apt-get install qemu dmsetup libvirt-dev
```

The recommended way to install `os-sandbox` is via `pip`. Further, to fully
isolate the installation from anything else on the sandbox host, we recommend
installing `os-sandbox` in a `virtualenv` and aliasing `os-sandbox` to the
virtualenv `os-sandbox` binary. That way, the only software you need installed
on the sandbox host is `python-virtualenv` and you won't need to execute the
install steps as root. Here are the steps to install `os-sandbox` in this
recommended way:

```bash
export OS_SANDBOX_DIR=~/os-sandbox
VENV_DIR="$OS_SANDBOX_DIR/.venv"
mkdir -p $OS_SANDBOX_DIR
virtualenv --no-site-packages $VENV_DIR
$VENV_DIR/bin/pip install os-sandbox
```

Add an alias to your bash shell for `os-sandbox` like so:

```bash
grep os-sandbox ~/.bash_aliases || \
echo "alias os-sandbox='$HOME/os-sandbox/.venv/bin/os-sandbox'" >> ~/.bash_aliases
```

### Developing on `os-sandbox`

Before developing, make sure you have the requisite operating system package
dependencies installed. For Debian-based systems, you can do this using
`apt-get install`:

```bash
apt-get install qemu dmsetup libvirt-dev
```

`git clone` the `os-sandbox` repository from Github.com:

```bash
# Change this to a directory that contains your source repositories
MY_SOURCE_DIR=~/src
cd $SOURCE_DIR
git clone git@github.com:jaypipes/os-sandbox
cd os-sandbox
```

Next, install a virtualenv to isolate your development environment and source
the activate file:

```bash
virtualenv --no-site-packages .venv
source .venv/bin/activate
```

And install the dependencies:

```bash
pip install -r requirements.txt
```

**Note:** If you modify requirements.txt, don't forget to re-run the above
command.

Finally, you can install your local `os-sandbox` from source:

```bash
python setup.py install
```

## Usage

### Setting up your sandbox host (one-time)

Before creating sandboxes you need to initialize the sandbox host with templates, a state directory, and a set of base images to use in creating virtual machines. Use the `os-sandbox setup` command to do this:

```bash
os-sandbox setup
```

The `os-sandbox setup` command is idempotent. You can run it at any time to
check if everything is OK with the `os-sandbox` install:

```
$ os-sandbox setup
Checking state dir /opt/os-sandbox exists ...                         yes
Checking state dir /opt/os-sandbox is group writeable ...             yes
Checking sandboxes dir /opt/os-sandbox/sandboxes exists ...           yes
Checking templates dir /opt/os-sandbox/templates exists ...           yes
Checking images dir /opt/os-sandbox/images exists ...                 yes
Checking base images exist ...                                        yes
Checking multi-one-control starter template exists ...                yes
Checking all-in-one starter template exists ...                       yes
```

### Listing templates

The first action you should take is list the templates that are available for
you to start a sandbox with. To do so, use the `os-sandbox template list`
command:

```bash
os-sandbox template list
```

Example output:

```
$ os-sandbox template list
+-------------------+-----------------------------------------------------------------+---------+
| Name              | Description                                                     | # Nodes |
+-------------------+-----------------------------------------------------------------+---------+
| multi-one-control | A set of 3 VMs with a single controller VM and two compute VMs. |       3 |
| all-in-one        | A single VM housing all OpenStack and infrastructure services.  |       1 |
+-------------------+-----------------------------------------------------------------+---------+
```

### Show details about a template

To dig inside a template to see what its configuration and structure looks
like, use the `os-sandbox template show <TEMPLATE>` command, like so:

```bash
os-sandbox template show all-in-one
```

Example output:

```
$ os-sandbox template show multi-one-control
Name: multi-one-control
Description: A set of 3 VMs with a single controller VM and two compute VMs.
Networks:
  public (192.168.30.1/24)
    private (192.168.20.1/24)
    mgmt (192.168.10.1/24)
Nodes:
  controller (controller)
  compute1 (compute)
  compute2 (compute)
```

### Listing images

You can see any images used by `os-sandbox` using the `os-sandbox image list`
command:

```
$ os-sandbox image list
+--------+-------+--------------+-----------+
| Image  | Type  | Virtual Size | Disk Size |
+--------+-------+--------------+-----------+
| ubuntu | qcow2 | 10 GB        | 351 MB    |
+--------+-------+--------------+-----------+
```

### Listing sandboxes

To view the sandboxes on the sandbox host, simple use `os-sandbox sandbox list`:

```bash
os-sandbox sandbox list
```

Example output:

```
$ os-sandbox sandbox list
+----------+-------------+-------------------+
| Sandbox  | Status      | Template          |
+----------+-------------+-------------------+
| test_sb  | Not started | multi-one-control |
| test_aio | Not started | all-in-one        |
+----------+-------------+-------------------+
```

### Showing details of a sandbox

To show information about an existing sandbox, use the `os-sandbox sandbox show
<NAME>` command:

```bash
os-sandbox sandbox show test_sb
```

Example output:

```
$ os-sandbox sandbox show test_aio
Name: test_aio
Status: Started
Template: all-in-one
Networks:
  test_aio-public (UP)
  test_aio-private (UP)
  test_aio-mgmt (UP)
Nodes:
  aio (Running)
```

### Creating a new sandbox

To create a new sandbox, use the `os-sandbox sandbox create <NAME> -t
<TEMPLATE>` command:

```bash
os-sandbox sandbox create test_sb -t multi-one-control
```

A successful creation looks like the following:

```
$ os-sandbox sandbox create test_sb -t multi-one-control
[OK] Created sandbox test_sb using template multi-one-control
```

**NOTE**: You can eliminate the printed output using the `--quiet` CLI option.

### Deleting a sandbox

To delete an existing sandbox, use the `os-sandbox sandbox delete <NAME>`
command:

```bash
os-sandbox sandbox delete test_sb
```

**NOTE**: The `os-sandbox delete` command shuts down any networks created for
the sandbox, terminates any VMs in the sandbox, undefines those VMs, and
completely destroys the sandbox directory housing all state for the sandbox.

### Starting a sandbox

To start up a sandbox, use the `os-sandbox sandbox start <NAME>` command:

```bash
os-sandbox sandbox start test_sb
```

Virtual machines and networks are created **on demand** for a sandbox when it
is started. The virtual machines and networks are **not persistent**, so if you
stop the sandbox or restart the sandbox host machine, none of the virtual
machines or networks can be seen, for instance, using `virsh list` or `virsh
net-list`.

A successful start looks like the following:

```
$ os-sandbox sandbox start test_aio
[OK] Started sandbox test_aio
```

**NOTE**: You can eliminate the printed output using the `--quiet` CLI option.

### Stopping a sandbox

To stop a running sandbox, use the `os-sandbox sandbox stop <NAME>` command:

```bash
os-sandbox sandbox stop test_sb
```

### Saving a snapshot of a sandbox

Sometimes it is useful to create a sandbox on one sandbox host machine and
launch an identical sandbox on another sandbox host machine. The `os-sandbox
sandbox save <NAME>` command produces a compressed file that can be started
on another sandbox host:

```bash
os-sandbox sandbox save test_sb
```

All virtual machines for the target sandbox are snapshotted, and all
configuration for the sandbox is written to an export directory which is then
zipped up and compressed.

The above command writes an export tarball file (by default to a file called
`$SANDBOX_NAME.tar.gz` in the current working directory).

You can start the saved sandbox on another host machine using the `os-sandbox
sandbox start --from-save=$SAVE_FILE` command:

```bash
os-sandbox sandbox start --from-save=~/Downloads/test_sb.tar.gz
```
