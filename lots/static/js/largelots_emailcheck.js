var found_applications;

var fill_found_applications_modal = function(data, email) {
    $.each(data, function() {
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

var flush_found_applications = function() {
    $('#found_applications').empty();
    $('#found_application_confirm').hide();

    var auto_filled_fields = [
        $('#id_first_name'),
        $('#id_last_name'),
        $('#id_contact_zip_code'),
    ];

    $.each(auto_filled_fields, function() {
        this.val('');
    });
}

$('#id_email').autocomplete({
    source: function(request, response) {
        $.get("/api/get-applications", {
            email: request.term,
        }, function(data) {
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

var fill_existing_applicant_details = function (selected) {
    var applicant_details;

    $.each(found_applications, function() {
        if ( this.id == selected) {
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
