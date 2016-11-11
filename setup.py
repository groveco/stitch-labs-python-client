from setuptools import setup, find_packages


setup(
    name='stitchlabs-python',
    version='0.0.1',
    description='Python client for Stitch Labs REST API',
    url='https://github.com/groveco/stitch-labs-python-client',
    keywords=['stitch'],
    install_requires=['requests==2.3.0'],
    packages=find_packages(),
    include_package_data=True,
)
