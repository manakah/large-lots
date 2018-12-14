from collections import OrderedDict

from django.conf import settings

from lots_admin.utils import application_steps


def extra_context(request):
    pilot_info = OrderedDict(reversed(sorted(settings.PILOT_INFO.items())))
    
    return {'steps': application_steps(),
            'pilot_info': pilot_info}

