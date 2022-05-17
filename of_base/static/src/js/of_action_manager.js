odoo.define('of_base.action_manager', function(require) {
    // Add new type of action to reload the main view after closing the wizard
    var action_manager = require('web.ActionManager');
    var OfBaseActionManager = action_manager.include({
        ir_actions_act_close_wizard_and_reload_view: function (action, options) {
            if (!this.dialog) {
                options.on_close();
            }
            this.dialog_stop();
            this.inner_widget.active_view.controller.reload();
            return $.when();
        },
    });
    return OfBaseActionManager;
});
