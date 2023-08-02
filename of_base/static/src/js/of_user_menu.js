odoo.define('of_web.UserMenu_id', function (require) {
"use strict";

var Model = require('web.Model');
var UserMenu = require('web.UserMenu');

UserMenu.include({
    template: "UserMenu",
   on_menu_documentation: function () {
        new Model('ir.config_parameter').call('get_param', ['of.documentation']).then(function(url) {
            window.open(url, '_blank');
        });
    },
   on_menu_support: function () {
        new Model('ir.config_parameter').call('get_param', ['of.support']).then(function(url) {
            window.open(url, '_blank');
        });
    },
});

return UserMenu;
});
