from setuptools import setup

setup(
    name='textractor',
    version='1.0',
    description='Minimalistic HTML text extraction library',
    url='https://github.com/kirberich/textractor',
    author='Robert Kirberich',
    license='MIT',
    py_modules=['textractor'],
    zip_safe=False,
    install_requires=[
        'six',
        'beautifulsoup4'
    ]
)
