DENIAL_REASONS = {
    'duplicate': 'Applicant used the same deed for more than two lots',
    'document': 'Applicant did not provide a property deed',
    'church': 'Applicant\'s owned property is a church',
    'name': 'Applicant name does not match deed',
    'address': 'Applicant address does not match deed',
    'nameaddress': 'Applicant name and address do not match deed',
    'block': 'Applicant is not on same block as lot',
    'adjacent': 'Another applicant is adjacent to lot',
    'lottery': 'Another applicant won the lottery',
    'letter': 'Alderman did not provide letter of support',
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