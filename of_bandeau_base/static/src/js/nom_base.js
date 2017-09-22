odoo.define('of_bandeau_base.UserMenu', function (require) {
"use strict";

var UserMenu = require('web.UserMenu');
var session = require('web.session');

UserMenu.include({
    do_update: function () {
        var $avatar = this.$('.oe_topbar_avatar');
        if (!session.uid) {
            $avatar.attr('src', $avatar.data('default-src'));
            return $.when();
        }
        var topbar_name = session.name;
        // Inhibé par OpenFire pour afficher dans tous les cas le nom de la base
        //if(session.debug) {
        topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
        //}
        this.$('.oe_topbar_name').text(topbar_name);
        var avatar_src = session.url('/web/image', {model:'res.users', field: 'image_small', id: session.uid});
        $avatar.attr('src', avatar_src);
    },
});

return UserMenu;
});