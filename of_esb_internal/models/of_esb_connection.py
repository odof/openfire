# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = "of.esb.connection"

    ttype = fields.Selection(selection_add=[("internal", "Internal")])

    def connect_internal(self):
        return True

    def get_out_example_internal(self):
        return """
        result = [
            {
                "model": "res.partner",
                "result": [
                    { "id" : 1, "name": "test" },
                    { "id" : 2, "name": "test2" },
                ]
            },
        ]
            """

    def get_in_example_internal(self):
        return """
        [
            {
                "model": "res.partner",
                "fields": [ "id", "name" ],
                "domain": [],
                "limit": 0,
                "offset": 0,
            },
        ]
        """
