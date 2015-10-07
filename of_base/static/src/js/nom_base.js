// Afficher de façon permanente le nom de la base dans la barre de menu

openerp.of_base = function (instance) {
   
    instance.web.UserMenu.include({

	do_update: function () {
        var self = this;
        var fct = function() {
            var $avatar = self.$el.find('.oe_topbar_avatar');
            $avatar.attr('src', $avatar.data('default-src'));
            if (!self.session.uid)
                return;
            var func = new instance.web.Model("res.users").get_func("read");
            return self.alive(func(self.session.uid, ["name", "company_id"])).then(function(res) {
                var topbar_name = res.name;
                // Inhibé par OpenFire pour afficher dans tous les cas le nom de la base
                // if(instance.session.debug)
                topbar_name = _.str.sprintf("%s (%s)", topbar_name, instance.session.db);
                if(res.company_id[0] > 1)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, res.company_id[1]);
                self.$el.find('.oe_topbar_name').text(topbar_name);
                /* Inhibé par OpenFire pour afficher dans tous les cas le nom de la base
                if (!instance.session.debug) {
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, instance.session.db);
                } */
                var avatar_src = self.session.url('/web/binary/image', {model:'res.users', field: 'image_small', id: self.session.uid});
                $avatar.attr('src', avatar_src);

                openerp.web.bus.trigger('resize');  // Re-trigger the reflow logic
            });
        };
        this.update_promise = this.update_promise.then(fct, fct);
    },

    });
};
