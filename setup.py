import setuptools
#code inspired by:
# https://packaging.python.org/tutorials/packaging-projects/

with open("README.md", "r", encoding="utf-8") as fh:
    entire_description = fh.read()

exec(open('src/legohdl/__version__.py').read())
setuptools.setup(
    name="legohdl",
    version=__version__,
    author="Chase Ruskin",
    author_email="c.ruskin@ufl.edu",
    description="A complete HDL package manager",
    long_description=entire_description,
    long_description_content_type="text/markdown",
    url="https://github.com/c-rus/legoHDL",
    classifiers=[
        "",
    ],
    install_requires=[
        "PyYAML",
        "git-Python",
        "ordered_set",
        "requests",
    ],
    entry_points='''
            [console_scripts]
            legohdl=legohdl.manager:main
        ''',
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.5",
)