from setuptools import setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="Chii",
    version="1.1.4",
    packages=["chii"],
    description="A minimal marketplace bot maker.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "requests",
        "python-telegram-bot==13.15",
    ],
)
