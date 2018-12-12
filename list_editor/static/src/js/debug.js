/*
* @Author: D.Jane
* @Email: jane.odoo.sp@gmail.com
* */
odoo.define('list_editor.debug', function (require) {
    "use strict";
    var DebugManager = require('web.DebugManager');

    DebugManager.include({
        update: function (tag, descriptor, widget) {
            if (localStorage.getItem('list_editor')) {
                this.list_editor = true;
            }
            return this._super(tag, descriptor, widget);
        },
        toggle_list_editor: function () {
            var enable = localStorage.getItem('list_editor');
            if (enable) {
                localStorage.setItem('list_editor', '');
            } else {
                localStorage.setItem('list_editor', '1');
            }
            window.location.reload();
        }
    })
});