from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.widgets import FilteredSelectMultiple
from core.models import Practice, Agent


User = get_user_model()


# Create ModelForm based on the Group / Users model from Django
class PracticeAdminForm(forms.ModelForm):
    class Meta:
        model = Practice
        exclude = []

    # Add the agents field.
    agents = forms.ModelMultipleChoiceField(
        queryset=Agent.objects.all(),
        required=False,
        # Use the pretty 'filter_horizontal widget'.
        widget=FilteredSelectMultiple("agents", False),
    )

    def __init__(self, *args, **kwargs):
        # Do the normal form initialisation.
        super().__init__(*args, **kwargs)
        # If it is an existing practice (saved objects have a pk).
        if self.instance.pk:
            # Populate the agents field with the current Practice agents.
            self.fields["agents"].initial = self.instance.agent_set.all()

    def save_m2m(self):
        # Add the agents to the Practice.
        self.instance.agent_set.set(self.cleaned_data["agents"])

    def save(self, *args, **kwargs):
        # Default save
        instance = super(PracticeAdminForm, self).save()
        # Save many-to-many data
        self.save_m2m()
        return instance
