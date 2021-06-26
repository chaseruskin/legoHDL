import setuptools
import os
import pathlib
#some setup code inspired by:
# https://towardsdatascience.com/how-to-build-and-publish-command-line-applications-with-python-96065049abc1
# https://packaging.python.org/tutorials/packaging-projects/

with open("README.md", "r", encoding="utf-8") as fh:
    entire_description = fh.read()

with open("requirements.txt", 'r', encoding='utf-8') as f:
    reqs = f.read().split('\n')

install_list = [x.strip() for x in reqs if ('git+' not in x) \
    and (not x.startswith('#') and (not x.startswith('-')))]
dep_links = [x.strip().replace('git+', '') for x in reqs if 'git+' not in x]

setuptools.setup(
    name="legoHDL",
    version="0.0.1",
    author="Chase Ruskin",
    author_email="c.ruskin@ufl.edu",
    description="A lightweight HDL package manager",
    long_description=entire_description,
    long_descriotion_content_type="text/markdown",
    url="https://github.com/c-rus/legoHDL",
    classifiers=[
        "",
    ],
    install_requires=install_list,
    entry_points='''
            [console_scripts]
            legoHDL=pkgmngr.manager:main
        ''',
    dependency_links=dep_links,
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    package_data={
        "": ["settings.yml"],
    },
    python_requires=">=3.6"
)