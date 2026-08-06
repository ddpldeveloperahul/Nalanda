import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndis.settings')
django.setup()

from django.db import connection, transaction
from myapp.models import Department, DepartmentOfficer, AssetCategory, Facility, Complaint, ComplaintCategory, User, Proposal, UserDistrictScope

def resequence():
    with transaction.atomic():
        departments = list(Department.objects.all().order_by('id'))
        print(f"Total departments to resequence: {len(departments)}")
        
        # Phase 1: Move FKs and PKs to temporary high IDs (1000, 1001, etc.)
        for idx, d in enumerate(departments, start=1000):
            old_id = d.id
            temp_id = idx
            
            DepartmentOfficer.objects.filter(department_id=old_id).update(department_id=temp_id)
            AssetCategory.objects.filter(department_id=old_id).update(department_id=temp_id)
            Facility.objects.filter(department_id=old_id).update(department_id=temp_id)
            Complaint.objects.filter(department_id=old_id).update(department_id=temp_id)
            ComplaintCategory.objects.filter(department_id=old_id).update(department_id=temp_id)
            User.objects.filter(department_id=old_id).update(department_id=temp_id)
            UserDistrictScope.objects.filter(department_id=old_id).update(department_id=temp_id)
            Proposal.objects.filter(department_id=old_id).update(department_id=temp_id)
            
            Department.objects.filter(pk=old_id).update(id=temp_id)

        # Phase 2: Move FKs and PKs from temporary IDs to final clean IDs 1..10
        for idx, d in enumerate(departments, start=1):
            temp_id = idx + 999
            new_id = idx
            print(f"Assigning clean ID #{new_id} to Department '{d.name}'")
            
            DepartmentOfficer.objects.filter(department_id=temp_id).update(department_id=new_id)
            AssetCategory.objects.filter(department_id=temp_id).update(department_id=new_id)
            Facility.objects.filter(department_id=temp_id).update(department_id=new_id)
            Complaint.objects.filter(department_id=temp_id).update(department_id=new_id)
            ComplaintCategory.objects.filter(department_id=temp_id).update(department_id=new_id)
            User.objects.filter(department_id=temp_id).update(department_id=new_id)
            UserDistrictScope.objects.filter(department_id=temp_id).update(department_id=new_id)
            Proposal.objects.filter(department_id=temp_id).update(department_id=new_id)
            
            Department.objects.filter(pk=temp_id).update(id=new_id)

        # Step 3: Reset sequence in PostgreSQL to 11
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval(pg_get_serial_sequence('mst_department', 'id'), 10, true);")
            
    print("SUCCESS: All Department IDs re-sequenced to 1..10 and PostgreSQL sequence reset to 11!")

if __name__ == '__main__':
    resequence()
