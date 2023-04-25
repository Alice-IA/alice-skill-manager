import os
from setuptools import setup, find_packages

BASEDIR = os.path.abspath(os.path.dirname(__file__))

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

# def required(requirements_file):
#     """ Read requirements file and remove comments and empty lines. """
#     with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
#         requirements = f.read().splitlines()
#         if 'ALICE_LOOSE_REQUIREMENTS' in os.environ:
#             print('USING LOOSE REQUIREMENTS!')
#             requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
#         return [pkg for pkg in requirements
#                 if pkg.strip() and not pkg.startswith("#")]

setup(
    name='alice-skills-manager',
    version='0.0.8',
    packages=find_packages(),
    install_requires=[line.strip() for line in open('requirements/requirements.txt')],
    package_data={'': package_files('asm')},
    # tests_require=required('requirements/tests.txt'),
    python_requires='>=3.6',
    url='https://github.com/Alice-IA/alice-skills-manager',
    license='Apache-2.0',
    author='Alice-IA',
    author_email='yuiassistant@gmail.com',
    description='Alice Skills Manager',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    entry_points={
        'console_scripts': {
            'asm=asm.__main__:main'
        }
    },
)
