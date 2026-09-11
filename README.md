# Tello Drone App

Aplicación móvil para controlar un dron Tello con Python, Kivy y OpenCV.

## Requisitos

Python 3.10+ recomendado.

## Instalar dependencias

Desde la raíz del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si en tu proyecto el archivo se llama `requeriments.txt` en lugar de `requirements.txt`, usa:

```bash
python -m pip install -r requeriments.txt
```

## Dependencias

```txt
Kivy==2.3.0
opencv-python==4.10.0.84
djitellopy==2.4.0
numpy>=1.26
```

## Ejecutar la app

```bash
python App_movile.py
```

## Nota

Asegúrate de estar conectado al Wi‑Fi del dron antes de lanzar la aplicación.
