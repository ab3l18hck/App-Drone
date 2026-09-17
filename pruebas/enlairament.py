import time
from djitellopy import Tello


def main():
    drone = Tello()

    print("Conectando al dron...")
    drone.connect()
    print("Batería:", drone.get_battery())

    print("Despegando...")
    drone.takeoff()
    time.sleep(2)

    print("Aterrizando...")
    drone.land()

    print("Prueba finalizada.")


if __name__ == "__main__":
    main()
