odoo.define('of_import.import_pager', function (require) {
"use strict";

var core = require('web.core');
var Pager = require('web.Pager');
var One2ManyListView = core.one2many_view_registry.get('list');

Pager.include({
    /**
     * Private function that renders the pager's state
     */
    _render: function () {
        var size = this.state.size;
        var current_min = this.state.current_min;
        var current_max = this.state.current_max;
        var single_page = 1 === current_min && current_max === size;

        if ((size === 0 || single_page) && this.options.single_page_hidden) {
            this.do_hide();
        } else {
            this.do_show();

            if (single_page) {
                this.disable();
            } else {
                this.enable();
            }

            var value = "" + current_min;
            if (this.state.limit > 1) {
                value += "-" + current_max;
            }
            this.$value.html(value);
            this.$limit.html(size);
        }
    },
});

One2ManyListView.include({
    render_pager: function($node, options) {
        if (this.x2m) {
            if (typeof this.x2m.options.single_page_hidden === 'undefined') {
                this._super($node, options);
            }
            else {
                var option_value = this.x2m.options.single_page_hidden;
                console.log(option_value);
                options = _.extend(options || {}, {
                    single_page_hidden: this.x2m.options.single_page_hidden,
                });

                if (!this.pager && this.options.pager) {
                    this.pager = new Pager(this, this.dataset.size(), 1, this._limit, options);
                    this.pager.appendTo($node || this.options.$pager);

                    this.pager.on('pager_changed', this, function (new_state) {
                        var self = this;
                        var limit_changed = (this._limit !== new_state.limit);

                        this._limit = new_state.limit;
                        this.current_min = new_state.current_min;
                        this.reload_content_when_ready().then(function() {
                            // Reset the scroll position to the top on page changed only
                            if (!limit_changed) {
                                self.set_scrollTop(0);
                                self.trigger_up('scrollTo', {offset: 0});
                            }
                        });
                    });
                }
            }
        }
        else {
            this._super($node, options);
        }
    },
});

});
