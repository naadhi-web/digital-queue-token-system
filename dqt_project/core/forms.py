from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import QueueSlot, CanteenBooking


# ----------------------------
# User Registration Form
# ----------------------------
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        # Remove help text
        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please use a different email.")
        return email


# ----------------------------
# General Booking Form
# ----------------------------
class BookingForm(forms.Form):
    slot = forms.ModelChoiceField(
        queryset=QueueSlot.objects.none(),
        label="Select Slot",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        service_filter = kwargs.pop('service_filter', None)
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        queryset = QueueSlot.objects.filter(date__gte=today)
        
        if service_filter:
            queryset = queryset.filter(service=service_filter)
            
        self.fields["slot"].queryset = queryset.order_by("date", "start_time")


# ----------------------------
# QueueSlot Management Form
# ----------------------------
class QueueSlotForm(forms.ModelForm):
    class Meta:
        model = QueueSlot
        fields = ["service", "date", "start_time", "end_time", "max_tokens"]
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }


# ----------------------------
# Canteen Time Slot Booking Form
# ----------------------------
class CanteenTimeSlotBookingForm(forms.ModelForm):
    class Meta:
        model = CanteenBooking
        fields = ['date', 'time_slot', 'purpose']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'min': timezone.localdate().isoformat()
            }),
            'time_slot': forms.Select(attrs={'class': 'form-select'}),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Brief purpose of your canteen visit...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.localdate()

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < timezone.localdate():
            raise forms.ValidationError("Cannot book for past dates.")
        return date


# ----------------------------
# Canteen Queue Slot Booking Form
# ----------------------------
class CanteenQueueBookingForm(forms.Form):
    slot = forms.ModelChoiceField(
        queryset=QueueSlot.objects.none(),
        label="Select Canteen Slot",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields['slot'].queryset = QueueSlot.objects.filter(
            service='canteen',
            date__gte=today
        ).order_by('date', 'start_time')