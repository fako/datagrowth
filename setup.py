import setuptools

from datagrowth.version import VERSION


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="datagrowth",
    version=VERSION,
    author="Fako Berkers",
    author_email="email@fakoberkers.nl",
    description="Data engineering tools to create data mash ups using Django",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fako/datagrowth",
    packages=setuptools.find_packages(
        exclude=[
            "core", "core.*",
            "docs", "docs.*",
            "sources", "sources.*"
        ]
    ),
    install_requires=[
        "Django>=2.2",
        "celery",
        "jsonschema",
        "html5lib",
        "lxml",
        "beautifulsoup4",
        "urlobject",
        "requests",
        "Pillow>=5",
        "tqdm",
        "django-json-field",
    ],
    python_requires="~=3.6",
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.2",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
    ),
)
