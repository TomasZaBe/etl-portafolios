"""Acceso a las variables de entorno, siguiendo el Django-Styleguide.

Se importa en la configuración con ``from config.env import env``.
"""

import environ

env = environ.Env()
