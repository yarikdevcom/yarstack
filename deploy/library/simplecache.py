#!/usr/bin/python

import pathlib as pl
import re
import shlex
import shutil

import httpx
from ansible.module_utils.basic import AnsibleModule

PATTERN = r"[^0-9a-zA-Z\_\.]+"
DOCUMENTATION = r"""
---
module: simplecache

short_description: Cache objects using simple http get, post protocol

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: Use this module to cache directory or file by key.
lz4 required to operate and compress.
If src provided it will try to update cache.

options:
    name:
        description: Chose unique key to store cache
        required: true
        type: str
    src:
        description: Directory or file to be cached
        required: false
        type: str
    dest:
        description: Directory or file to be write in
        required: false
        type: str
    token:
        description: Auth token
        required: true
        type: str
    use_arch:
        description: Arch dependent cache
        required: false
        type: bool
        default: true
    ignore_not_existing:
        description: Ignore unexisting dirs
        required: false
        type: bool
        default: false

# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
extends_documentation_fragment:
    - simplecache

author:
    - Yaroslav Rudenok (@yarikdevcom)
"""

EXAMPLES = r"""
# Pass in a message
- name: Get from cache if dir or file not exists provided to src
  register: some_cache
  simplecache:
    name: some_key
    dest: ./mydir
    token: 'fb4cds3'

# pass in a message and have changed true
- name: Set to cache
  cache:
    name: {{ some_cache.key }}
    src: {{ some_cache.dest }}
    token: {{ some_cache.token }}
  when: not some_cache.exists
"""

RETURN = r"""
# These are examples of possible return values,
# and in general should use other names for return values.
name:
    description: File or directory key stored in cache
    type: str
    returned: always
    sample: 'python_build_1'
dest:
    description: Path to de-compress and move into
    type: str
    returned: always
    sample: '/some/path/python_build'
src:
    description: Path to file or directory to compress and cache
    type: str
    returned: always
    sample: '/some/path/python_build'
token:
    description: Token for auth
    type: str
    returned: always
    sample: 'some_gen_token'
exists:
    description: If cache exists on server
    type: bool
    returned: always
    sample: true
ignore_not_existing:
    description: Ignore non-existing dirs
    type: bool
    returned: always
    sample: false
"""


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type="str", required=True),
        src=dict(type="str", required=False, default=""),
        dest=dict(type="str", required=False, default=""),
        token=dict(type="str", required=True),
        use_arch=dict(type="bool", required=False, default=True),
        ignore_not_existing=dict(type="bool", required=False, default=False),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        name="",
        src="",
        dest="",
        token="",
        exists=False,
        use_arch=True,
        ignore_not_existing=False,
        extract_command=""
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    result["name"] = module.params["name"]
    result["src"] = module.params["src"]
    result["dest"] = module.params["dest"]
    result["token"] = module.params["token"]
    result["use_arch"] = module.params["use_arch"]
    result["ignore_not_existing"] = module.params["ignore_not_existing"]

    if result["src"] and result["dest"]:
        module.fail_json(msg="Please choose dest or src", **result)

    if result["use_arch"]:
        args = shlex.split("arch")
        rc, stdout, stderr = module.run_command(args)
        cpu_use_arch = stdout.strip().lower()
        args = shlex.split("cat /proc/cpuinfo")
        rc, stdout, stderr = module.run_command(args)
        cpu_model_name = stdout.split("model name")[-1].split("\n")
        cpu_model_name = cpu_model_name[0].split(":")[1]
        cpu_model_name = cpu_model_name.strip().replace(" ", "_").lower()
        cpu_key = "{}_{}".format(cpu_model_name, cpu_use_arch)
        cache_name = "{}_{}".format(result["name"].strip().lower(), cpu_key)
    else:
        cache_name = result["name"].strip().lower()

    cache_name = re.sub(PATTERN, "", cache_name)

    if result["dest"]:
        cache_name = "{}.tar.lz4".format(cache_name)
        response = httpx.get(
            "https://simplecache.work/files/{}".format(cache_name),
            headers={"Authorization": "Bearer {}".format(result["token"])},
        )
        dest_path = pl.Path(result["dest"]).expanduser()
        cache_file = (dest_path.parent / cache_name).resolve()
        cache_file_tar = pl.Path(
            str(cache_file).replace(".tar.lz4", ".tar")
        ).resolve()
        if response.status_code == 200:
            shutil.rmtree(str(dest_path), ignore_errors=True)
            # try:
            with cache_file.open("wb") as f, httpx.stream(
                "GET",
                "https://simplecache.work/files/{}".format(cache_name),
                headers={"Authorization": "Bearer {}".format(result["token"])},
            ) as r:
                for chunk in r.iter_bytes():
                    f.write(chunk)
            # except httpx.ConnectError:
            #     module.exit_json(**result)
            #     return

            args = "unlz4 -f {} {}".format(cache_file, cache_file_tar)
            args = shlex.split(args)
            rc, stdout, stderr = module.run_command(args)
            if rc:
                result["cache_file"] = str(cache_file)
                result["stderr"] = stderr
                module.fail_json(msg="Fail to unpack lz4 file", **result)

            args = "tar -xf {} -C {} {}".format(
                cache_file_tar, dest_path.parent, dest_path.name
            )
            args = shlex.split(args)
            result['extract_command'] = args
            rc, stdout, stderr = module.run_command(args)
            if rc:
                result["cache_file"] = str(cache_file_tar)
                result["stderr"] = stderr
                module.fail_json(msg="Fail to unpack tar file", **result)

            result["exists"] = True
            cache_file.unlink(missing_ok=True)
            cache_file_tar.unlink(missing_ok=True)
            result["changed"] = True
    elif result["src"]:
        src_path = pl.Path(result["src"]).expanduser().resolve()
        if not src_path.exists() and result["ignore_not_existing"]:
            module.exit_json(**result)
            return

        cache_file = (src_path.parent / "{}.tar".format(cache_name)).resolve()
        args = "tar -zcf {} -C {} --dereference {}".format(
            cache_file, src_path.parent, src_path.name
        )
        args = shlex.split(args)
        rc, stdout, stderr = module.run_command(args)
        if rc:
            result["cache_file"] = str(cache_file)
            result["stderr"] = stderr
            module.fail_json(msg="Fail to pack tar file", **result)

        cache_file_lz4 = pl.Path("{}.lz4".format(cache_file)).resolve()
        args = "lz4 -9 -f {} {}".format(cache_file, cache_file_lz4)
        args = shlex.split(args)
        rc, stdout, stderr = module.run_command(args)
        if rc:
            result["cache_file"] = str(cache_file_lz4)
            result["stderr"] = stderr
            module.fail_json(msg="Fail to pack lz4 file", **result)

        with cache_file_lz4.open("rb") as file:
            response = httpx.post(
                "https://simplecache.work/files/",
                headers={"Authorization": "Bearer {}".format(result["token"])},
                files={"input_file": file},
            )
            if response.status_code != 201:
                module.fail_json(
                    msg="Fail to upload file: {}".format(response.text),
                    **result
                )
            result["changed"] = True

        cache_file.unlink()
        cache_file_lz4.unlink()

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
