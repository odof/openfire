(function() {
    'use strict';
    var website = openerp.website;
    website.openerp_website = {};

    website.snippet.options.snippet_testimonial_options = website.snippet.Option.extend({
        on_focus: function() {
            alert("On focus!");
        }
    })
})();