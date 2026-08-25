"""
Explainable Need-Based Gap & Priority Scoring Engine for Nalanda DDSS.
Uses GapModelVersion weights and multi-dimensional indicator components:
gap_score = w1*demand_gap + w2*capacity_gap + w3*accessibility_gap + w4*infrastructure_gap + w5*hr_gap + w6*medicine_gap + w7*coverage_gap + w8*citizen_feedback_gap
"""
from myapp.models import (
    GapModelVersion, PriorityLocation, Facility, Department, District, Block, VillageWard
)

"""
Explainable Need-Based Gap & Priority Scoring Engine for Nalanda DDSS.
Uses GapModelVersion weights and multi-dimensional indicator components per Department:
gap_score = sum(w_i * component_i)
"""
from myapp.models import (
    GapModelVersion, PriorityLocation, Facility, Department, District, Block, VillageWard
)

class GapPriorityEngine:
    DEPARTMENT_WEIGHT_PROFILES = {
        "HEALTH": {
            "hr_gap": 0.20,
            "infrastructure_gap": 0.20,
            "medicine_gap": 0.15,
            "demand_gap": 0.20,
            "accessibility_gap": 0.15,
            "citizen_feedback_gap": 0.10
        },
        "EDUCATION": {
            "teacher_gap": 0.30,
            "infrastructure_gap": 0.25,
            "student_demand_gap": 0.20,
            "accessibility_gap": 0.15,
            "citizen_feedback_gap": 0.10
        },
        "WATER_RESOURCES": {
            "coverage_gap": 0.35,
            "supply_gap": 0.30,
            "source_availability_gap": 0.25,
            "citizen_feedback_gap": 0.10
        },
        "WATER_SANITATION": {
            "coverage_gap": 0.35,
            "supply_gap": 0.30,
            "source_availability_gap": 0.25,
            "citizen_feedback_gap": 0.10
        },
        "PWD": {
            "road_condition_gap": 0.40,
            "connectivity_gap": 0.30,
            "accessibility_gap": 0.20,
            "citizen_feedback_gap": 0.10
        },
        "PWD_TRANSPORT": {
            "road_condition_gap": 0.40,
            "connectivity_gap": 0.30,
            "accessibility_gap": 0.20,
            "citizen_feedback_gap": 0.10
        }
    }

    DEFAULT_WEIGHTS = {
        "demand_gap": 0.15,
        "capacity_gap": 0.15,
        "accessibility_gap": 0.15,
        "infrastructure_gap": 0.15,
        "hr_gap": 0.15,
        "medicine_gap": 0.10,
        "coverage_gap": 0.10,
        "citizen_feedback_gap": 0.05
    }

    @classmethod
    def get_active_model_version(cls, department=None):
        query = GapModelVersion.objects.filter(is_active=True)
        if department:
            dept_model = query.filter(department=department).first()
            if dept_model:
                return dept_model
        
        fallback = query.first()
        if not fallback:
            code = department.code if department else "ALL"
            weights = cls.DEPARTMENT_WEIGHT_PROFILES.get(code, cls.DEFAULT_WEIGHTS)
            fallback = GapModelVersion.objects.create(
                department=department,
                version=f"v1.0-{code}",
                weights=weights,
                description=f"Approved Gap Model for {code}"
            )
        return fallback

    @classmethod
    def compute_facility_gap(cls, facility):
        dept = facility.department
        dept_code = dept.code if dept and dept.code else "HEALTH"
        model_ver = cls.get_active_model_version(department=dept)
        weights = model_ver.weights or cls.DEPARTMENT_WEIGHT_PROFILES.get(dept_code, cls.DEFAULT_WEIGHTS)

        if dept_code == "EDUCATION":
            edu_ind = facility.education_indicators.first() if hasattr(facility, "education_indicators") else None
            vacancies = edu_ind.teacher_vacancies if edu_ind else 3
            teacher_gap = min(100.0, vacancies * 20.0)
            infra_gap = 75.0 if edu_ind and (not edu_ind.drinking_water_status or not edu_ind.separate_girls_toilet) else 25.0
            student_gap = 65.0 if edu_ind and edu_ind.student_enrolment > 300 else 30.0
            accessibility_gap = 40.0
            feedback_gap = 45.0

            components = {
                "teacher_gap": teacher_gap,
                "infrastructure_gap": infra_gap,
                "student_demand_gap": student_gap,
                "accessibility_gap": accessibility_gap,
                "citizen_feedback_gap": feedback_gap
            }
        elif dept_code in ["WATER_RESOURCES", "WATER_SANITATION"]:
            wtr_ind = facility.water_indicators.first() if hasattr(facility, "water_indicators") else None
            coverage_gap = (100.0 - wtr_ind.household_coverage_percent) if wtr_ind else 35.0
            supply_gap = 80.0 if wtr_ind and wtr_ind.daily_supply_hours < 5.0 else 20.0
            source_gap = (wtr_ind.non_functional_sources_count * 25.0) if wtr_ind else 40.0
            feedback_gap = 30.0

            components = {
                "coverage_gap": coverage_gap,
                "supply_gap": supply_gap,
                "source_availability_gap": source_gap,
                "citizen_feedback_gap": feedback_gap
            }
        else:
            # Default / Health
            indicators = facility.health_indicators.first() if hasattr(facility, "health_indicators") else None
            staffing = facility.staffing_records.all() if hasattr(facility, "staffing_records") else []
            workload = facility.workload_records.first() if hasattr(facility, "workload_records") else None
            medicines = facility.medicine_stocks.all() if hasattr(facility, "medicine_stocks") else []

            demand_gap = 70.0 if workload and workload.capacity_pressure in ["HIGH", "CRITICAL"] else 40.0
            capacity_gap = 80.0 if indicators and indicators.bed_count < 20 else 30.0
            accessibility_gap = 60.0
            infrastructure_gap = 85.0 if indicators and (indicators.oxygen_status != "AVAILABLE" or indicators.icu_bed_count == 0) else 25.0

            vacancies = sum(s.vacancy_count for s in staffing) if staffing else 2
            hr_gap = min(100.0, vacancies * 25.0)

            stockout_count = sum(1 for m in medicines if m.stock_status == "STOCKOUT") if medicines else 0
            medicine_gap = 90.0 if stockout_count > 0 else 20.0
            coverage_gap = 45.0
            citizen_feedback_gap = 50.0

            components = {
                "demand_gap": round(demand_gap, 1),
                "capacity_gap": round(capacity_gap, 1),
                "accessibility_gap": round(accessibility_gap, 1),
                "infrastructure_gap": round(infrastructure_gap, 1),
                "hr_gap": round(hr_gap, 1),
                "medicine_gap": round(medicine_gap, 1),
                "coverage_gap": round(coverage_gap, 1),
                "citizen_feedback_gap": round(citizen_feedback_gap, 1),
            }

        composite_score = sum(components.get(k, 0.0) * weights.get(k, 0.1) for k in components)
        composite_score = round(min(100.0, max(0.0, composite_score)), 1)

        priority = "P4"
        if composite_score >= 75.0:
            priority = "P1"
        elif composite_score >= 60.0:
            priority = "P2"
        elif composite_score >= 40.0:
            priority = "P3"

        reasons = [f"HIGH_{k.upper()}" for k, v in components.items() if v >= 60.0]

        return {
            "facility_id": facility.id,
            "facility_name": facility.name,
            "department_code": dept_code,
            "gap_score": composite_score,
            "priority": priority,
            "components": components,
            "reason_codes": reasons,
            "model_version": model_ver.version,
            "weights_used": weights
        }
