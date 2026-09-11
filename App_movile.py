import threading
import cv2
from djitellopy import Tello

from kivy.config import Config
# Ajuste de tamaño simulación móvil
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image


class ConnectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = RelativeLayout()

        
        self.label_info = Label(
            text="[b]Paso 1:[/b] Conéctate al Wi-Fi de tu Dron Tello.\n\n[b]Paso 2:[/b] Pulsa el botón para iniciar conexión.",
            markup=True,  
            font_size="15sp",
            halign="center",
            valign="middle",
            size_hint=(0.85, 0.3),
            pos_hint={'center_x': 0.5, 'center_y': 0.6}
        )
        self.label_info.bind(size=self.label_info.setter('text_size'))
        layout.add_widget(self.label_info)


        self.btn_con = Button(
            text='Conectar',
            bold=True,
            size_hint=(0.8, 0.08), 
            pos_hint={"center_x": 0.5, "center_y": 0.3},
            background_normal="",
            background_color=(0.1, 0.6, 0.9, 1) 
        )
        layout.add_widget(self.btn_con)
        self.add_widget(layout)
    def try_connection(self, instance):
        self.btn_con.disabled = True
        self.label_info = "Intentando Conectar...."
        #hilo secundario
        threading.Thread(target=self.async_connect).start()
    def async_connect(self):
        app = App.get_running_app()
        try:
            app.
        except:


#class ControlScreen(Screen):
    #def __init__(self, **kwargs):
        s#uper().__init__(**kwargs)
        


class TelloApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ConnectScreen(name='connect'))
        sm.add_widget(ControlScreen(name='control'))
        return sm


if __name__ == "__main__":
    TelloApp().run()