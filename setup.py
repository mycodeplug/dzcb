import codecs
from glob import glob
from os.path import abspath, basename, dirname, join, splitext

import setuptools


def read(*parts):
    """Read a file in this repository."""
    here = abspath(dirname(__file__))
    with codecs.open(join(here, *parts), 'r') as file_:
        return file_.read()


setuptools.setup(
    name='dzcb',
    use_scm_version=True,
    description='DMR Zone Channel Builder',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Masen Furer',
    author_email='m_github@0x26.net',
    url='https://github.com/masenf/dzcb',
    package_dir={"": 'src'},
    package_data={'dzcb': ['data/*.json', 'data/*.csv', 'data/k7abd/*.csv', 'data/farnsworth/*.json']},
    packages=setuptools.find_packages('src'),
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    python_requires='>=3.5,<4',
    setup_requires=[
        'setuptools_scm >= 3.3',
    ],
    install_requires=[
        'attrs',
        'beautifulsoup4~=4.9.3',
        'importlib-resources',
        'requests~=2.24.0',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
)
