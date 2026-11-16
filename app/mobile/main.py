#!/usr/bin/env python3
"""
AI-Local Mobile - Main Application
===================================
Mobile app for browsing, downloading, and running AI models locally on Android.
Uses Kivy for the GUI.
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.properties import ObjectProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar

from pathlib import Path
import threading
import time

from app.core.model_manager import ModelManager, ModelInfo
from app.core.executor import ModelExecutor, InferenceResult
from app.core.resource_detector import ResourceDetector
from app.db.database import Database


# Set window properties
Window.clearcolor = get_color_from_hex('#0a0a0a')
Window.size = (360, 640)  # Default mobile size


class ModelCard(BoxLayout):
    """Card displaying a model with download and run buttons."""
    
    model_info = ObjectProperty(None)
    
    def __init__(self, model_info: ModelInfo, **kwargs):
        super().__init__(**kwargs)
        self.model_info = model_info
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 5
        self.size_hint_y = None
        self.height = 150
        
        # Card background
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(rgba=get_color_from_hex('#1e2749'))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15, 15, 15, 15])
        
        # Model name and author
        name_label = Label(
            text=f"[b]{model_info.name}[/b]" if model_info.name else "Unknown",
            markup=True,
            color=get_color_from_hex('#ffffff'),
            font_size=16,
            size_hint_y=None,
            height=30
        )
        
        author_label = Label(
            text=f"by {model_info.author}" if model_info.author else "",
            color=get_color_from_hex('#a0aec0'),
            font_size=12,
            size_hint_y=None,
            height=20
        )
        
        # Description
        desc_label = Label(
            text=model_info.description[:100] + "..." if len(model_info.description) > 100 else model_info.description,
            color=get_color_from_hex('#a0aec0'),
            font_size=12,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='top'
        )
        
        # Stats
        stats_layout = BoxLayout(size_hint_y=None, height=25, spacing=10)
        stats_layout.add_widget(Label(
            text=f"[color=#4fd1c7]⬇ {model_info.downloads}[/color]",
            markup=True,
            font_size=11
        ))
        stats_layout.add_widget(Label(
            text=f"[color=#ed8936]❤ {model_info.likes}[/color]",
            markup=True,
            font_size=11
        ))
        stats_layout.add_widget(Label(
            text=f"[color=#f56565]{model_info.size}[/color]",
            markup=True,
            font_size=11
        ))
        
        # Buttons
        buttons_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        
        download_btn = Button(
            text="⬇ Descargar",
            background_color=get_color_from_hex('#11998e'),
            color=get_color_from_hex('#ffffff'),
            font_size=12,
            size_hint_x=None,
            width=100
        )
        download_btn.bind(on_press=self.download_model)
        
        run_btn = Button(
            text="▶ Ejecutar",
            background_color=get_color_from_hex('#f093fb'),
            color=get_color_from_hex('#ffffff'),
            font_size=12,
            size_hint_x=None,
            width=100,
            disabled=not model_info.is_downloaded
        )
        run_btn.bind(on_press=self.run_model)
        
        buttons_layout.add_widget(download_btn)
        buttons_layout.add_widget(run_btn)
        
        # Add all widgets
        self.add_widget(name_label)
        self.add_widget(author_label)
        self.add_widget(desc_label)
        self.add_widget(stats_layout)
        self.add_widget(buttons_layout)
    
    def download_model(self, instance):
        """Handle download button press."""
        # This will be connected to the app's model manager
        pass
    
    def run_model(self, instance):
        """Handle run button press."""
        # This will be connected to the app's executor
        pass


class GalleryScreen(Screen):
    """Main gallery screen with model search and display."""
    
    manager = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'gallery'
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = Label(
            text="AI Gallery",
            color=get_color_from_hex('#ffffff'),
            font_size=24,
            size_hint_y=None,
            height=50,
            bold=True
        )
        header.canvas.before.clear()
        with header.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(rgba=get_color_from_hex('#667eea'))
            Rectangle(pos=header.pos, size=header.size)
        
        # Search bar
        search_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.search_input = TextInput(
            hint_text="Buscar modelos...",
            background_color=get_color_from_hex('#1a202c'),
            foreground_color=get_color_from_hex('#e0e0e0'),
            font_size=14,
            multiline=False
        )
        
        search_btn = Button(
            text="Buscar",
            background_color=get_color_from_hex('#667eea'),
            color=get_color_from_hex('#ffffff'),
            font_size=14,
            size_hint_x=None,
            width=80
        )
        search_btn.bind(on_press=self.search_models)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        
        # Task filter
        filter_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        filter_label = Label(
            text="Tarea:",
            color=get_color_from_hex('#a0aec0'),
            font_size=14,
            size_hint_x=None,
            width=60
        )
        self.task_spinner = Spinner(
            text='Todas',
            values=('Todas', 'text-generation', 'text-classification', 'image-classification', 'translation', 'summarization'),
            size_hint_x=0.7,
            background_color=get_color_from_hex('#1a202c'),
            color=get_color_from_hex('#e0e0e0')
        )
        filter_layout.add_widget(filter_label)
        filter_layout.add_widget(self.task_spinner)
        
        # Scrollable model list
        scroll = ScrollView(size_hint_y=1)
        self.models_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=5
        )
        self.models_layout.bind(minimum_height=self.models_layout.setter('height'))
        scroll.add_widget(self.models_layout)
        
        # Add to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(search_layout)
        main_layout.add_widget(filter_layout)
        main_layout.add_widget(scroll)
        
        self.add_widget(main_layout)
    
    def search_models(self, instance):
        """Search for models and display results."""
        query = self.search_input.text
        task = self.task_spinner.text if self.task_spinner.text != 'Todas' else None
        
        # This will call the model manager
        # For now, add a loading indicator
        loading_label = Label(
            text="Buscando modelos...",
            color=get_color_from_hex('#a0aec0'),
            font_size=14,
            size_hint_y=None,
            height=40
        )
        self.models_layout.clear_widgets()
        self.models_layout.add_widget(loading_label)
        
        # In a real implementation, this would be async
        # def load_models():
        #     try:
        #         results = model_manager.search_models(query=query, task=task, limit=20)
        #         self.display_results(results)
        #     except Exception as e:
        #         self.show_error(str(e))
        # threading.Thread(target=load_models).start()
    
    def display_results(self, results: list):
        """Display search results."""
        self.models_layout.clear_widgets()
        for model in results:
            card = ModelCard(model)
            self.models_layout.add_widget(card)
    
    def show_error(self, message: str):
        """Show error message."""
        self.models_layout.clear_widgets()
        error_label = Label(
            text=f"[color=#ff4757]Error: {message}[/color]",
            markup=True,
            color=get_color_from_hex('#ff4757'),
            font_size=14
        )
        self.models_layout.add_widget(error_label)


class MyModelsScreen(Screen):
    """Screen showing downloaded models."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'my_models'
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        header = Label(
            text="Mis Modelos",
            color=get_color_from_hex('#ffffff'),
            font_size=24,
            size_hint_y=None,
            height=50
        )
        
        scroll = ScrollView()
        self.models_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=5
        )
        self.models_layout.bind(minimum_height=self.models_layout.setter('height'))
        scroll.add_widget(self.models_layout)
        
        main_layout.add_widget(header)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)


class RunScreen(Screen):
    """Screen for running a model."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'run'
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        header = Label(
            text="Ejecutar Modelo",
            color=get_color_from_hex('#ffffff'),
            font_size=24,
            size_hint_y=None,
            height=50
        )
        
        # Input area
        self.input_text = TextInput(
            hint_text="Escribe tu prompt aquí...",
            background_color=get_color_from_hex('#1a202c'),
            foreground_color=get_color_from_hex('#e0e0e0'),
            font_size=14,
            multiline=True,
            size_hint_y=0.4
        )
        
        # Run button
        run_btn = Button(
            text="Ejecutar",
            background_color=get_color_from_hex('#f093fb'),
            color=get_color_from_hex('#ffffff'),
            font_size=16,
            size_hint_y=None,
            height=50
        )
        
        # Output area
        self.output_text = TextInput(
            hint_text="Resultado aparecerá aquí...",
            background_color=get_color_from_hex('#1a202c'),
            foreground_color=get_color_from_hex('#e0e0e0'),
            font_size=14,
            multiline=True,
            size_hint_y=0.4,
            readonly=True
        )
        
        main_layout.add_widget(header)
        main_layout.add_widget(self.input_text)
        main_layout.add_widget(run_btn)
        main_layout.add_widget(self.output_text)
        self.add_widget(main_layout)


class SettingsScreen(Screen):
    """Settings screen with device info."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        header = Label(
            text="Configuración",
            color=get_color_from_hex('#ffffff'),
            font_size=24,
            size_hint_y=None,
            height=50
        )
        
        # Device info
        detector = ResourceDetector()
        info_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        info_layout.add_widget(Label(
            text=f"[b]Dispositivo:[/b] {detector.get_device_type()}",
            markup=True,
            color=get_color_from_hex('#a0aec0'),
            font_size=14
        ))
        info_layout.add_widget(Label(
            text=f"[b]RAM:[/b] {detector.get_total_ram()} GB",
            markup=True,
            color=get_color_from_hex('#a0aec0'),
            font_size=14
        ))
        info_layout.add_widget(Label(
            text=f"[b]Almacenamiento:[/b] {detector.get_total_storage()} GB",
            markup=True,
            color=get_color_from_hex('#a0aec0'),
            font_size=14
        ))
        
        main_layout.add_widget(header)
        main_layout.add_widget(info_layout)
        self.add_widget(main_layout)


class AIApp(App):
    """Main application class."""
    
    def build(self):
        """Build the application."""
        self.title = "AI Local Gallery"
        self.icon = str(Path(__file__).parent.parent.parent / 'assets' / 'icon' / 'icon.png')
        
        # Create screen manager
        sm = ScreenManager()
        
        # Add screens
        sm.add_widget(GalleryScreen(name='gallery'))
        sm.add_widget(MyModelsScreen(name='my_models'))
        sm.add_widget(RunScreen(name='run'))
        sm.add_widget(SettingsScreen(name='settings'))
        
        return sm


if __name__ == '__main__':
    AIApp().run()
