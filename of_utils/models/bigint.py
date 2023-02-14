# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields


class BigInteger(fields.Integer):
    column_type = ('int8', 'int8')
