odoo.define('of_company_deletion.form_view', function(require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var FormView = require('web.FormView');

FormView.include({
    // Redéfintion de la fonction standard
    on_button_delete: function() {
        var self = this;
        if (self.model === 'res.company'){
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'of.company.deletion.wizard',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {'default_company_ids': [self.datarecord.id], 'active_model': 'res.company'}
            });
        }
        else{
            self._super();
        }
    },
});
})
