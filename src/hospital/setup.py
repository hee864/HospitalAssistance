import glob
from setuptools import find_packages, setup

package_name = 'hospital'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    # packages=find_packages(include=['hospital', 'hospital.*']),
    
    data_files=[
    ('share/ament_index/resource_index/packages',['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    ('share/' + package_name + '/resource', glob.glob('resource/*')),
    ('share/' + package_name + '/resource', ['resource/.env']),  # glob.glob 제거
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='seokhwan',
    maintainer_email='soho010526@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_control = hospital.controller.robot_control:main',
            'object_detection = hospital.detection.detection:main',
            'get_keyword = hospital.voice.get_keyword:main',
            'test_wake_up=hospital.voice.test_wake_up:main',
            'detection_manager = hospital.detection.DetectionManager:main',

            'tracking = hospital.controller.tracking:main',
            'tracking_detection = hospital.detection.tracking_detection:main',
        ],
    },
)
