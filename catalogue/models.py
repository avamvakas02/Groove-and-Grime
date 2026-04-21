from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Categories" # Fixes "Categorys" [cite: 57]

    def __str__(self):
        return self.name

class VinylRecord(models.Model):
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=50) # Item characteristic [cite: 12]
    image = models.ImageField(upload_to='vinyls/') # Required for catalog [cite: 16]
    description = models.TextField()

    class Meta:
        verbose_name_plural = "Vinyl Records" # Fixes "Vynil Records" [cite: 57]

    def __str__(self):
        return self.title

class Review(models.Model):
    record = models.ForeignKey(VinylRecord, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5) # For AJAX ratings [cite: 20]
    comment = models.TextField()

    class Meta:
        verbose_name_plural = "Reviews"