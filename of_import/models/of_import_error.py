# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError


class OfImportError(UserError):
    def __init__(self, msg):
        super().__init__(msg)
