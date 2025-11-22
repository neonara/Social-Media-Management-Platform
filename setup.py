import os
from setuptools import setup, find_packages


# Function to read the version from __init__.py
def get_version():
    version = {}
    with open(os.path.join(os.path.dirname(__file__), "backend", "__init__.py")) as f:
        exec(f.read(), version)
    return version["__version__"]


setup(
    name="SocialMediaManagementPlatform",
    version=get_version(),
    packages=find_packages(),
    install_requires=[
        "Django>=4.2.25,<5.0",
        "djangorestframework==3.14.0",
        "psycopg2-binary==2.9.9",
        "daphne==4.2.0",
        "django-cors-headers==3.13.0",
        "djangorestframework-simplejwt==5.5.1",
        "python-dotenv==1.1.0",
        "celery==5.3.0",
        "redis==6.2.0",
        "Pillow>=10.0.0",
        "requests==2.31.0",
        "channels==4.2.2",
        "channels-redis==4.2.0",
        "django-unfold==0.67.0",
        "whitenoise==6.9.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
