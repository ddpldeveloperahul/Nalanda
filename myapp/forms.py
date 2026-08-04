from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from myapp.models import User


class CustomUserCreationForm(UserCreationForm):
    """
    Custom User Creation Form for Django Admin and Form views.
    Includes Enterprise assignment fields (Role, State, District, Department, Designation, Phone).
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "state",
            "district",
            "department",
            "designation",
            "phone",
        )


    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        department = cleaned_data.get("department")

        if role and (role.code in ["CITIZEN_REGISTERED", "CITIZEN_ANONYMOUS"] or role.scope_level in ["SELF", "ANONYMOUS"]):
            if department:
                raise forms.ValidationError({"department": "Department cannot be assigned to a Citizen role."})
            cleaned_data["department"] = None
            cleaned_data["designation"] = ""

        return cleaned_data


class CustomUserChangeForm(UserChangeForm):
    """
    Custom User Change Form for Django Admin and Form views.
    """
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        department = cleaned_data.get("department")

        if role and (role.code in ["CITIZEN_REGISTERED", "CITIZEN_ANONYMOUS"] or role.scope_level in ["SELF", "ANONYMOUS"]):
            if department:
                raise forms.ValidationError({"department": "Department cannot be assigned to a Citizen role."})
            cleaned_data["department"] = None
            cleaned_data["designation"] = ""

        return cleaned_data
