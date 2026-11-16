#!/usr/bin/env python3
"""
AI-Local - Main Entry Point
============================
This is the main entry point for the AI-Local application.
It will detect the platform and launch the appropriate GUI.

For desktop: Streamlit web interface
For mobile: Kivy native interface
"""

import sys
import platform


def is_mobile():
    """Check if running on mobile (Android)."""
    # Check for Android
    if 'ANDROID_ROOT' in sys.environ or 'ANDROID_DATA' in sys.environ:
        return True
    
    # Check for Termux
    if 'PREFIX' in sys.environ and '/data/data/com.termux' in sys.environ.get('PREFIX', ''):
        return True
    
    # Check platform
    if platform.system().lower() == 'android':
        return True
    
    return False


def main():
    """Main entry point."""
    if is_mobile():
        # Launch Kivy mobile app
        print("Launching AI-Local Mobile (Kivy)...")
        from app.mobile.main import AIApp
        AIApp().run()
    else:
        # Launch Streamlit desktop app
        print("Launching AI-Local Desktop (Streamlit)...")
        print("Run: streamlit run app/gui/app.py")
        import subprocess
        import os
        
        # Try to launch streamlit
        try:
            subprocess.run(['streamlit', 'run', 'app/gui/app.py'], check=True)
        except FileNotFoundError:
            print("Streamlit not found. Please install it with: pip install streamlit")
            sys.exit(1)


if __name__ == '__main__':
    main()
