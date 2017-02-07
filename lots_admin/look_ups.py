DENIAL_REASONS = {
    'deedoveruse': 'Applicant used the same deed for more than two lots',
    'duplicate': 'Applicant submitted the same or similar application more than once',
    'document': 'Applicant did not provide a valid property deed',
    'church': 'Applicant\'s owned property is a church',
    'name': 'Applicant name does not match deed',
    'address': 'Applicant address does not match deed',
    'nameaddress': 'Applicant name and address do not match deed',
    'block': 'Applicant is not on same block as lot',
    'adjacent': 'Another applicant is adjacent to lot',
    'lottery': 'Another applicant won the lottery',
    'residential': 'The City reserved this lot for a residential development project.',
    'economic': 'The City reserved this lot for an economic development project.',
    'open_space': 'The lot participates in NeighborSpace, of which the City was previously unaware',
    'landmark': 'The lot resides in a Landmark District and its sale depended on the criteria established by the Historic Preservation staff',
    'EDS': 'Incomplete information on EDS and principal profile',
    'debts': 'Applicant did not pay city debts',
    'commission': 'Plan Commission did not approve application',
    'citycouncil': 'City Council did not approve application',
    'none': 'None',
}

APPLICATION_STATUS = {
  'deed': 'Deed check',
  'location': 'Location check',
  'multi': 'Multiple applicant check',
  'lottery': 'Lottery',
  'letter': 'Alderman letter of support',
  'EDS': 'Submit EDS and principal profile',
  'debts': 'Certify as free and clear of debts to the city',
  'commission': 'Approval by Plan Commission',
  'city_council': 'Approval by City Council',
  'sold': 'Sold'
}