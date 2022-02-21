import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='meshctrl',
    version='0.1.7',    
    description='Python port of MeshCentral\'s Meshctrl.js program',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/amidaware/meshctrl-py',
    author='Josh Krawczyk',
    author_email='josh@torchlake.com',
    license='MIT',
    install_requires=["websockets", "pycryptodome"],

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)