from __future__ import print_function

import os
import platform
import sys
from subprocess import check_call

from setuptools import Command, find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist

here = os.path.dirname(os.path.abspath(__file__))
node_root = os.path.join(here, "js")
is_repo = os.path.exists(os.path.join(here, ".git"))

npm_path = os.pathsep.join(
    [
        os.path.join(node_root, "node_modules", ".bin"),
        os.environ.get("PATH", os.defpath),
    ]
)

from distutils import log

log.set_verbosity(log.DEBUG)
log.info("setup.py entered")
log.info("$PATH=%s" % os.environ["PATH"])

LONG_DESCRIPTION = "A widget for interactive server-side ParaView rendering"


def js_prerelease(command, strict=False):
    """decorator for building minified js/css prior to another command"""

    class DecoratedCommand(command):
        def run(self):
            jsdeps = self.distribution.get_command_obj("jsdeps")
            if not is_repo and all(os.path.exists(t) for t in jsdeps.targets):
                # sdist, nothing to do
                command.run(self)
                return

            try:
                self.distribution.run_command("jsdeps")
            except Exception as e:
                missing = [t for t in jsdeps.targets if not os.path.exists(t)]
                if strict or missing:
                    log.warn("rebuilding js and css failed")
                    if missing:
                        log.error("missing files: %s" % missing)
                    raise e
                else:
                    log.warn("rebuilding js and css failed (not a problem)")
                    log.warn(str(e))
            command.run(self)
            update_package_data(self.distribution)

    return DecoratedCommand


def update_package_data(distribution):
    """update package_data to catch changes during setup"""
    build_py = distribution.get_command_obj("build_py")
    # distribution.package_data = find_package_data()
    # re-init build_py options which load package_data
    build_py.finalize_options()


class NPM(Command):
    description = "install package.json dependencies using npm"

    user_options = []

    node_modules = os.path.join(node_root, "node_modules")

    targets = [
        os.path.join(here, "ipyparaview", "static", "extension.js"),
        os.path.join(here, "ipyparaview", "static", "index.js"),
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def get_npm_name(self):
        npmName = "npm"
        if platform.system() == "Windows":
            npmName = "npm.cmd"

        return npmName

    def has_npm(self):
        npmName = self.get_npm_name()
        try:
            check_call([npmName, "--version"])
            return True
        except:
            return False

    def should_run_npm_install(self):
        package_json = os.path.join(node_root, "package.json")
        node_modules_exists = os.path.exists(self.node_modules)
        return self.has_npm()

    def run(self):
        has_npm = self.has_npm()
        if not has_npm:
            log.error(
                "`npm` unavailable.  If you're running this command using sudo, make sure `npm` is available to sudo"
            )

        env = os.environ.copy()
        env["PATH"] = npm_path

        if self.should_run_npm_install():
            log.info(
                "Installing build dependencies with npm.  This may take a while..."
            )
            npmName = self.get_npm_name()
            # NOTE: this is a dirty hack to get around permissions issues with npm in docker
            # It's not portable, or reliable. It may kill your dog without warning.
            import getpass

            if getpass.getuser() == "root":
                check_call(
                    [npmName, "install", "--unsafe-perm"],
                    cwd=node_root,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            else:
                check_call(
                    [npmName, "install"],
                    cwd=node_root,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            os.utime(self.node_modules, None)

        for t in self.targets:
            if not os.path.exists(t):
                msg = "Missing file: %s" % t
                if not has_npm:
                    msg += "\nnpm is required to build a development version of a widget extension"
                raise ValueError(msg)

        # update package data in case this created new files
        update_package_data(self.distribution)


version_ns = {}
with open(os.path.join(here, "ipyparaview", "_version.py")) as f:
    exec(f.read(), {}, version_ns)

setup_args = {
    "name": "ipyparaview",
    "version": version_ns["__version__"],
    "description": "A widget for interactive server-side ParaView rendering",
    "long_description": LONG_DESCRIPTION,
    "include_package_data": True,
    "data_files": [
        (
            "share/jupyter/nbextensions/ipyparaview",
            [
                "ipyparaview/static/extension.js",
                "ipyparaview/static/index.js",
                "ipyparaview/static/index.js.map",
            ],
        ),
        ("etc/jupyter/nbconfig/notebook.d", ["ipyparaview.json"]),
    ],
    "install_requires": [
        "ipywidgets>=7.0.0",
        "pillow>=7.0.0" "numpy",
    ],
    "packages": find_packages(),
    "zip_safe": False,
    "cmdclass": {
        "build_py": js_prerelease(build_py),
        "egg_info": js_prerelease(egg_info),
        "sdist": js_prerelease(sdist, strict=True),
        "jsdeps": NPM,
    },
    "author": "Nick Leaf",
    "author_email": "nleaf@nvidia.com",
    "url": "https://github.com/NVIDIA/ipyparaview",
    "keywords": [
        "ipython",
        "jupyter",
        "widgets",
    ],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Framework :: IPython",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Graphics",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
}

setup(**setup_args)
