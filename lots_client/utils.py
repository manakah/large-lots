import requests

from django.conf import settings

# Query Carto - useful for application form validators
def call_carto(query_args, pin):
    carto = 'http://datamade.cartodb.com/api/v2/sql'
    pin = pin.replace('-', '')
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q': "SELECT {query_args} FROM {carto_table} WHERE pin_nbr='{pin_nbr}'" \
            .format(query_args=query_args,
                    carto_table=settings.CURRENT_CARTODB,
                    pin_nbr=pin),
    }

    response = requests.get(carto, params=params)

    return response
