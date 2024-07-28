from django.db import models

class Ilm(models.Model):
    # Kasutame olemasolevaid ilmateenistus.ee inglise keelseid nimetusi
    station = models.ForeignKey(
        'Jaam',
        on_delete=models.CASCADE,
        blank=True,
    )
    airtemperature = models.DecimalField('Õhutemperatuur tunni keskmine (°C)', max_digits=4, decimal_places=1, blank=True, null=True)
    relativehumidity = models.DecimalField('Suhteline õhuniiskus (%)', max_digits=4, decimal_places=1, blank=True,
                                           null=True)
    airpressure = models.DecimalField('Õhurõhk merepinnal (hPa)', max_digits=6, decimal_places=1, blank=True, null=True)
    airpressure_delta = models.DecimalField('Õhurõhu muutus (hPa)', max_digits=6, decimal_places=1, blank=True,
                                            null=True)
    winddirection = models.PositiveSmallIntegerField('Tuul suund (°)', blank=True, null=True)
    windspeed = models.DecimalField('Tuul kiirus (m/s)', max_digits=4, decimal_places=1, blank=True, null=True)
    windspeedmax = models.DecimalField('Tuul max kiirus (m/s)', max_digits=4, decimal_places=1, blank=True, null=True)
    cloudiness = models.DecimalField('Pilvisus (palli)', max_digits=4, decimal_places=1, blank=True, null=True)
    phenomenon = models.CharField('Hetkeilm (sensor)', max_length=50, blank=True, null=True)
    phenomenon_observer = models.CharField('Hetkeilm (vaatleja)', max_length=50, blank=True, null=True)
    precipitations = models.DecimalField('Sademed (mm)', max_digits=4, decimal_places=1, blank=True, null=True)
    visibility = models.DecimalField('Nähtavus (km)', max_digits=5, decimal_places=1, blank=True, null=True)
    timestamp = models.DateTimeField('Mõõtmise aeg', blank=True)
    airtemperature_max = models.DecimalField('Õhutemperatuur tunni max (°C)', max_digits=4, decimal_places=1, blank=True, null=True)
    airtemperature_min = models.DecimalField('Õhutemperatuur tunni min (°C)', max_digits=4, decimal_places=1, blank=True, null=True)


    def __repr__(self):
        return str(self.timestamp)

    def __str__(self):
        return str(self.timestamp)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Ilmavaatlused"


class Jaam(models.Model):
    name = models.CharField('Jaam', max_length=30)
    wmocode = models.CharField('wmocode', max_length=10, blank=True)
    longitude = models.FloatField('longitude', blank=True, null=True)
    latitude = models.FloatField('latitude', blank=True, null=True)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Jaamad"