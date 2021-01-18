odoo.define('of_company_deletion.list__view', function(require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var ListView = require('web.ListView');

ListView.include({
    // Redéfinition de la fonction standard
    do_delete: function (ids) {
        var self = this;
        if (self.model === 'res.company'){
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'of.company.deletion.wizard',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {'default_company_ids': ids, 'active_model': 'res.company'}
            });
        }
        else{
            self._super.apply(this, arguments);
        }
    },
});
})
