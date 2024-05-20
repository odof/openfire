# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFImage(models.Model):
    _inherit = 'of.image'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if caption := args.get('caption'):
            mutation['caption'] = caption

        if printable := args.get('printable'):
            mutation['printable'] = printable

        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence

        if image_1920 := args.get('image_1920'):
            mutation['image_1920'] = image_1920

        return mutation
