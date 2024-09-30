# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from io import BytesIO

# We can preload Ico too because it is considered safe
from PIL import Image

from odoo import api, fields, models, tools


class OFImage(models.Model):
    _name = "of.image"
    _description = "Image"
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    name = fields.Char()
    sequence = fields.Integer(default=10)

    image_1920 = fields.Image(required=True)

    can_image_1024_be_zoomed = fields.Boolean(
        string="Can Image 1024 be zoomed", compute="_compute_can_image_1024_be_zoomed", store=True
    )

    caption = fields.Text()
    printable = fields.Boolean(string="Print in reports", default=True)

    def action_button_rotate_left(self):
        return self.action_rotate()

    def action_button_rotate_right(self):
        return self.action_rotate(mode="right")

    def action_rotate(self, mode="left"):
        self.ensure_one()
        image_opened = Image.open(BytesIO(base64.b64decode(self.image_1920)))

        # Rotate the image by 90 degrees
        angle = 90 if mode == "left" else 270
        rotated_img = image_opened.rotate(angle, expand=True)

        # Save the rotated image as a base64 string
        buffered = BytesIO()
        rotated_img.save(buffered, format=image_opened.format)
        image_data = base64.b64encode(buffered.getvalue())

        self.write({"image_1920": image_data})
        return True

    @api.depends("image_1920", "image_1024")
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            image.can_image_1024_be_zoomed = image.image_1920 and tools.is_image_size_above(
                image.image_1920, image.image_1024
            )
