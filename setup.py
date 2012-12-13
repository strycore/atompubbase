from distutils.core import setup
VERSION = '0.1.0'
setup(name='atompubbase',
        version=VERSION, 
        author='Joe Gregorio',
        author_email='joe@bitworking.org',
        url='http://code.google.com/p/feedvalidator/',
        description='An Atom Publishing Protocol client library.',
        license='MIT',
        long_description="""

The atompubbase library is an Atom Publishing Protocol client library. 

        """,
        packages=['atompubbase', 'atompubbase.mimeparse'],
        classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
        ],
        )

