from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.utils import application_steps


def steps(request):
    return {'steps': application_steps()}
    # short_names = {
    #     'deed': 'Deed check',
    #     'location': 'Location check',
    #     'multi': 'Multiple applicant check',
    #     'letter': 'Alderman letter',
    #     'lottery': 'Lottery',
    #     'EDS_waiting': 'Submit EDS & PPF',
    #     'EDS_submission': 'EDS & PPF submitted',
    #     'city_council': 'Approved by City Council & Plan Commission',
    #     'debts': 'Certified as debt free',
    #     'sold': 'Sold',
    # }

    # steps = [(step_from_status(k), short_names[k])
    #          for k in APPLICATION_STATUS.keys()]

    # return {'steps': steps}