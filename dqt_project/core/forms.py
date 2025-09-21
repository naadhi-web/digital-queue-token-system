from django import forms
from django.contrib.auth.models import User
from .models import QueueSlot
from django.utils import timezone


# ----------------------------
# User Registration
# ----------------------------
class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data


# ----------------------------
# General Booking Form
# ----------------------------
class BookingForm(forms.Form):
    slot = forms.ModelChoiceField(
        queryset=QueueSlot.objects.none(),
        label="Select Slot",
        widget=forms.Select(attrs={"class": "form-select"})  # ✅ Bootstrap styling
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["slot"].queryset = QueueSlot.objects.filter(
            date__gte=today
        ).order_by("date", "start_time")


# ----------------------------
# QueueSlot Management Form (Admin/Staff)
# ----------------------------
class QueueSlotForm(forms.ModelForm):
    class Meta:
        model = QueueSlot
        fields = ["date", "start_time", "end_time", "max_tokens"]  # removed service
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# ----------------------------
# Reschedule Token
# ----------------------------
class RescheduleForm(forms.Form):
    new_slot = forms.ModelChoiceField(queryset=QueueSlot.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["new_slot"].queryset = QueueSlot.objects.filter(
            date__gte=today
        ).order_by("date", "start_time")


# ----------------------------
# Library Booking Form
# ----------------------------
class LibrarySlotForm(forms.ModelForm):
    class Meta:
        model = QueueSlot
        fields = ["service", "date", "start_time", "end_time", "max_tokens"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].initial = 'library'
        self.fields['service'].disabled = True
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Only show library slots
        self.fields['service'].queryset = QueueSlot.objects.filter(service="library")


# ----------------------------
# Canteen Booking Form
# ----------------------------
class CanteenSlotForm(forms.ModelForm):
    class Meta:
        model = QueueSlot
        fields = ['service', 'date', 'start_time', 'end_time']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Only show canteen slots
        self.fields['service'].queryset = QueueSlot.objects.filter(service="canteen")
