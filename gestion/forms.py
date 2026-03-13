from django import forms
from .models import Societe, Agent, Affectation, HeureTransport, Chauffeur

class SocieteForm(forms.ModelForm):
    class Meta:
        model = Societe
        fields = ['nom', 'matricule_fiscale', 'adresse', 'telephone', 'email', 'contact_personne']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la société'}),
            'matricule_fiscale': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matricule fiscale'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Adresse complète'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'contact_personne': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Personne à contacter'}),
        }
        labels = {
            'nom': 'Nom de la société *',
            'matricule_fiscale': 'Matricule fiscale',
            'adresse': 'Adresse',
            'telephone': 'Téléphone',
            'email': 'Email',
            'contact_personne': 'Personne à contacter',
        }

class SocieteModificationForm(forms.ModelForm):
    class Meta:
        model = Societe
        fields = ['nom', 'matricule_fiscale', 'adresse', 'telephone', 'email', 'contact_personne']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule_fiscale': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_personne': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ChauffeurForm(forms.ModelForm):
    class Meta:
        model = Chauffeur
        fields = ['nom', 'type_chauffeur', 'telephone', 'numero_identite', 'numero_voiture', 'societe', 'prix_course_par_defaut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'type_chauffeur': forms.Select(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_identite': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_voiture': forms.TextInput(attrs={'class': 'form-control'}),
            'societe': forms.TextInput(attrs={'class': 'form-control'}),
            'prix_course_par_defaut': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class UploadFileForm(forms.Form):
    fichier_planning = forms.FileField(
        label='Fichier Excel de Planning',
        help_text='Telechargez le fichier EMS.xlsx'
    )

class FiltreForm(forms.Form):
    JOURS_CHOICES = [
        ('Tous', 'Tous les jours'),
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
        ('Dimanche', 'Dimanche'),
    ]
    
    TYPE_TRANSPORT_CHOICES = [
        ('tous', 'Tous les types'),
        ('ramassage', 'Ramassage seulement'),
        ('depart', 'Départ seulement'),
    ]
    
    FILTRE_AGENTS_CHOICES = [
        ('tous', 'Tous les agents'),
        ('complets', 'Agents complets seulement'),
        ('incomplets', 'Agents incomplets seulement'),
    ]
    
    jour = forms.ChoiceField(choices=JOURS_CHOICES, initial='Tous', widget=forms.Select(attrs={'class': 'form-control'}))
    type_transport = forms.ChoiceField(choices=TYPE_TRANSPORT_CHOICES, initial='tous', widget=forms.Select(attrs={'class': 'form-control'}))
    heure_ete = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    filtre_agents = forms.ChoiceField(choices=FILTRE_AGENTS_CHOICES, initial='tous', required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    heure_specifique = forms.IntegerField(required=False, widget=forms.HiddenInput())  # AJOUTÉ
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Les heures seront chargées dynamiquement via JavaScript
        # On crée des champs vides qui seront remplis après la sélection du type de transport
        pass

class FiltreDateForm(forms.Form):
    date_debut = forms.DateField(
        label='Date début',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_fin = forms.DateField(
        label='Date fin', 
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

class ImportAgentForm(forms.Form):
    fichier_excel = forms.FileField(
        label='Fichier Excel des agents',
        help_text='Téléchargez un fichier Excel au format info.xlsx'
    )

class AgentForm(forms.ModelForm):
    societe_select = forms.ModelChoiceField(
        queryset=Societe.objects.all().order_by('nom'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Société (liste)"
    )
    societe_texte = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ou entrez le nom de la société'}),
        label="Société (texte)"
    )
    
    class Meta:
        model = Agent
        fields = ['nom', 'adresse', 'telephone', 'voiture_personnelle']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.societe:
                self.fields['societe_select'].initial = self.instance.societe
            else:
                self.fields['societe_texte'].initial = self.instance.societe_texte

    def save(self, commit=True):
        agent = super().save(commit=False)
        societe_select = self.cleaned_data.get('societe_select')
        societe_texte = self.cleaned_data.get('societe_texte')
        
        if societe_select:
            agent.societe = societe_select
            agent.societe_texte = None
        elif societe_texte:
            agent.societe = None
            agent.societe_texte = societe_texte
        else:
            agent.societe = None
            agent.societe_texte = None
            
        if commit:
            agent.save()
        return agent

class AgentModificationForm(forms.ModelForm):
    societe_select = forms.ModelChoiceField(
        queryset=Societe.objects.all().order_by('nom'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Société (liste)"
    )
    societe_texte = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ou entrez le nom de la société'}),
        label="Société (texte)"
    )
    
    class Meta:
        model = Agent
        fields = ['nom', 'adresse', 'telephone', 'voiture_personnelle']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.societe:
                self.fields['societe_select'].initial = self.instance.societe
            else:
                self.fields['societe_texte'].initial = self.instance.societe_texte

    def save(self, commit=True):
        agent = super().save(commit=False)
        societe_select = self.cleaned_data.get('societe_select')
        societe_texte = self.cleaned_data.get('societe_texte')
        
        if societe_select:
            agent.societe = societe_select
            agent.societe_texte = None
        elif societe_texte:
            agent.societe = None
            agent.societe_texte = societe_texte
        else:
            agent.societe = None
            agent.societe_texte = None
            
        if commit:
            agent.save()
        return agent

class AffectationMultipleForm(forms.Form):
    chauffeur = forms.ModelChoiceField(
        queryset=Chauffeur.objects.filter(actif=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Chauffeur *"
    )
    heure = forms.CharField(
        widget=forms.HiddenInput(),
        label="Heure *"
    )
    type_transport = forms.ChoiceField(
        choices=[('', 'Sélectionner le type'), ('ramassage', 'Ramassage'), ('depart', 'Départ')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Type Transport *"
    )
    jour = forms.ChoiceField(
        choices=[
            ('', 'Sélectionner un jour'),
            ('Lundi', 'Lundi'),
            ('Mardi', 'Mardi'),
            ('Mercredi', 'Mercredi'),
            ('Jeudi', 'Jeudi'),
            ('Vendredi', 'Vendredi'),
            ('Samedi', 'Samedi'),
            ('Dimanche', 'Dimanche')
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Jour *"
    )
    agents = forms.CharField(
        widget=forms.HiddenInput(),
        label="Agents"
    )

    def clean_heure(self):
        "Convertit la valeur d'heure en entier pour la validation"
        heure = self.cleaned_data.get('heure')
        if heure:
            try:
                return int(heure)
            except (ValueError, TypeError):
                raise forms.ValidationError("Heure invalide")
        return heure

class FiltreForm(forms.Form):
    JOURS_CHOICES = [
        ('Tous', 'Tous les jours'),
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
        ('Dimanche', 'Dimanche'),
    ]
    
    TYPE_TRANSPORT_CHOICES = [
        ('tous', 'Tous les types'),
        ('ramassage', 'Ramassage seulement'),
        ('depart', 'Départ seulement'),
    ]
    
    FILTRE_AGENTS_CHOICES = [
        ('tous', 'Tous les agents'),
        ('complets', 'Agents complets seulement'),
        ('incomplets', 'Agents incomplets seulement'),
    ]
    
    jour = forms.ChoiceField(choices=JOURS_CHOICES, initial='Tous', widget=forms.Select(attrs={'class': 'form-control'}))
    type_transport = forms.ChoiceField(choices=TYPE_TRANSPORT_CHOICES, initial='tous', widget=forms.Select(attrs={'class': 'form-control'}))
    heure_ete = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    filtre_agents = forms.ChoiceField(choices=FILTRE_AGENTS_CHOICES, initial='tous', required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Les heures seront chargées dynamiquement via JavaScript
        # On crée des champs vides qui seront remplis après la sélection du type de transport
        pass
    heure_specifique = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
