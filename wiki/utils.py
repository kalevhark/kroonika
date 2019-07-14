from django.core.files.base import ContentFile
import os.path
from PIL import Image
from io import BytesIO

def make_thumbnail(dst_image_field, src_image_field, size, name_suffix, sep='_'):
    """
    make thumbnail image and field from source image field

    @example
        thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
    """
    # create thumbnail image
    image = Image.open(src_image_field)
    image.thumbnail(size, Image.ANTIALIAS)

    # build file name for dst
    dst_path, dst_ext = os.path.splitext(src_image_field.name)
    dst_ext = dst_ext.lower()
    dst_fname = dst_path + sep + name_suffix + dst_ext

    # check extension
    if dst_ext in ['.jpg', '.jpeg']:
        filetype = 'JPEG'
    elif dst_ext == '.gif':
        filetype = 'GIF'
    elif dst_ext == '.png':
        filetype = 'PNG'
    else:
        raise RuntimeError('unrecognized file type of "%s"' % dst_ext)

    # Save thumbnail to in-memory file as StringIO
    dst_bytes = BytesIO()
    image.save(dst_bytes, filetype)
    dst_bytes.seek(0)

    # set save=False, otherwise it will run in an infinite loop
    dst_image_field.save(dst_fname, ContentFile(dst_bytes.read()), save=False)
    dst_bytes.close()