# -*- coding: utf-8 -*-

from odoo import models


class Report(models.Model):
    _inherit = "report"

    def _build_wkhtmltopdf_args(self, paperformat, specific_paperformat_args=None):
        # ATTENTION: les cases à cocher ne sont pas éditables
        # pour les rendre éditables il faudra reprendre la fonction _run_wkhtmltopdf
        # récupérer le pdf généré, et modifier le caractère éditable des champs checkbox
        # adapter la solution C# à ce souci en python
        # la solution C#: https://stackoverflow.com/questions/13265592/unable-to-print-check-boxes-in-pdf
        command_args = super(Report, self)._build_wkhtmltopdf_args(paperformat, specific_paperformat_args)
        command_args.extend(['--enable-forms'])
        return command_args
