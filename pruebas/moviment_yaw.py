from djitellopy import Tello
import time

tello = Tello()

try:
    tello.connect()
    print("Bateria:", tello.get_battery(), "%")

    tello.takeoff()
    time.sleep(2)

    # Moviment lineal
    distancia = 20  # cm
    print(f"Avançant {distancia} cm...")
    tello.move_forward(distancia)

    time.sleep(2)

    # Gir de Yaw
    angle = 90
    print(f"Girant {angle} graus...")
    tello.rotate_clockwise(angle)

    time.sleep(2)

    tello.land()

except Exception as e:
    print("Error:", e)

finally:
    tello.end()