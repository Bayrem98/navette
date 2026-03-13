from django import template

register = template.Library()

@register.filter
def divisibleby(value, arg):
   
    try:
        if float(arg) == 0:
            return 0.0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

@register.filter(name='multiply')
def multiply(value, arg):
    
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0.0

@register.filter
def get_prix_par_societe_reel(course):
   
    try:
        # Si la course a un prix total défini
        if hasattr(course, 'prix_total') and course.prix_total and float(course.prix_total) > 0:
            prix_reel = float(course.prix_total)
        else:
            # Sinon, utiliser le prix par défaut
            prix_reel = float(course.get_prix_course())
        
        # Compter le nombre de sociétés uniques
        societes = course.get_societes_dans_course()
        societes_count = len(societes) if societes else 1
        
        # Calculer le prix par société
        prix_par_societe = prix_reel / societes_count if societes_count > 0 else prix_reel
        
        return round(prix_par_societe, 2)
        
    except Exception as e:
        print(f"Erreur dans get_prix_par_societe_reel: {e}")
        return 0.0

@register.filter
def get_prix_course_reel(course):
   
    try:
        if hasattr(course, 'prix_total') and course.prix_total and float(course.prix_total) > 0:
            return float(course.prix_total)
        else:
            return float(course.get_prix_course())
    except:
        return 0.0

@register.filter
def get_item(dictionary, key):
    
    return dictionary.get(key, '')

@register.filter
def select_type(list, type_name):
   
    return [item for item in list if item.get('type_transport') == type_name]

@register.filter
def get_affectations_course(course):
    
    return course.affectation_set.all()

@register.filter
def sum_attr(list, attr_name):
  
    total = 0
    for item in list:
        value = item.get(attr_name, 0)
        if isinstance(value, (int, float)):
            total += value
    return round(total, 2)

@register.filter
def get_societe_info(societe_nom):
  
    try:
        from gestion.models import Societe
        societe = Societe.objects.filter(nom=societe_nom).first()
        if societe:
            return {
                'matricule_fiscale': societe.matricule_fiscale,
                'adresse': societe.adresse,
                'telephone': societe.telephone,
                'email': societe.email,
                'contact_personne': societe.contact_personne
            }
        return None
    except:
        return None

# Filtres mathématiques additionnels
@register.filter
def add(value, arg):
  
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def subtract(value, arg):
   
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def divide(value, arg):
   
    try:
        if float(arg) == 0:
            return 0.0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

@register.filter
def percentage(value, arg):
  
    try:
        if float(arg) == 0:
            return 0.0
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError):
        return 0.0
