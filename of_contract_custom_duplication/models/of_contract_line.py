# -*- coding: utf-8 -*-

from odoo import api, models


class OFContractLine(models.Model):
    _inherit = 'of.contract.line'

    @api.multi
    def copy_contract_line_vals(self, contract):
        self.ensure_one()
        return {
            'contract_id': contract.id,
            'address_id': self.address_id.id,
            'partner_code_magasin': self.partner_code_magasin,
            'partner_id': self.partner_id.id,
            'supplier_id': self.supplier_id.id,
            'afficher_facturation': self.afficher_facturation,
            'grouped': self.grouped,
            'next_date': self.next_date,
            'use_index': self.use_index,
            'frequency_type': self.frequency_type,
            'recurring_invoicing_payment_id': self.recurring_invoicing_payment_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'revision': self.revision,
            'contract_product_ids': [
                (
                    0,
                    0,
                    p.copy_contract_line_products_vals(),
                )
                for p in self.contract_product_ids
            ],
            'exception_line_ids': [
                (
                    0,
                    0,
                    exception_line.copy_contract_line_exception_vals(),
                )
                for exception_line in self.exception_line_ids
            ],
            'intervention_template_id': self.intervention_template_id.id,
            'tache_id': self.tache_id.id,
            'interv_frequency_nbr': self.interv_frequency_nbr,
            'interv_frequency': self.interv_frequency,
            'mois_reference_ids': [(4, month_id) for month_id in self.mois_reference_ids.ids],
            'use_sav': self.use_sav,
            'sav_count': self.sav_count,
            'notes': self.notes,
            'parc_installe_id': self.parc_installe_id.id,
            'note': self.note,
        }
