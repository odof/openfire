$(document).ready(function () {
    $('select[name="construction_date_id"]').on('change', function() {
        var construction_date_id = $(this);
        var show_better_g =  $('select[name="construction_date_id"] option:selected').attr('show_better_g');
        if (typeof show_better_g !== 'undefined' && show_better_g !== false) {
            $('input[name="floor_number"]').parent().show();
            $('select[name="wall_surface_id"]').parent().show();
            $('select[name="roof_surface_id"]').parent().show();
            $('select[name="floor_surface_id"]').parent().show();
        }
        else {
            $('input[name="floor_number"]').parent().hide();
            $('select[name="wall_surface_id"]').parent().hide();
            $('select[name="roof_surface_id"]').parent().hide();
            $('select[name="floor_surface_id"]').parent().hide();
        }
    });
    $('select[name="construction_date_id"]').change();
});
