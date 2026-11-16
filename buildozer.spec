# Buildozer specification
# This file is used by Buildozer to build the APK

[app]

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

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,app/*

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, .git, .github, __pycache__, *.pyc, *.pyo, .buildozer, bin, .venv, docs

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
requirements = python3,kivy==2.2.1,requests,psutil,gitpython,PyGithub,pydantic,anyio,httpx,Pillow,cython

# (str) Icon of the application
icon.filename = assets/icon/icon.png

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (list) List of permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Minimum API required (default is 21)
android.minapi = 21

# (list) Android architecture, default is armeabi-v7a
android.archs = arm64-v8a,armeabi-v7a

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) python-for-android branch to use
p4a.branch = develop

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (str) The bootstraps to build for, choices: sdl2_gradle, pygame_gradle, webview_gradle, service_only
p4a.bootstrap = sdl2_gradle

# (int) Android NDK API to use. This is the minimum API version you want to support
android.ndk_api = 21

# (str) Android SDK path
#android.sdk_path = /home/runner/android-sdk

# (str) Android NDK path
#android.ndk_path = /home/runner/android-sdk/android-ndk-r23b


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2
