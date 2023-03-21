# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class OfLogMessage(models.Model):
    _name = 'of.log.message'
    _order = 'create_date DESC'

    name = fields.Char(string="Title")
    model = fields.Char(string="Model")
    type = fields.Char(string="Error type", default="error")
    message = fields.Text(string="Message", required=True)
    function = fields.Char(string="Function")
    log_level = fields.Selection(selection=[
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string="Log level", required=True, default='warning')

    @api.model
    def delete_old_logs(self, day_limit=7):
        if day_limit == 0:  # On ne veut pas que les logs soit supprimés
            return
        remove_from = datetime.now() - relativedelta(days=day_limit)
        st = fields.Datetime.to_string(remove_from)
        self.search([('create_date', '<=', st)]).unlink()

    @api.model
    def new_log(self, obj, name, type, message, function, log_level='warning'):
        model = hasattr(obj, "_name") and obj._name or ""
        self.env['of.log.message'].create({
            'name': name,
            'model': model,
            'type': type,
            'message': message,
            'function': function,
            'log_level': log_level,
        })
