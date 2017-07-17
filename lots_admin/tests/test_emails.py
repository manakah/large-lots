import pytest

from lots_admin.models import Application, ApplicationStatus

@pytest.mark.django_db
def test_eds_email(django_db_setup):
    '''The test database contains four application statuses,
    two for Rivers Cuomo on step 7 with no EDS sent, one
    for Robin Peckinold on step 6, and one for Lana Del Rey
    on step 7 with EDS already sent.

    Test that we appropriately select Rivers Cuomo once, and
    correctly identify the related application.
    '''

    applicants = ApplicationStatus.objects\
                                  .filter(current_step__step=7)\
                                  .filter(application__eds_sent=False)\
                                  .distinct('application__email')

    assert len(applicants) == 1

    application = applicants[0].application
    applicant_name = ' '.join([application.first_name,
                               application.last_name])

    assert applicant_name == 'Rivers Cuomo'

    related_applications = Application.objects\
                                      .filter(email=application.email)\
                                      .filter(applicationstatus__current_step__step=7)\
                                      .exclude(id=application.id)

    assert len(related_applications) == 1