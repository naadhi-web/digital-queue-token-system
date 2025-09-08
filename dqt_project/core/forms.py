from django import forms
from django.contrib.auth.models import User
from .models import QueueSlot
from django.utils import timezone

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


class BookingForm(forms.Form):
    slot = forms.ModelChoiceField(queryset=QueueSlot.objects.none(), empty_label=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["slot"].queryset = QueueSlot.objects.filter(date__gte=today).order_by("date","start_time")

class QueueSlotForm(forms.ModelForm):
    class Meta:
        model = QueueSlot
        fields = ["name","queue_type","date","start_time","end_time","max_tokens","avg_service_minutes"]

class RescheduleForm(forms.Form):
    new_slot = forms.ModelChoiceField(queryset=QueueSlot.objects.none())
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["new_slot"].queryset = QueueSlot.objects.filter(date__gte=today).order_by("date","start_time")

