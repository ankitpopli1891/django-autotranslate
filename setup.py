import os

from setuptools import (setup, find_packages)


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-autotranslate',
    version='0.2',
    packages=find_packages(),
    install_requires=['goslate'],
    include_package_data=True,
    license='MIT License',
    description='A simple Django app to autotranslate po files using google translate',
    long_description=README,
    url='https://github.com/ankitpopli1891/django-autotranslate/',
    author='Ankit Popli',
    author_email='ankitpopli1891@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)