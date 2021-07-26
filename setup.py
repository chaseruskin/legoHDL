import setuptools
from setuptools.command.install import install
#code inspired by:
# https://packaging.python.org/tutorials/packaging-projects/

with open("README.md", "r", encoding="utf-8") as fh:
    entire_description = fh.read()

setuptools.setup(
    name="legohdl",
    version="0.1.0",
    author="Chase Ruskin",
    author_email="c.ruskin@ufl.edu",
    description="A complete HDL package manager",
    long_description=entire_description,
    long_description_content_type="text/markdown",
    url="https://github.com/c-rus/legoHDL",
    classifiers=[
        "",
    ],
    entry_points='''
            [console_scripts]
            legohdl=pkgmngr.manager:main
        ''',
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    package_data={
        "": ["settings.yml"],
        "": ["template"]
    },
    python_requires=">=3.5"
)

#
#---Installation---
#   1. create ~/.legohdl directory
#   2. create /settings.yml file
#   3. create /scripts, /registry, /template, /workspaces folders
#