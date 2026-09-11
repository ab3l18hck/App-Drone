import threading
import time
import cv2

from djitellopy import Tello
from ultralytics import YOLO

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.screenmanager import ScreenManager, Screen


Window.size = (360, 640)
Config.set('graphics', 'resizable', False)


# ============================================================
# PANTALLA DE CONEXIÓN
# ============================================================

class Conexion(Screen):

    def intentar_conectar(self):

        self.ids.label_info.text = 'Intentando conectar...'
        self.ids.label_info.color = (1, 1, 1, 1)

        self.ids.button_control.disabled = True

        threading.Thread(
            target=self.conectar_hilo,
            daemon=True
        ).start()

    def conectar_hilo(self):

        app = App.get_running_app()

        try:

            app.tello.connect()

            Clock.schedule_once(
                self.conexion_exitosa
            )

        except Exception as e:

            print(f"Error conectando: {e}")

            Clock.schedule_once(
                self.conexion_fallida
            )

    def conexion_exitosa(self, dt):

        self.ids.label_info.text = 'Conexión exitosa'
        self.ids.label_info.color = (0, 1, 0, 1)

        self.ids.button_control.disabled = False

        app = App.get_running_app()
        app.sm.current = 'controles'

    def conexion_fallida(self, dt):

        self.ids.label_info.text = (
            'Conexión fallida\n'
            'Pulsa el botón para reintentar'
        )

        self.ids.label_info.color = (0.7, 0, 0, 1)

        self.ids.button_control.disabled = False

        self.ids.button_control.text = (
            'Reintentar conexión'
        )


# ============================================================
# PANTALLA DE CONTROLES
# ============================================================

class Controles(Screen):

    velocidad = 45

    # Tiempo máximo de inspección
    TIEMPO_INSPECCION = 10

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        # ----------------------------------------------------
        # YOLO
        # ----------------------------------------------------

        self.modelo = None

        try:

            print("Cargando modelo YOLO...")

            self.modelo = YOLO("yolo11n.pt")

            print("YOLO cargado correctamente")

        except Exception as e:

            print(
                f"ERROR cargando YOLO: {e}"
            )

        # ----------------------------------------------------
        # ESTADO
        # ----------------------------------------------------

        self.inspeccionando = False

        self.hilo_inspeccion = None

        self.detener_inspeccion = threading.Event()

        # ----------------------------------------------------
        # MENSAJE
        # ----------------------------------------------------

        self.mensaje_visible = False

    # ========================================================
    # ENTRAR
    # ========================================================

    def on_enter(self):

        app = App.get_running_app()

        try:

            app.tello.streamoff()
            time.sleep(0.2)
            app.tello.streamon()

            Clock.schedule_interval(
                self.recargar_frame,
                1.0 / 30.0
            )

            # Batería
            Clock.schedule_interval(
                self.actualizar_bateria,
                15.0
            )

            self.actualizar_bateria(0)

            self.inspeccionando = False
            self.detener_inspeccion.clear()

            self.ids.btn_insp.text = "Inspeccionar"

            self.ocultar_mensaje(0)

            print(
                "Cámara iniciada."
            )

        except Exception as e:

            print(
                f"Error al iniciar controles: {e}"
            )

    # ========================================================
    # SALIR
    # ========================================================

    def on_leave(self):

        Clock.unschedule(
            self.recargar_frame
        )

        Clock.unschedule(
            self.actualizar_bateria
        )

        self.inspeccionando = False

        self.detener_inspeccion.set()

    # ========================================================
    # CÁMARA (CORREGIDO EL COLOR AZUL)
    # ========================================================

    
    
    def recargar_frame(self, dt):

        app = App.get_running_app()

        try:

            frame_read = app.tello.get_frame_read()

            if frame_read is None:
                return

            frame = frame_read.frame

            if frame is None:
                return

            texture = Texture.create(
                size=(
                    frame.shape[1],
                    frame.shape[0]
                ),
                colorfmt='rgb'
            )

            texture.blit_buffer(
                frame.tobytes(),
                colorfmt='rgb',
                bufferfmt='ubyte'
            )

            texture.flip_vertical()

            self.ids.camara_dron.texture = texture
        except Exception as e:

            print(f"Error cargando frame: {e}")




    # ========================================================
    # BOTÓN INSPECCIONAR
    # ========================================================

    def inspeccionar(self):

        if self.inspeccionando:

            return

        # Comprobar que YOLO existe
        if self.modelo is None:

            self.mostrar_mensaje(
                "Error: YOLO no está disponible",
                5
            )

            return

        # ----------------------------------------------------
        # Activar inspección
        # ----------------------------------------------------

        self.inspeccionando = True

        self.detener_inspeccion.clear()

        self.ids.btn_insp.text = (
            "Inspeccionando..."
        )

        # ----------------------------------------------------
        # Crear hilo
        # ----------------------------------------------------

        self.hilo_inspeccion = threading.Thread(
            target=self.buscar_persona,
            daemon=True
        )

        self.hilo_inspeccion.start()

        print(
            "================================"
        )

        print(
            "INSPECCIÓN INICIADA"
        )

        print(
            "Tiempo máximo: 10 segundos"
        )

        print(
            "================================"
        )

    # ========================================================
    # YOLO - BUSCAR PERSONA
    # ========================================================

    def buscar_persona(self):

        app = App.get_running_app()

        tiempo_inicio = time.time()

        persona_encontrada = False

        print(
            "Buscando persona..."
        )

        while self.inspeccionando:

            # =================================================
            # COMPROBAR TIEMPO
            # =================================================

            tiempo_transcurrido = (
                time.time() - tiempo_inicio
            )

            if tiempo_transcurrido >= self.TIEMPO_INSPECCION:

                print(
                    "Han pasado 10 segundos."
                )

                break

            # =================================================
            # OBTENER FRAME
            # =================================================

            try:

                frame_read = (
                    app.tello.get_frame_read()
                )

                if frame_read is None:

                    time.sleep(0.1)

                    continue

                frame = frame_read.frame

                if frame is None:

                    time.sleep(0.1)

                    continue

                # =================================================
                # REDUCIR IMAGEN
                # =================================================

                frame_yolo = cv2.resize(
                    frame,
                    (640, 480)
                )

                # =================================================
                # YOLO
                # =================================================

                resultados = self.modelo(
                    frame_yolo,
                    verbose=False,
                    conf=0.50
                )

                # =================================================
                # BUSCAR PERSONA
                # =================================================

                for resultado in resultados:

                    if resultado.boxes is None:
                        continue

                    for caja in resultado.boxes:

                        clase = int(
                            caja.cls[0]
                        )

                        confianza = float(
                            caja.conf[0]
                        )

                        # Clase 0 = PERSONA
                        if (
                            clase == 0
                            and confianza >= 0.50
                        ):

                            persona_encontrada = True

                            print(
                                "PERSONA DETECTADA"
                            )

                            print(
                                f"Confianza: "
                                f"{confianza:.2f}"
                            )

                            break

                    if persona_encontrada:
                        break

                # =================================================
                # SI ENCUENTRA PERSONA
                # =================================================

                if persona_encontrada:

                    self.inspeccionando = False

                    self.detener_inspeccion.set()

                    Clock.schedule_once(
                        self.persona_detectada
                    )

                    return

                # Pequeña pausa
                time.sleep(0.05)

            except Exception as e:

                print(
                    f"Error durante inspección: {e}"
                )

                time.sleep(0.2)

        # =====================================================
        # TERMINÓ SIN ENCONTRAR PERSONA
        # =====================================================

        self.inspeccionando = False

        self.detener_inspeccion.set()

        Clock.schedule_once(
            self.no_hay_objeto
        )

    # ========================================================
    # PERSONA DETECTADA
    # ========================================================

    def persona_detectada(self, dt):

        self.ids.btn_insp.text = (
            "Inspeccionar"
        )

        self.mostrar_mensaje(
            "OBJETO DETECTADO\nPERSONA",
            5
        )

        print(
            "Mensaje: OBJETO DETECTADO - PERSONA"
        )

    # ========================================================
    # NO SE DETECTÓ NADA
    # ========================================================

    def no_hay_objeto(self, dt):

        self.ids.btn_insp.text = (
            "Inspeccionar"
        )

        self.mostrar_mensaje(
            "NO SE HA RECONOCIDO\nNINGÚN OBJETO",
            5
        )

        print(
            "No se ha reconocido ningún objeto."
        )

    # ========================================================
    # MOSTRAR MENSAJE
    # ========================================================

    def mostrar_mensaje(
        self,
        texto,
        segundos
    ):

        self.ids.label_objeto.text = texto

        self.ids.label_objeto.opacity = 1

        self.mensaje_visible = True

        # Cancelar ocultaciones anteriores
        Clock.unschedule(
            self.ocultar_mensaje
        )

        # Ocultar después del tiempo indicado
        Clock.schedule_once(
            self.ocultar_mensaje,
            segundos
        )

    # ========================================================
    # OCULTAR MENSAJE
    # ========================================================

    def ocultar_mensaje(self, dt):

        self.ids.label_objeto.text = ''

        self.ids.label_objeto.opacity = 0

        self.mensaje_visible = False

    # ========================================================
    # BATERÍA
    # ========================================================

    def actualizar_bateria(self, dt):

        def leer_bateria():

            app = App.get_running_app()

            try:

                bateria = (
                    app.tello.get_battery()
                )

                Clock.schedule_once(
                    lambda dt:
                    self.actualizar_texto_bateria(
                        bateria
                    )
                )

            except Exception as e:

                print(
                    f"Error leyendo batería: {e}"
                )

        threading.Thread(
            target=leer_bateria,
            daemon=True
        ).start()

    def actualizar_texto_bateria(
        self,
        bateria
    ):

        self.ids.label_battery.text = (
            f"Battery: {bateria}%"
        )

    # ========================================================
    # MOVIMIENTO
    # ========================================================

    def mover_dron(
        self,
        lr=0,
        fb=0,
        ud=0,
        yaw=0
    ):

        app = App.get_running_app()

        try:

            app.tello.send_rc_control(
                int(lr),
                int(fb),
                int(ud),
                int(yaw)
            )

        except Exception as e:

            print(
                f"Error enviando comando: {e}"
            )

    # ========================================================
    # DETENER
    # ========================================================

    def detener_dron(self):

        self.mover_dron(
            0,
            0,
            0,
            0
        )

    # ========================================================
    # DESPEGAR
    # ========================================================

    def despegar(self):

        def _despegar():

            app = App.get_running_app()

            try:

                app.tello.takeoff()

            except Exception as e:

                print(
                    f"Error al despegar: {e}"
                )

        threading.Thread(
            target=_despegar,
            daemon=True
        ).start()

    # ========================================================
    # ATERRIZAR
    # ========================================================

    def aterrizar(self):

        def _aterrizar():

            app = App.get_running_app()

            try:

                app.tello.land()

            except Exception as e:

                print(
                    f"Error al aterrizar: {e}"
                )

        threading.Thread(
            target=_aterrizar,
            daemon=True
        ).start()

    # ========================================================
    # ROTAR
    # ========================================================

    def rotar(self):

        def _rotar():

            app = App.get_running_app()

            try:

                app.tello.rotate_clockwise(90)

            except Exception as e:

                print(
                    f"Error al rotar: {e}"
                )

        threading.Thread(
            target=_rotar,
            daemon=True
        ).start()


# ============================================================
# APP
# ============================================================

class droneApp(App):

    def build(self):

        self.title = 'Dron Tello App'

        self.tello = Tello()

        self.sm = ScreenManager()

        self.conexion = Conexion(
            name='conexion'
        )

        self.controles = Controles(
            name='controles'
        )

        self.sm.add_widget(
            self.conexion
        )

        self.sm.add_widget(
            self.controles
        )

        return self.sm

    def on_stop(self):

        try:

            self.controles.inspeccionando = False

            self.controles.detener_inspeccion.set()

        except Exception:
            pass

        def detener_tello():

            try:

                self.tello.send_rc_control(
                    0,
                    0,
                    0,
                    0
                )

                self.tello.streamoff()

            except Exception:
                pass

        threading.Thread(
            target=detener_tello,
            daemon=True
        ).start()


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == '__main__':

    droneApp().run()

