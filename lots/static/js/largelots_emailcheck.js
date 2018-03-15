var found_applications;

function fill_found_applications_modal(data, email) {
    $.each(data, function add_application() {
        var el = '<li><button class="option btn btn-link" data-application_id="' + this.id + '">' + this.label + '</button></li>';
        $('#found_applications').append(el);
    });

    $('#found_applications_count').text(data.length);

    if ( data.length === 1 ) {
        $('#found_applications_clause').text('person has');
    } else {
        $('#found_applications_clause').text('people have');
    }

    $('#found_applications_email').text(email);
}

function flush_found_applications() {
    $('#found_applications').empty();
    $('#found_application_confirm').hide();

    var auto_filled_fields = [
        $('#id_first_name'),
        $('#id_last_name'),
        $('#id_contact_zip_code'),
    ];

    $.each(auto_filled_fields, function clear_fields() {
        this.val('');
    });
}

$('#id_email').autocomplete({
    source: function call_application_api(request) {
        $.get("/api/get-applications", {
            email: request.term,
        }, function fill_or_flush(data) {
            var parsed_data = JSON.parse(data);

            if ( parsed_data.length > 0 ) {
                found_applications = parsed_data;
                fill_found_applications_modal(parsed_data, request.term);
                $('#application_found_modal').modal('show');
            } else {
                flush_found_applications();
            }
        });
    },
});

function fill_existing_applicant_details(selected) {
    var applicant_details;

    $.each(found_applications, function get_application_details() {
        if ( this.id === selected) {
            applicant_details = this;
            return;
        }
    });

    $('#id_first_name').val(applicant_details.first_name);
    $('#id_last_name').val(applicant_details.last_name);
    $('#id_contact_zip_code').val(applicant_details.zip_code);

    $('#application_found_modal').modal('hide');
}

$(document).on('click', 'button.option', function() {
    fill_existing_applicant_details($(this).attr('data-application_id'));
    $('#found_application_confirm').show();
});
