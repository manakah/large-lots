import requests
import usaddress

from django.conf import settings

# Query Carto - useful for application form validators
def call_carto(query_args, pin):
    carto = 'https://datamade.cartodb.com/api/v2/sql'
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q': "SELECT {query_args} FROM {carto_table} WHERE pin_nbr='{pin_nbr}'" \
            .format(query_args=query_args,
                    carto_table=settings.CURRENT_CARTODB,
                    pin_nbr=pin),
    }

    response = requests.get(carto, params=params)

    return response

def parse_address(address):
    parsed = usaddress.parse(address)
    street_number = ' '.join([p[0] for p in parsed if p[1] == 'AddressNumber'])
    street_dir = ' '.join([p[0] for p in parsed if p[1] == 'StreetNamePreDirectional'])
    street_name = ' '.join([p[0] for p in parsed if p[1] == 'StreetName'])
    street_type = ' '.join([p[0] for p in parsed if p[1] == 'StreetNamePostType'])
    unit_number = ' '.join([p[0] for p in parsed if p[1] == 'OccupancyIdentifier'])

    return (street_number, street_dir, street_name, street_type, unit_number)