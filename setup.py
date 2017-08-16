from setuptools import setup

setup(
    name='adwords',
    version='0.1.0',
    description='Python API for Google AdWords',
    url='https://github.com/mfrodl/adwords',
    author='Martin Frodl',
    author_email='maarilainen@gmail.com',
    license='GPLv2',
    packages=['adwords'],
    install_requires=[
        'googleads',
    ],
)
