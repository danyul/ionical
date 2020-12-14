import re

from setuptools import find_packages, setup  # type: ignore

with open("README.md") as r, open("CHANGELOG.md") as c:
    long_description = r.read() + "\n\n" + c.read()

version_regex = re.compile(r"__version__ = [\'\"]((\d+\.?)+(-beta)?)[\'\"]")
with open("ionical/__init__.py") as f:
    vlines = f.readlines()
version = next(
    re.match(version_regex, line).group(1)  # type: ignore
    for line in vlines
    if re.match(version_regex, line)
)

with open("requirements.txt") as requirements_file:
    requirements = requirements_file.read().splitlines()

with open("requirements-dev.txt") as dev_requirements_file:
    dev_requirements = dev_requirements_file.read().splitlines()

with open("requirements-test.txt") as test_requirements_file:
    test_requirements = test_requirements_file.read().splitlines()
    dev_requirements.extend(test_requirements)

found_packages = find_packages()
print(f"FINDPACKAGES: {found_packages}")

setup(
    name="ionical",
    version=version,
    description="command line tool for tracking ical changes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Daniel Langsam",
    author_email="dangit@langsam.org",
    url="https://github.com/danyul/ionical",
    packages=found_packages,
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords="icalendar, ics, schedule, changelog, amion, gcal, google, calendar",
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
    ],
    extras_require={
        "dev": dev_requirements,
        "test": test_requirements,
    },
    entry_points={
        "console_scripts": ["ionical=ionical.__main__:cli"],
    },
    test_suite="tests",
    tests_require=test_requirements,
)
