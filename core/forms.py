from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.widgets import FilteredSelectMultiple
from core.models import Practice


User = get_user_model()


# Create ModelForm based on the Practice model.
class PracticeAdminForm(forms.ModelForm):
    class Meta:
        model = Practice
        exclude = []

    # Add the users field.
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        # Use the pretty 'filter_horizontal widget'.
        widget=FilteredSelectMultiple("users", False),
    )

    def __init__(self, *args, **kwargs):
        # Do the normal form initialisation.
        super(PracticeAdminForm, self).__init__(*args, **kwargs)
        # If it is an existing practice (saved objects have a pk).
        if self.instance.pk:
            # Populate the users field with the current Practice users.
            self.fields["users"].initial = self.instance.user_set.all()

    def save_m2m(self):
        # Add the users to the Practice.
        self.instance.user_set.set(self.cleaned_data["users"])

    def save(self, *args, **kwargs):
        # Default save
        instance = super(PracticeAdminForm, self).save()
        # Save many-to-many data
        self.save_m2m()
        return instance
