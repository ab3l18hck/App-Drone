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

# Ajustem la mida de la finestra per simular la pantalla d'un mòbil i desactivem el canvi de mida
Window.size = (360, 640)
Config.set('graphics', 'resizable', False)



# PANTALLA DE CONNEXIÓ


class Conexion(Screen):

    def intentar_conectar(self):
        # Actualitzem la interfície abans d'iniciar la connexió
        self.ids.label_info.text = 'Intentando conectar...'
        self.ids.label_info.color = (1, 1, 1, 1)

        # Desactivem el botó per evitar múltiples clics
        self.ids.button_control.disabled = True

        # Llancem la connexió en un fil secundari perquè la app no es quedi congelada
        threading.Thread(
            target=self.conectar_hilo,
            daemon=True
        ).start()

    def conectar_hilo(self):
        app = App.get_running_app()

        try:
            # Intentem connectar amb el dron via Wi-Fi
            app.tello.connect()

            # Si funciona, passem el canvi de pantalla al fil principal de Kivy
            Clock.schedule_once(
                self.conexion_exitosa
            )

        except Exception as e:
            print(f"Error conectando: {e}")

            # En cas d'error, ho notifiquem a la interfície
            Clock.schedule_once(
                self.conexion_fallida
            )

    def conexion_exitosa(self, dt):
        self.ids.label_info.text = 'Conexión exitosa'
        self.ids.label_info.color = (0, 1, 0, 1)

        self.ids.button_control.disabled = False

        # Canviem a la pantalla de control del dron
        app = App.get_running_app()
        app.sm.current = 'controles'

    def conexion_fallida(self, dt):
        self.ids.label_info.text = (
            'Conexión fallida\n'
            'Pulsa el botón para reintentar'
        )

        self.ids.label_info.color = (0.7, 0, 0, 1)

        # Tornem a habilitar el botó canviant el text per reintentar
        self.ids.button_control.disabled = False
        self.ids.button_control.text = 'Reintentar conexión'



# PANTALLA DE CONTROLS

class Controles(Screen):

    velocidad = 45

    # Temps límit de cerca autònoma
    TIEMPO_INSPECCION = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # YOLO
        self.modelo = None

        try:
            print("Cargando modelo YOLO...")
            # Carreguem el model lleuger de YOLO
            self.modelo = YOLO("yolo11n.pt")
            print("YOLO cargado correctamente")

        except Exception as e:
            print(f"ERROR cargando YOLO: {e}")

        # ESTAT
        self.inspeccionando = False
        self.hilo_inspeccion = None
        self.detener_inspeccion = threading.Event()

        # MISSATGE
        self.mensaje_visible = False

    # ENTRAR A LA PANTALLA

    def on_enter(self):
        app = App.get_running_app()

        try:
            # Reiniciem el stream de vídeo per assegurar-nos que reps el senyal
            app.tello.streamoff()
            time.sleep(0.2)
            app.tello.streamon()

            # Programem el refresc del vídeo a 30 FPS
            Clock.schedule_interval(
                self.recargar_frame,
                1.0 / 30.0
            )

            # Consultem la bateria cada 15 segons
            Clock.schedule_interval(
                self.actualizar_bateria,
                15.0
            )

            # Lectura inicial de la bateria
            self.actualizar_bateria(0)

            self.inspeccionando = False
            self.detener_inspeccion.clear()

            self.ids.btn_insp.text = "Inspeccionar"
            self.ocultar_mensaje(0)

            print("Cámara iniciada.")

        except Exception as e:
            print(f"Error al iniciar controles: {e}")

    # SORTIR DE LA PANTALLA

    def on_leave(self):
        # Parem la retransmissió de vídeo i l'actualització de bateria per estalviar recursos
        Clock.unschedule(self.recargar_frame)
        Clock.unschedule(self.actualizar_bateria)

        self.inspeccionando = False
        self.detener_inspeccion.set()

    # REFRESC DEL VÍDEO

    def recargar_frame(self, dt):
        app = App.get_running_app()

        try:
            frame_read = app.tello.get_frame_read()

            if frame_read is None:
                return

            frame = frame_read.frame

            if frame is None:
                return

            # Creem la textura RGB a partir de la matriu d'imatge que ens dóna OpenCV
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

            # Capgirem la imatge verticalment perquè Kivy no la mostri del revés
            texture.flip_vertical()

            self.ids.camara_dron.texture = texture

        except Exception as e:
            print(f"Error cargando frame: {e}")

    # BOTÓ INSPECCIONAR

    def inspeccionar(self):
        # Si ja s'està executant la cerca, no fem res
        if self.inspeccionando:
            return

        # Comprovem que el model s'hagi carregat correctament
        if self.modelo is None:
            self.mostrar_mensaje(
                "Error: YOLO no está disponible",
                5
            )
            return

        # Activem l'estat d'inspecció i actualitzem el botó
        self.inspeccionando = True
        self.detener_inspeccion.clear()
        self.ids.btn_insp.text = "Inspeccionando..."

        # Llancem la cerca amb YOLO en un fil a part per no bloquejar el vídeo ni la pantalla
        self.hilo_inspeccion = threading.Thread(
            target=self.buscar_persona,
            daemon=True
        )

        self.hilo_inspeccion.start()

        print("================================")
        print("INSPECCIÓN INICIADA")
        print("Tiempo máximo: 10 segundos")
        print("================================")

    # BÚSQUEDA DE PERSONA AMB YOLO

    def buscar_persona(self):
        app = App.get_running_app()
        tiempo_inicio = time.time()
        persona_encontrada = False

        print("Buscando persona...")

        while self.inspeccionando:

            # Si passem dels 10 segons, aturem la cerca
            tiempo_transcurrido = time.time() - tiempo_inicio

            if tiempo_transcurrido >= self.TIEMPO_INSPECCION:
                print("Han pasado 10 segundos.")
                break

            try:
                frame_read = app.tello.get_frame_read()

                if frame_read is None:
                    time.sleep(0.1)
                    continue

                frame = frame_read.frame

                if frame is None:
                    time.sleep(0.1)
                    continue

                # Reduïm la resolució a 640x480 per accelerar el processament de la IA
                frame_yolo = cv2.resize(
                    frame,
                    (640, 480)
                )

                # Passem el frame per YOLO amb un llindar de confiança del 50%
                resultados = self.modelo(
                    frame_yolo,
                    verbose=False,
                    conf=0.50
                )

                # Recorrem les caixes de detecció obtingudes
                for resultado in resultados:

                    if resultado.boxes is None:
                        continue

                    for caja in resultado.boxes:
                        clase = int(caja.cls[0])
                        confianza = float(caja.conf[0])

                        # Comprovem si és la classe 0 (persona) i supera el 50% de confiança
                        if clase == 0 and confianza >= 0.50:
                            persona_encontrada = True
                            print("PERSONA DETECTADA")
                            print(f"Confianza: {confianza:.2f}")
                            break

                    if persona_encontrada:
                        break

                # Si hem trobat algú, parem el bucle i ho mostrem a la pantalla
                if persona_encontrada:
                    self.inspeccionando = False
                    self.detener_inspeccion.set()

                    Clock.schedule_once(
                        self.persona_detectada
                    )
                    return

                # Petita pausa per no carregar el processador al 100%
                time.sleep(0.05)

            except Exception as e:
                print(f"Error durante inspección: {e}")
                time.sleep(0.2)

        # Si hem exhaurit el temps sense trobar ningú
        self.inspeccionando = False
        self.detener_inspeccion.set()

        Clock.schedule_once(
            self.no_hay_objeto
        )

    # ESDEVENIMENTS DE RESULTAT

    def persona_detectada(self, dt):
        self.ids.btn_insp.text = "Inspeccionar"
        self.mostrar_mensaje(
            "OBJETO DETECTADO\nPERSONA",
            5
        )
        print("Mensaje: OBJETO DETECTADO - PERSONA")

    def no_hay_objeto(self, dt):
        self.ids.btn_insp.text = "Inspeccionar"
        self.mostrar_mensaje(
            "NO SE HA RECONOCIDO\nNINGÚN OBJETO",
            5
        )
        print("No se ha reconocido ningún objeto.")

    
    # GESTIÓ DE MISSATGES EN PANTALLA

    def mostrar_mensaje(self, texto, segundos):
        self.ids.label_objeto.text = texto
        self.ids.label_objeto.opacity = 1
        self.mensaje_visible = True

        # Netegem qualsevol temporitzador anterior per evitar tancaments prematurs
        Clock.unschedule(self.ocultar_mensaje)

        # Programem l'ocultació del missatge segons els segons indicats
        Clock.schedule_once(
            self.ocultar_mensaje,
            segundos
        )

    def ocultar_mensaje(self, dt):
        self.ids.label_objeto.text = ''
        self.ids.label_objeto.opacity = 0
        self.mensaje_visible = False

    
    # CONSULTA DE LA BATERIA

    def actualizar_bateria(self, dt):
        def leer_bateria():
            app = App.get_running_app()

            try:
                # Llegim l'estat de la bateria en un fil independent
                bateria = app.tello.get_battery()

                Clock.schedule_once(
                    lambda dt: self.actualizar_texto_bateria(bateria)
                )

            except Exception as e:
                print(f"Error leyendo batería: {e}")

        threading.Thread(
            target=leer_bateria,
            daemon=True
        ).start()

    def actualizar_texto_bateria(self, bateria):
        self.ids.label_battery.text = f"Battery: {bateria}%"

    # CONTROL DE MOVIMENT I MANIOBRES

    def mover_dron(self, lr=0, fb=0, ud=0, yaw=0):
        app = App.get_running_app()

        try:
            # Enviem les comandes de moviment RC (esquerra/dreta, endavant/atràs, amunt/avall, rotació)
            app.tello.send_rc_control(
                int(lr),
                int(fb),
                int(ud),
                int(yaw)
            )
        except Exception as e:
            print(f"Error enviando comando: {e}")

    def detener_dron(self):
        # Parem tots els moviments establint els eixos a 0
        self.mover_dron(0, 0, 0, 0)

    def despegar(self):
        def _despegar():
            app = App.get_running_app()
            try:
                app.tello.takeoff()
            except Exception as e:
                print(f"Error al despegar: {e}")

        # S'executa en un fil a part per no bloquejar la interfície mentre s'enlaira
        threading.Thread(
            target=_despegar,
            daemon=True
        ).start()

    def aterrizar(self):
        def _aterrizar():
            app = App.get_running_app()
            try:
                app.tello.land()
            except Exception as e:
                print(f"Error al aterrizar: {e}")

        threading.Thread(
            target=_aterrizar,
            daemon=True
        ).start()

    def rotar(self):
        def _rotar():
            app = App.get_running_app()
            try:
                # Fem un gir de 90 graus en el sentit de les agulles del rellotge
                app.tello.rotate_clockwise(90)
            except Exception as e:
                print(f"Error al rotar: {e}")

        threading.Thread(
            target=_rotar,
            daemon=True
        ).start()


# CLASSE PRINCIPAL DE LA APLICACIÓ

class droneApp(App):

    def build(self):
        self.title = 'Dron Tello App'

        # Instanciem l'objecte del dron Tello
        self.tello = Tello()

        # Configurem el gestor de pantalles
        self.sm = ScreenManager()

        self.conexion = Conexion(name='conexion')
        self.controles = Controles(name='controles')

        self.sm.add_widget(self.conexion)
        self.sm.add_widget(self.controles)

        return self.sm

    def on_stop(self):
        # Aturem la inspecció si l'aplicació es tanca de cop
        try:
            self.controles.inspeccionando = False
            self.controles.detener_inspeccion.set()
        except Exception:
            pass

        def detener_tello():
            try:
                # Enviem ordre d'aturada de seguretat als motors i apaguem el vídeo
                self.tello.send_rc_control(0, 0, 0, 0)
                self.tello.streamoff()
            except Exception:
                pass

        threading.Thread(
            target=detener_tello,
            daemon=True
        ).start()


# PUNT D'ENTRADA DE L'APLICACIÓ

if __name__ == '__main__':
    droneApp().run()
