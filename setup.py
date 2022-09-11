from setuptools import find_packages, setup

setup(
    name="chanfig",
    version="0.0.15",
    description="Easy Configuration",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="deep learning",
    maintainer="Zhiyuan Chen",
    maintainer_email="this@zyc.ai",
    author="Zhiyuan Chen, Evian C. Liu",
    author_email="this@zyc.ai, evian.liu@outlook.com",
    url="http://github.com/ZhiyuanChen/chanfig",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
