# -*- coding: utf-8 -*-

# 1: imports of python lib
from dateutil.relativedelta import relativedelta
# 2: imports of odoo
from odoo import models, fields, api
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OFContractMassAvenantWizard(models.TransientModel):
    _name = 'of.contract.mass.avenant.wizard'

    date_start = fields.Date(string="Date de prise d'effet", required=True)
    frequency = fields.Selection(selection=[
        ('date', u"À la prestation"),
        ('days', "Jour"),
        ('weeks', "Semaine"),
        ('months', "Mois"),
        ('trimester', "Trimestre"),
        ('semester', "Semestre"),
        ('years', u"Année"),
        ], string=u"Fréquence de facturation")
    frequency_amount = fields.Integer(string="Amount")
    recurring_invoicing_payment_id = fields.Many2one(
        'of.contract.recurring.invoicing.payment', string="Type de facturation")
    line_ids = fields.One2many('of.contract.mass.avenant.wizard.line', 'wizard_id')

    @api.multi
    def select_all(self):
        self.line_ids.update({'selected': True})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def deselect_all(self):
        self.line_ids.update({'selected': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_create(self):
        contract_line_obj = self.env['of.contract.line']
        for origine in self.line_ids.filtered('selected').mapped('contract_line_id'):
            data = origine.copy_data(default={
                'state': 'draft',
                'date_avenant': self.date_start,
                'type': 'avenant',
                'revision_avenant': origine.recurring_invoicing_payment_id.code == 'pre-paid',
                })[0]
            if self.recurring_invoicing_payment_id:
                data['recurring_invoicing_payment_id'] = self.recurring_invoicing_payment_id.id
            if self.frequency:
                data['frequency'] = self.frequency
            if self.frequency_amount:
                data['frequency_amount'] = self.frequency_amount
            line_data = []
            for line in origine.contract_product_ids:
                line_data.append((0, 0, line.copy_data(default={'previous_product_id': line.id})[0]))
            data['contract_product_ids'] = line_data
            avenant = contract_line_obj.create(data)
            origine.with_context(no_verification=True).write({
                'line_avenant_id': avenant.id,
                'date_end'       : fields.Date.to_string(fields.Date.from_string(self.date_start) - relativedelta(days=1)),
                })
            origine.remove_services()
        return self.env['of.popup.wizard'].popup_return(u"Les avenants on été créés", titre="Avenant de masse")


class OFContractMassAvenantWizardLine(models.TransientModel):
    _name = 'of.contract.mass.avenant.wizard.line'

    wizard_id = fields.Many2one('of.contract.mass.avenant.wizard', string="Wizard")
    selected = fields.Boolean(string=u"Affectée")
    contract_line_id = fields.Many2one('of.contract.line', string="Ligne de contrat")
    address_id = fields.Many2one(related='contract_line_id.address_id', readonly=True)
    tache_id = fields.Many2one(related='contract_line_id.tache_id', readonly=True)
