import setuptools

from datagrowth.version import VERSION


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="datagrowth",
    version=VERSION,
    author="Fako Berkers",
    author_email="email@fakoberkers.nl",
    description="A data mash up framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fako/datagrowth",
    packages=setuptools.find_packages(),
    install_requires=[
        "Django>=1.11",
        "jsonschema",
        "html5lib",
        "beautifulsoup4",
        "urlobject",
        "requests",
        "psycopg2-binary",
        "Pillow>=5",
        "tqdm",
        "django-json-field",
    ],
    python_requires="~=3.5",
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ),
)
