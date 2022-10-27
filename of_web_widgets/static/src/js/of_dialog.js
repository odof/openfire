odoo.define('of_web_widgets.dialog', function (require) {
"use strict";
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');

Dialog.include({
    init: function (parent, options) {
        var self = this;
        this._super.apply(this, arguments);

        var context = options.context && options.context.eval() || false;
        if (context.of_popup_width) {
            this.$modal.find('.modal-dialog').width(context.of_popup_width);
        }
    },
});

});