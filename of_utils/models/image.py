# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io

from PIL import Image


def _get_pdf_from_img(attachment):
    stream = io.BytesIO(attachment.raw)
    img = Image.open(stream)
    new_stream = io.BytesIO()
    img.convert("RGB").save(new_stream, format="pdf")
    stream.close()
    stream = new_stream
    result = stream.getvalue()
    stream.close()
    return result
