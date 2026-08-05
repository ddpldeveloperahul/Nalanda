import os
import math
import uuid
import json
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count

from myapp.models import (
    User,
    Role,
    District,
    SubDivision,
    Block,
    VillageWard,
    Department,
    Facility,
    GISLayerFeature,
    Complaint,
    ComplaintCategory,
    ComplaintStatus,
    ComplaintPriority,
    ComplaintEvidence,
    ComplaintTimeline,
    NotificationTemplate,
    NotificationDispatchLog,
    HAS_GEODJANGO,
)

if HAS_GEODJANGO:
    from django.contrib.gis.geos import Point, GEOSGeometry


def calculate_haversine_distance_m(lat1, lon1, lat2, lon2):
    """Calculates Haversine distance in meters between two lat/lng pairs."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999999.0
    R = 6371000.0 # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def seed_fixed_roles():
    """
    Ensures the 10 fixed system roles exist in database.
    """
    roles_data = [
        {"code": "CITIZEN", "name": "Citizen", "scope": "SELF", "desc": "Citizen public grievance submitter"},
        {"code": "DISTRICT_COLLECTOR", "name": "District Collector", "scope": "DISTRICT", "desc": "District Collector executive monitoring"},
        {"code": "DISTRICT_MAGISTRATE", "name": "District Magistrate (DM)", "scope": "DISTRICT", "desc": "District Magistrate (DM) executive oversight & override"},
        {"code": "ADM", "name": "Additional District Magistrate (ADM)", "scope": "DISTRICT", "desc": "ADM grievance monitoring & escalation authority"},
        {"code": "DEPARTMENT_HEAD", "name": "Department Head", "scope": "DEPARTMENT", "desc": "Line Department Head ticket assignment authority"},
        {"code": "DEPARTMENT_OFFICER", "name": "Department Officer", "scope": "DEPARTMENT", "desc": "Department Officer ticket execution & resolution"},
        {"code": "EXECUTIVE_ENGINEER", "name": "Executive / Assistant Engineer", "scope": "DEPARTMENT", "desc": "Executive / Assistant Engineer inspection lead"},
        {"code": "FIELD_INSPECTOR", "name": "Field Inspector / Junior Engineer", "scope": "DEPARTMENT", "desc": "Field Inspector / JE geotagged site verification"},
        {"code": "FIELD_SUPERVISOR", "name": "Field Supervisor", "scope": "DEPARTMENT", "desc": "Field Supervisor work execution monitoring"},
        {"code": "STATE_ADMIN", "name": "State Admin", "scope": "STATE", "desc": "State Level Administrator full access"},
    ]

    for r in roles_data:
        role_obj = Role.objects.filter(Q(code=r["code"]) | Q(name=r["name"])).first()
        if not role_obj:
            Role.objects.create(
                code=r["code"],
                name=r["name"],
                scope_level=r["scope"],
                description=r["desc"]
            )
        else:
            role_obj.code = r["code"]
            role_obj.name = r["name"]
            role_obj.save()


def seed_default_complaint_categories():
    """
    Ensures default grievance categories with auto-routing departments & SLA targets exist.
    """
    seed_fixed_roles()
    categories_data = [
        {
            "name": "Broken Handpump / Borewell Defect",
            "dept_name": "Water Resources Department",
            "priority": ComplaintPriority.HIGH,
            "sla": 24,
            "icon": "fa-faucet-drip",
            "desc": "Drinking water handpump leakage, mechanical breakdown, or borewell failure."
        },
        {
            "name": "Piped Water Leakage / Contamination",
            "dept_name": "Water Resources Department",
            "priority": ComplaintPriority.HIGH,
            "sla": 12,
            "icon": "fa-pipe-valve",
            "desc": "Har Ghar Nal Ka Jal pipe breakage or water quality contamination."
        },
        {
            "name": "Garbage Accumulation / Sanitation",
            "dept_name": "Urban Development & Infra",
            "priority": ComplaintPriority.MEDIUM,
            "sla": 24,
            "icon": "fa-trash-can",
            "desc": "Uncollected municipal solid waste, clogged public drains, or sanitation hazard."
        },
        {
            "name": "Non-Functional Street Light",
            "dept_name": "Urban Development & Infra",
            "priority": ComplaintPriority.LOW,
            "sla": 48,
            "icon": "fa-lightbulb",
            "desc": "Street light dark spot or electrical pole fixture defect."
        },
        {
            "name": "Transformer Failure / Power Outage",
            "dept_name": "Public Works & Transport Department",
            "priority": ComplaintPriority.CRITICAL,
            "sla": 6,
            "icon": "fa-bolt-lightning",
            "desc": "Burnt electrical transformer, fallen wire, or prolonged power failure."
        },
        {
            "name": "Hospital Staff / Oxygen / Facility Issue",
            "dept_name": "Health Department",
            "priority": ComplaintPriority.HIGH,
            "sla": 12,
            "icon": "fa-hospital",
            "desc": "PHC/Sadar hospital medicine shortage, emergency staff absence, or equipment breakdown."
        },
        {
            "name": "School Infrastructure / Roof / Sanitation",
            "dept_name": "Education Department",
            "priority": ComplaintPriority.MEDIUM,
            "sla": 48,
            "icon": "fa-school",
            "desc": "Government school building damage, student toilet blockage, or drinking water defect."
        },
        {
            "name": "Road Potholes / Damaged Bridge",
            "dept_name": "Public Works & Transport Department",
            "priority": ComplaintPriority.MEDIUM,
            "sla": 72,
            "icon": "fa-road",
            "desc": "PWD road pothole, damaged culvert, or hazardous bridge defect."
        },
    ]

    for cat_info in categories_data:
        dept, _ = Department.objects.get_or_create(name=cat_info["dept_name"])
        ComplaintCategory.objects.get_or_create(
            name=cat_info["name"],
            defaults={
                "department": dept,
                "default_priority": cat_info["priority"],
                "default_sla_hours": cat_info["sla"],
                "icon": cat_info["icon"],
                "description": cat_info["desc"]
            }
        )


class ComplaintService:
    """
    Enterprise Service Layer for Complaint Management & Workflow Orchestration.
    """

    @staticmethod
    def generate_tracking_no():
        date_str = timezone.now().strftime("%Y%m%d")
        rand_str = uuid.uuid4().hex[:5].upper()
        return f"NDIS-{date_str}-{rand_str}"

    @staticmethod
    def dispatch_notification(complaint, user, message_template):
        """Sends background notification dispatch record."""
        if not user:
            return
        try:
            template, _ = NotificationTemplate.objects.get_or_create(
                name="COMPLAINT_WORKFLOW_EVENT",
                defaults={
                    "channel": "PUSH",
                    "locale": "EN",
                    "body_template": message_template
                }
            )
            NotificationDispatchLog.objects.create(
                template=template,
                user=user,
                status="DISPATCHED"
            )
        except Exception:
            pass

    @staticmethod
    def log_timeline(complaint, action, performer=None, from_status=None, to_status=None, remarks="", metadata=None):
        """Appends immutable audit timeline event."""
        role_name = ""
        if performer and hasattr(performer, "role") and performer.role:
            role_name = performer.role.name
        
        ComplaintTimeline.objects.create(
            complaint=complaint,
            action=action,
            from_status=from_status or complaint.status,
            to_status=to_status or complaint.status,
            performed_by=performer if (performer and getattr(performer, "is_authenticated", True)) else None,
            performer_role=role_name,
            remarks=remarks,
            metadata=metadata or {}
        )

    @classmethod
    def create_complaint(cls, user, validated_data, files=None):
        """
        Creates a new complaint ticket with auto-routing, spatial calculations, and SLA computation.
        """
        seed_default_complaint_categories()
        
        with transaction.atomic():
            tracking_no = cls.generate_tracking_no()
            category = validated_data.get("category")
            
            # Determine Department via Auto-Routing Engine
            department = validated_data.get("department")
            if not department and category:
                department = category.department
            if not department:
                department = Department.objects.first()

            # SLA calculation
            sla_hours = category.default_sla_hours if category else 24
            priority = category.default_priority if category else ComplaintPriority.MEDIUM
            sla_deadline = timezone.now() + timedelta(hours=sla_hours)

            lat = validated_data.get("latitude")
            lng = validated_data.get("longitude")

            # Spatial Calculations for Nearest Facility & Administrative Boundaries
            nearest_fac = None
            nearest_fac_name = None
            nearest_fac_dist = None
            
            if lat and lng:
                facilities = Facility.objects.all()[:100]
                min_dist = 999999.0
                closest = None
                for fac in facilities:
                    fac_lat, fac_lng = None, None
                    if hasattr(fac, 'geom') and fac.geom:
                        try:
                            if hasattr(fac.geom, 'y'):
                                fac_lat, fac_lng = fac.geom.y, fac.geom.x
                            elif isinstance(fac.geom, dict) and 'coordinates' in fac.geom:
                                coords = fac.geom['coordinates']
                                fac_lng, fac_lat = coords[0], coords[1]
                        except Exception:
                            pass
                    
                    if fac_lat and fac_lng:
                        dist = calculate_haversine_distance_m(lat, lng, fac_lat, fac_lng)
                        if dist < min_dist:
                            min_dist = dist
                            closest = fac
                
                if closest:
                    nearest_fac = closest
                    nearest_fac_name = f"{closest.name} ({int(min_dist)}m away)"
                    nearest_fac_dist = min_dist

            # Create Spatial Geometry Point if GeoDjango is available
            geos_point = None
            if HAS_GEODJANGO and lat and lng:
                try:
                    geos_point = Point(float(lng), float(lat), srid=4326)
                except Exception:
                    geos_point = None

            # Citizen Info
            citizen_name = validated_data.get("citizen_name") or (user.get_full_name() if user and hasattr(user, 'get_full_name') and user.get_full_name() else getattr(user, 'username', 'Citizen'))
            citizen_phone = validated_data.get("citizen_phone") or getattr(user, 'phone', '') or "+919876543210"
            citizen_email = validated_data.get("citizen_email") or getattr(user, 'email', '')

            district = validated_data.get("district") or District.objects.first()

            complaint = Complaint.objects.create(
                tracking_no=tracking_no,
                title=validated_data.get("title") or (category.name if category else "Infrastructure Defect"),
                description=validated_data.get("description", ""),
                category=category,
                department=department,
                citizen_user=user if (user and getattr(user, 'is_authenticated', True)) else None,
                citizen_name=citizen_name,
                citizen_phone=citizen_phone,
                citizen_email=citizen_email,
                is_identity_masked=validated_data.get("is_identity_masked", False),
                status=ComplaintStatus.SUBMITTED,
                priority=priority,
                sla_target_hours=sla_hours,
                sla_deadline=sla_deadline,
                latitude=lat,
                longitude=lng,
                geom=geos_point,
                district=district,
                block=validated_data.get("block"),
                village_ward=validated_data.get("village_ward"),
                nearest_facility=nearest_fac,
                nearest_facility_name=nearest_fac_name,
                nearest_facility_distance_m=nearest_fac_dist,
            )

            # Process Evidence files if attached
            if files:
                for file_obj in files:
                    ComplaintEvidence.objects.create(
                        complaint=complaint,
                        file=file_obj,
                        file_name=file_obj.name,
                        file_type="IMAGE" if file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) else "DOCUMENT",
                        stage="SUBMISSION",
                        uploaded_by=user if (user and getattr(user, 'is_authenticated', True)) else None,
                        latitude=lat,
                        longitude=lng,
                        is_geotag_verified=True,
                        distance_from_pin_m=0.0
                    )

            # Audit Timeline Log
            cls.log_timeline(
                complaint=complaint,
                action="SUBMITTED",
                performer=user,
                from_status=None,
                to_status=ComplaintStatus.SUBMITTED,
                remarks=f"Complaint created and auto-routed to {department.name} queue."
            )

            # Dispatch Notification to Dept Officer / Head
            dept_officers = User.objects.filter(department=department)[:5]
            for off in dept_officers:
                cls.dispatch_notification(complaint, off, f"New ticket {complaint.tracking_no} assigned to {department.name}.")

            return complaint

    @classmethod
    def assign_complaint(cls, complaint, performer, target_officer, remarks=""):
        old_status = complaint.status
        complaint.assigned_officer = target_officer
        complaint.status = ComplaintStatus.ASSIGNED
        complaint.save()

        cls.log_timeline(complaint, "ASSIGNED", performer, old_status, ComplaintStatus.ASSIGNED, remarks=remarks)
        cls.dispatch_notification(complaint, target_officer, f"Ticket {complaint.tracking_no} has been assigned to you.")
        return complaint

    @classmethod
    def accept_complaint(cls, complaint, performer, remarks=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.ACCEPTED
        complaint.save()

        cls.log_timeline(complaint, "ACCEPTED", performer, old_status, ComplaintStatus.ACCEPTED, remarks=remarks)
        return complaint

    @classmethod
    def start_inspection(cls, complaint, performer, assigned_inspector=None, remarks=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.INSPECTION_STARTED
        if assigned_inspector:
            complaint.assigned_inspector = assigned_inspector
        complaint.save()

        cls.log_timeline(complaint, "INSPECTION_STARTED", performer, old_status, ComplaintStatus.INSPECTION_STARTED, remarks=remarks)
        if assigned_inspector:
            cls.dispatch_notification(complaint, assigned_inspector, f"Assigned for site inspection on ticket {complaint.tracking_no}.")
        return complaint

    @classmethod
    def upload_evidence(cls, complaint, performer, files, stage="INSPECTION", remarks="", lat=None, lng=None):
        created_evidences = []
        for file_obj in files:
            is_valid_dist = True
            dist_m = 0.0
            if lat and lng and complaint.latitude and complaint.longitude:
                dist_m = calculate_haversine_distance_m(lat, lng, complaint.latitude, complaint.longitude)
                is_valid_dist = dist_m <= 100.0

            ev = ComplaintEvidence.objects.create(
                complaint=complaint,
                file=file_obj,
                file_name=file_obj.name,
                file_type="IMAGE" if file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) else "DOCUMENT",
                stage=stage,
                uploaded_by=performer if (performer and getattr(performer, 'is_authenticated', True)) else None,
                latitude=lat or complaint.latitude,
                longitude=lng or complaint.longitude,
                is_geotag_verified=is_valid_dist,
                distance_from_pin_m=dist_m
            )
            created_evidences.append(ev)

        old_status = complaint.status
        if complaint.status in [ComplaintStatus.INSPECTION_STARTED, ComplaintStatus.ACCEPTED]:
            complaint.status = ComplaintStatus.EVIDENCE_UPLOADED
            complaint.save()

        cls.log_timeline(complaint, "EVIDENCE_UPLOADED", performer, old_status, complaint.status, remarks=remarks or f"Uploaded {len(files)} evidence file(s).")
        return created_evidences

    @classmethod
    def resolve_complaint(cls, complaint, performer, resolution_summary, remarks=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.RESOLVED
        complaint.resolution_summary = resolution_summary
        complaint.resolved_at = timezone.now()
        complaint.save()

        cls.log_timeline(complaint, "RESOLVED", performer, old_status, ComplaintStatus.RESOLVED, remarks=resolution_summary)
        cls.dispatch_notification(complaint, complaint.citizen_user, f"Ticket {complaint.tracking_no} resolved! Please provide your feedback.")
        return complaint

    @classmethod
    def citizen_feedback(cls, complaint, citizen_user, rating, feedback_comment=""):
        complaint.rating = rating
        complaint.feedback_comment = feedback_comment
        complaint.save()

        cls.log_timeline(complaint, "CITIZEN_FEEDBACK", citizen_user, complaint.status, complaint.status, remarks=f"Rating: {rating}/5 stars. {feedback_comment}")
        return complaint

    @classmethod
    def close_complaint(cls, complaint, performer, remarks=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.CLOSED
        complaint.closed_at = timezone.now()
        complaint.save()

        cls.log_timeline(complaint, "CLOSED", performer, old_status, ComplaintStatus.CLOSED, remarks=remarks)
        return complaint

    @classmethod
    def reopen_complaint(cls, complaint, citizen_user, reason=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.REOPENED
        complaint.save()

        cls.log_timeline(complaint, "REOPENED", citizen_user, old_status, ComplaintStatus.REOPENED, remarks=reason)
        return complaint

    @classmethod
    def transfer_complaint(cls, complaint, performer, new_department, reason=""):
        old_status = complaint.status
        complaint.department = new_department
        complaint.assigned_officer = None
        complaint.assigned_inspector = None
        complaint.status = ComplaintStatus.TRANSFERRED
        complaint.transfer_reason = reason
        complaint.save()

        cls.log_timeline(complaint, "TRANSFERRED", performer, old_status, ComplaintStatus.TRANSFERRED, remarks=f"Transferred to {new_department.name}. Reason: {reason}")
        return complaint

    @classmethod
    def escalate_complaint(cls, complaint, performer, reason=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.ESCALATED
        complaint.escalation_reason = reason
        complaint.save()

        cls.log_timeline(complaint, "ESCALATED", performer, old_status, ComplaintStatus.ESCALATED, remarks=f"Escalated: {reason}")
        
        # Notify District Authorities (ADM / DM)
        adm_users = User.objects.filter(role__code__in=["ADM", "DISTRICT_COLLECTOR", "DISTRICT_MAGISTRATE"])[:5]
        for adm in adm_users:
            cls.dispatch_notification(complaint, adm, f"ESCALATED TICKET: {complaint.tracking_no} ({complaint.department.name}).")
        
        return complaint

    @classmethod
    def reject_complaint(cls, complaint, performer, reason=""):
        old_status = complaint.status
        complaint.status = ComplaintStatus.REJECTED
        complaint.rejection_reason = reason
        complaint.save()

        cls.log_timeline(complaint, "REJECTED", performer, old_status, ComplaintStatus.REJECTED, remarks=f"Rejected: {reason}")
        cls.dispatch_notification(complaint, complaint.citizen_user, f"Ticket {complaint.tracking_no} rejected. Reason: {reason}")
        return complaint
