# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFResPartnerUpdateSectorWizard(models.TransientModel):
    "Wizard for automatic assignment of sectors to partners"

    _name = 'of.res.partner.update.sector.wizard'
    _description = __doc__

    def action_button_validate(self):
        context = self._context.copy()
        active_ids = context.get('active_ids', []) or []

        for record in self.env['res.partner'].browse(active_ids):
            record.of_com_sector_id = (
                record.env['of.sector']
                .get_sector_from_zip_code(record.zip)
                .filtered(lambda sec: sec.type in ('commercial', 'technical_commercial'))
            )
            record.of_tech_sector_id = (
                record.env['of.sector']
                .get_sector_from_zip_code(record.zip)
                .filtered(lambda sec: sec.type in ('technical', 'technical_commercial'))
            )
