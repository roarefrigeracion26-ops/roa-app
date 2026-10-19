"""
Validación y compresión de imágenes para las fotos de equipos.

Se aplica antes de guardar en el storage: reorienta según EXIF, redimensiona,
recomprime a JPEG y descarta los metadatos (incluido GPS).
"""
import io

from PIL import Image, ImageOps
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

MAX_LADO_PX = 1600
CALIDAD_JPEG = 80
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024
EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp'}

# Tope defensivo contra imágenes "bomba" (Pillow por defecto es ~89 MP).
Image.MAX_IMAGE_PIXELS = 40_000_000


def validar_archivo(archivo):
    """Verifica tamaño, tipo y que sea una imagen real. Lanza ValidationError."""
    if archivo is None:
        raise ValidationError('No se recibió ninguna imagen.')
    if archivo.size > TAMANO_MAXIMO_BYTES:
        raise ValidationError('La imagen supera el tamaño máximo permitido (10 MB).')

    content_type = getattr(archivo, 'content_type', '') or ''
    if not content_type.startswith('image/'):
        raise ValidationError('El archivo no es una imagen.')

    try:
        with Image.open(archivo) as img:
            if img.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValidationError('Formato no soportado. Usa JPG, PNG o WebP.')
            img.verify()
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError('El archivo no es una imagen válida o está dañada.') from error
    finally:
        try:
            archivo.seek(0)
        except Exception:
            pass


def _aplanar_fondo(img):
    """Compone transparencia sobre blanco y deja la imagen en modo RGB."""
    if img.mode == 'RGB':
        return img
    con_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    if con_alpha:
        img = img.convert('RGBA')
        fondo = Image.new('RGB', img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        return fondo
    return img.convert('RGB')


def procesar_imagen(archivo):
    """Reorienta, redimensiona y recomprime a JPEG. Devuelve un ContentFile."""
    archivo.seek(0)
    img = Image.open(archivo)
    img = ImageOps.exif_transpose(img)
    img = _aplanar_fondo(img)
    img.thumbnail((MAX_LADO_PX, MAX_LADO_PX), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=CALIDAD_JPEG, optimize=True)
    buffer.seek(0)
    return ContentFile(buffer.read(), name='foto.jpg')
