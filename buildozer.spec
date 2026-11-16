# (str) Title of your application
title = AI Local Gallery

# (str) Package name
package.name = ai.local.gallery

# (str) Package domain (needed for android/ios packaging)
package.domain = org.ailocals

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,woff,woff2,svg

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,app/*

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, .git, .github, __pycache__, *.pyc, *.pyo

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 1.0.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.2.1,requests,huggingface_hub,psutil,gitpython,PyGithub,pydantic,anyio,httpx,Pillow

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source. = 

# (list) Garden requirements
#garden_requirements = 

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
icon.filename = assets/icon/icon.png

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PYTHON_FILE

# (str) Android logcat filters (optional)
#android.logcat_filters = *:S python:D

# (bool) Copy library zip files when building for android
#android.copy_libs = 1

# (str) Android NDK version (default is 19b)
#android.ndk = 19b

# (int) Android API to use (default is 27)
#android.api = 27

# (int) Minimum API required (default is 21)
android.minapi = 21

# (int) Android SDK version to use (default is 27)
android.sdk = 30

# (str) android NDK version (default is 19b)
android.ndk = 23b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path = 

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path = 

# (str) python-for-android branch to use
p4a.branch = develop

# (str) OUYA Console category. Should be one of GAME or APP
#ouya.category = GAME

# (str) Filename of the Android app (aab or apk)
#android.arch = armeabi-v7a

# (int) Android App ABI version (default is 0)
#android.abi = 

# (list) Android additional libraries to copy into libs/ (optional)
#android.add_libs = foo

# (list) Android additional java code (optional)
#android.add_java_code = foo

# (str) Override Java main class name (optional)
#android.java_main_class = 

# (str) Override Java package name (optional)
#android.java_package_name = 

# (str) Override Java package domain (optional)
#android.java_package_domain = 

# (str) Override Java package source directory (optional)
#android.java_src_dir = 

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (list) List of Java .jar files to add to the libs so that pyjnius can access
# their classes (Don't add jars that you do not need, since extra jars can slow
# down the build process). All jars found in the source dir will be included
# automatically. (optional)
#android.add_jars = foo.jar,bar.jar,path/to/more/*.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files) (optional)
#android.add_java_files = 

# (list) Android architecture, default is armeabi-v7a
android.arch = arm64-v8a,armeabi-v7a

# (int) Android NDK API to use. This is the minimum API version you want to support
#android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) The Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path = 

# (str) The Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path = 

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
#p4a.source_dir = 

# (str) The bootstraps to build for, choices: sdl2_gradle, pygame_gradle, webview_gradle, service_only
android.bootstrap = sdl2_gradle

# (int) port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
#p4a.port = 

# (list) List of permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# (list) List of features (uses android:hardware element)
#android.features = android.hardware.camera

# (str) The name of the activity to start when the app is launched
#android.activity = org.kivy.android.PythonActivity

# (bool) Whether to use the Android Studio IDE for building the app
#android.studio = False

# (str) The path to the Android Studio project directory
#android.studio_path = 

# (bool) Whether to use the Gradle build system for building the app
#android.gradle = True

# (str) The path to the Gradle build file
#android.gradle_path = 

# (bool) Whether to use the Maven build system for building the app
#android.maven = False

# (str) The path to the Maven build file
#android.maven_path = 
