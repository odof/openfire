# -*- coding: utf-8 -*-

from odoo import models

class ResCompany(models.Model):
    _inherit = "res.company"

    # Empêcher la complétion et la suppression des zéros à droite du code des comptes comptables.
    def reflect_code_digits_change(self, digits):
        return