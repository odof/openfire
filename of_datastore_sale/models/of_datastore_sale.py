# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class OFDatastoreSale(models.Model):
    _name = "of.datastore.sale"
    _inherit = "of.datastore.connector"
    _description = "Sales Connector"
    _rec_name = "db_name"
    _order = "db_name"

    active = fields.Boolean(default=True)
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="datastore_partner_rel",
        column1="datastore_id",
        column2="partner_id",
        string="Customers",
        copy=False,
        domain=[("is_customer", "=", True), "|", ("is_company", "=", True), ("parent_id", "=", False)],
    )

    _sql_constraints = [
        (
            "db_name_login_uniq",
            "unique (db_name, login)",
            "There is already a connection for this database and login.",
        )
    ]

    def action_button_dummy(self):
        return True
