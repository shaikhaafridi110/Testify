# yourapp/context_processors.py
from .models import Contact

def contact_badge(request):
    if not request.path.startswith('/admin/'):
        return {}
    return {'new_contacts_count': Contact.objects.filter(status='new').count()}