from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.utils import step_from_status


def application_steps(request):
    short_names = {
        'deed': 'Deed check',
        'location': 'Location check',
        'multi': 'Multiple applicant check',
        'letter': 'Alderman letter',
        'lottery': 'Lottery',
        'EDS_waiting': 'Submit EDS & PPF',
        'EDS_submission': 'EDS & PPF submitted',
        'city_council': 'Approved by City Council & Plan Commission',
        'debts': 'Certified as debt free',
        'sold': 'Sold',
    }

    steps = [(step_from_status(k), short_names[k])
             for k in APPLICATION_STATUS.keys()]

    return {'steps': steps}