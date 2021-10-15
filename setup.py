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
    description="A complete HDL package manager and development tool",
    long_description=entire_description,
    long_description_content_type="text/markdown",
    url="https://github.com/c-rus/legoHDL",
    classifiers=[
        "",
    ],
    install_requires=[
        "git-Python",
    ],
    entry_points='''
            [console_scripts]
            legohdl=legohdl.legohdl:main
        ''',
    package_dir={"": "src"},
    package_data={"": ['data/icon.gif']},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.5",
    license_files=('LICENSE',),
)