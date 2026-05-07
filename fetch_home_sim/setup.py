from glob import glob
from setuptools import setup

package_name = 'fetch_home_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/worlds', glob('worlds/*.world')),
        ('share/' + package_name + '/worlds/models', glob('worlds/models/*', recursive=True)),
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/maps', glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Hector Tovar',
    maintainer_email='h.tovarm07@gmail.com',
    description='Fetch autonomous home simulation.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'voice_listener = fetch_home_sim.voice_listener:main',
            'command_dispatcher = fetch_home_sim.command_dispatcher:main',
            'arm_reach = fetch_home_sim.arm_reach:main',
        ],
    },
)
