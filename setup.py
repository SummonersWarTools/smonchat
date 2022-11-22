from setuptools import find_packages, setup

setup(
    name='smonchat',
    packages=find_packages(include=['smonchat']),
    version='0.1.0',
    description='Python chat interface for Summoners War in-game chat.',
    author='ziddia',
    license='MIT',
    install_requires=['swgateway @ git+ssh://git@github.com/SummonersWarTools/swgateway.git#egg=swgateway-0.1.1'],
)