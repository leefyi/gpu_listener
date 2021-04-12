from setuptools import setup, find_packages

print(find_packages())
setup(
    name="glistener",
    version="1.0.2",
    author="leefyi",
    author_email="leefyi@126.com",
    description="single gpu listener of one time period",
    license="MIT License",
    # 项目主页
    url="https://github.com/leefyi/gpu_listener",
    # 你要安装的包，通过 setuptools.find_packages 找到当前目录下有哪些包
    packages=find_packages(),
    scripts=[],
    entry_points={
        'console_scripts': [
            'glistener=listener.gpu_standalone_listener:main'
        ]
    }
)