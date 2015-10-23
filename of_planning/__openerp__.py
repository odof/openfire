# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
        "name" : "OpenFire / Planning",
        "version" : "0.9",
        "author" : "OpenFire",
        "website" : "http://www.openfire.fr",
        "category" : "Generic Modules/Gestion Pose",
        "description": """ Le module OpenFire des plannings de pose.
Inclut la gestion d'équipes de pose.""",
        "depends" : [
                     'hr',
                     'product',
#                      'of_calendar',
                     'of_base',
                     'of_gesdoc',
                     ],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        'css' : [
            "static/src/css/of_planning.css",
        ],
        "data" : [
            'security/of_planning_security.xml',
            'security/ir.model.access.csv',
#             'wizard/wizard_calendar.xml',
#             'of_planning_view.xml',
#             'of_planning_data.xml',
#             'wizard/wizard_print_pose.xml',
#             'wizard/wizard_print_res.xml',
#             'wizard/wizard_equipe_semaine.xml',
#             'of_planning_report.xml',
#             'wizard/message_invoice.xml',
            'views/of_planning_pose_view.xml',
            'wizard/of_planning_pose_mensuel_view.xml',
        ],
        "installable": True,
        'active': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
