from setuptools import setup, find_packages


try:
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ""

setup(
    name="frago",  
    version="0.1.3",
    packages=find_packages(),
    license="MIT",
    include_package_data=True,

    description="Reusable Django app for chunked file uploads",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Albin Mathew",
    author_email="albinm970@gmail.com", 

    url="https://github.com/yourname/chunked-uploader",

    install_requires=[
        "Django>=3.2",
        "djangorestframework>=3.12",
    ],
    entry_points={
        'console_scripts': [
            'frago = frago.cli:main',
        ],
    },

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],

    python_requires=">=3.7",
)
