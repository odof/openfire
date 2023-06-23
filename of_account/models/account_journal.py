# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    of_is_current_user_admin = fields.Boolean(
        string="Is the current user admin?", compute='_compute_of_is_current_user_admin'
    )
    restrict_mode_hash_table = fields.Boolean(compute='_compute_restrict_mode_hash_table', store=True, readonly=False)

    @api.depends('type')
    def _compute_of_is_current_user_admin(self):
        admins = self.env.ref('base.user_root') | self.env.ref('base.user_admin')
        for journal in self:
            journal.of_is_current_user_admin = self.env.user.id in admins.ids

    @api.depends('type')
    def _compute_restrict_mode_hash_table(self):
        for journal in self:
            journal.restrict_mode_hash_table = journal.type and journal.type not in ('purchase', 'general')

    def of_check_edit_updateable(self, vals):
        """
        Check if the values received for the modification/creation of a journal are coherent with the rights
        to edit account moves.

        :param vals: values to modify/add in the journal.
        :return: tuple of 2 elements:
            - error message if any,
            - dictionary of values to replace those of vals.
        """
        admins = self.env.ref('base.user_root') | self.env.ref('base.user_admin')
        if self.env.user.id in admins.ids:
            # Admins can do whatever they want
            return False, {}

        if 'restrict_mode_hash_table' in vals and not vals.get('restrict_mode_hash_table'):
            # Manual modification of the field `restrict_mode_hash_table`.
            # Normally, a readonly attribute should prevent this.
            # The following tests prevent a user from bypassing this readonly attribute.
            if 'type' in vals:
                error = vals['type'] in ('sale', 'bank', 'cash')
            else:
                error = self.filtered(lambda o: o.type in ('sale', 'bank', 'cash'))
            if error:
                return _("You cannot authorize the modification of accounting entries on a journal of this type"), {}
        elif 'type' in vals:
            # When changing the type of a journal, the `restrict_mode_hash_table` field may be true and fail to change
            # to false because the field has become readonly.
            # We therefore make sure to force this value to false.
            if vals['type'] in ('sale', 'bank', 'cash'):
                return "", {'restrict_mode_hash_table': True}
        return "", {}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            error, data = self.of_check_edit_updateable(vals)
            if error:
                raise UserError(error)
            vals.update(data)
        return super().create(vals_list)

    def write(self, vals):
        error, data = self.of_check_edit_updateable(vals)
        if error:
            raise UserError(error)
        vals.update(data)
        return super().write(vals)

    @api.model
    def cron_activate_restrict_mode_hash_table_on_journals(self, journal_types=None):
        if journal_types is None:
            journal_types = []
        if journals := self.search([('type', 'in', journal_types), ('restrict_mode_hash_table', '=', False)]):
            journals.write({'restrict_mode_hash_table': True})
