from lots_admin.utils import application_steps


def steps(request):
    return {'steps': application_steps()}
