/*
* @Author: D.Jane
* @Email: jane.odoo.sp@gmail.com
* */
odoo.define('menu_editor.many2many_tags', function (require) {
    "use strict";
    var form_relational = require('web.form_relational');
    var core = require('web.core');

    var MyMany2ManyTags = form_relational.FieldMany2ManyTags.extend({
        render_tag: function (data) {
            this._super(data);
            var self = this;
            var $badge = this.$('.badge');
            var start_index;
            var $last_over;
            $badge.attr('draggable', 'true');
            $badge.on({
                dragstart: function () {
                    var start_id = parseInt($(this).attr('data-id'));
                    start_index = _.findIndex(data, {id: start_id})
                },
                dragenter: function () {
                    $last_over = $(this);
                },
                dragend: function () {
                    if (!$last_over){
                        return;
                    }
                    var enter_id = parseInt($last_over.attr('data-id'));
                    var enter_index = _.findIndex(data, {id: enter_id});
                    var temp = data[start_index];
                    data[start_index] = data[enter_index];
                    data[enter_index] = temp;
                    self.render_tag(data);
                    self.set('value', data.map(function (item) {
                        return item.id;
                    }));
                }
            });
        }
    });

    core.form_widget_registry.add('my_many2many_tags', MyMany2ManyTags);
});