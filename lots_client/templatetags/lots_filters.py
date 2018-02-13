from django import template
import re

register = template.Library()

@register.filter(name='remove_str')
def remove_str(value, arg):
    return value.replace(arg, '')

LINKS_TEXT = {
    "Z": {
        "link": "http://www.cityofchicago.org/city/en/depts/dcd/supp_info/plan_examination.html",
        "text": "Zoning Approval from Department of Planning and Development Required",
        "color": "default",
    },
    "S": {
        "link": "http://www.cityofchicago.org/city/en/depts/bldgs/provdrs/stand_plan/svcs/applications.html",
        "text": "Standard Permit Required (Dept of Buildings). Hire an Architect and a General Contractor",
        "color": "warning",
    },
    "E": {
        "link": "http://www.cityofchicago.org/city/en/depts/bldgs/provdrs/permit_proc.html",
        "text": "Easy Permit Required (Dept of Buildings). Hire a General Contractor",
        "color": "danger",
    },
}

@register.filter(name='lot_use_label', is_safe=True)
def remove_str(label_type, extra_text):
    label = "<label class='label label-{color}' data-content='{text}'>{label_type}</label>"
    if extra_text == 'True':
        label = "<label class='label label-{color}'>{label_type}</label> <a class='label-link' href='{link}' target='_blank'>{text}</a>"

    fmt_kwargs = LINKS_TEXT[label_type]
    fmt_kwargs['label_type'] = label_type

    return label.format(**fmt_kwargs)

@register.filter
def check_for_pdf(image_path):
    return image_path.endswith('pdf') or image_path.endswith('PDF')

@register.filter
def make_display_pin(pin):
    return '-'.join([pin[:2], pin[2:4], pin[4:7], pin[7:10], pin[10:]])

@register.simple_tag
def query_transform(request, **kwargs):
    updated = request.GET.copy()
    for k,v in kwargs.items():
        updated[k] = v
    return updated.urlencode()

@register.filter
def get_sort_icon(s):
    if 'desc' in str(s.lower()):
        return ' <i class="fa fa-sort-amount-asc"> </i>'
    return ' <i class="fa fa-sort-amount-desc"> </i>'

@register.filter
def get_step_all_denied(request):
    if 'all' in request:
        return 'all'
    elif 'denied' in request:
        return 'denied'
    else:
        return re.search(r'(lots-admin\/)(\d+)(\/)', request).group(2)

@register.filter
def get_value(collection, attr):
    return collection[str(attr)]
