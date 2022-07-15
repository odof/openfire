// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

odoo.define('of_planning_recurring.form_widgets', function (require) {
"use strict";

var form_widgets = require('web.form_widgets');
var Dialog = require('web.Dialog');

var WidgetButton = form_widgets.WidgetButton;

WidgetButton.include({
    execute_action: function() {
        var self = this;
        var dfd = $.Deferred();
        var args = arguments;
        if (this.view.model == "of.planning.intervention" && this.node.attrs.name == "action_edit_recurrency"
            && !this.field_manager.get_field_value("recurrency")) {
            // On force les dates car si le RDV est en dehors des horaires de travail,
            // le clic sur le bouton génèrera une erreur
            this.field_manager.set_values({"forcer_dates": true, "verif_dispo": false}).done(function() {
                self.field_manager.fields["forcer_dates"].trigger("changed_value");
                self.field_manager.fields["verif_dispo"].trigger("changed_value");
                dfd.resolve();
            });
        }else{
            dfd.resolve();
        }
        return $.when(dfd).then(function () {
            return self._super.apply(self, args);
        })
    },
});

return WidgetButton;
});
