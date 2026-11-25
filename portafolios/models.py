"""Modelos del dominio de portafolios.

Se almacenan solo los datos de entrada y los valores fijos en el tiempo:

- ``Precio``: p_i,t, cargado desde la hoja ``Precios``.
- ``Posicion``: relación portafolio-activo con w_i,0 (hoja ``weights``) y
  c_i,0 (calculada a partir de w_i,0, V_0 y p_i,0).

Los montos (x_i,t = p_i,t * c_i,0), el valor total (V_t = sum x_i,t) y los
weights en el tiempo (w_i,t = x_i,t / V_t) dependen de los precios, por lo que
se calculan bajo demanda con el ORM en lugar de guardarse. La justificación
está en la sección "Decisiones de diseño" del README.
"""

from django.db import models


class BaseModel(models.Model):
    """Campos de auditoría comunes a todos los modelos."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Activo(BaseModel):
    """Activo invertible (por ejemplo, ``EEUU`` o ``MM/Caja``)."""

    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Portafolio(BaseModel):
    """Portafolio de inversión compuesto por una combinación de activos.

    ``valor_inicial`` y ``fecha_inicio`` corresponden a V_0 y t = 0. Quedan
    vacíos hasta que se calculan las cantidades iniciales.
    """

    nombre = models.CharField(max_length=100, unique=True)
    valor_inicial = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    activos = models.ManyToManyField(
        Activo, through="Posicion", related_name="portafolios"
    )

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_inicial__isnull=True)
                | models.Q(valor_inicial__gt=0),
                name="portafolio_valor_inicial_positivo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valor_inicial__isnull=True, fecha_inicio__isnull=True)
                    | models.Q(valor_inicial__isnull=False, fecha_inicio__isnull=False)
                ),
                name="portafolio_valor_y_fecha_inicio_juntos",
            ),
        ]

    def __str__(self):
        return self.nombre


class Precio(BaseModel):
    """Precio p_i,t de un activo en una fecha."""

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="precios")
    fecha = models.DateField(db_index=True)
    valor = models.DecimalField(max_digits=18, decimal_places=6)

    class Meta:
        ordering = ["fecha", "activo__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["activo", "fecha"], name="precio_unico_por_activo_y_fecha"
            ),
            models.CheckConstraint(
                condition=models.Q(valor__gt=0), name="precio_valor_positivo"
            ),
        ]

    def __str__(self):
        return f"{self.activo} {self.fecha}: {self.valor}"


class Posicion(BaseModel):
    """Posición de un activo dentro de un portafolio.

    ``weight_inicial`` es w_i,0 y se carga desde el Excel. ``cantidad`` es
    c_i,0 = w_i,0 * V_0 / p_i,0. Queda vacía hasta que se calculan las
    cantidades iniciales y luego se mantiene constante (c_i,t = c_i,0).
    """

    portafolio = models.ForeignKey(
        Portafolio, on_delete=models.CASCADE, related_name="posiciones"
    )
    activo = models.ForeignKey(
        Activo, on_delete=models.CASCADE, related_name="posiciones"
    )
    weight_inicial = models.DecimalField(max_digits=9, decimal_places=6)
    cantidad = models.DecimalField(
        max_digits=28, decimal_places=10, null=True, blank=True
    )

    class Meta:
        verbose_name = "posición"
        verbose_name_plural = "posiciones"
        ordering = ["portafolio__nombre", "activo__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["portafolio", "activo"],
                name="posicion_unica_por_portafolio_y_activo",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_inicial__gte=0, weight_inicial__lte=1),
                name="posicion_weight_inicial_entre_0_y_1",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__isnull=True) | models.Q(cantidad__gte=0),
                name="posicion_cantidad_no_negativa",
            ),
        ]

    def __str__(self):
        return f"{self.portafolio} | {self.activo}"
