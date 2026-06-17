import re
import unicodedata
from django.db import migrations, transaction, IntegrityError


def _norm(nombre):
    s = str(nombre or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


# Provincia -> cantones (nombres en mayúscula, con acentos)
DATA = {
    'AZUAY': ['SEVILLA DE ORO', 'PAUTE', 'GUACHAPALA', 'EL PAN', 'GUALACEO', 'CHORDELEG', 'SÍGSIG', 'CUENCA', 'SANTA ISABEL', 'PUCARÁ', 'CAMILO PONCE ENRÍQUEZ', 'SAN FERNANDO', 'GIRÓN', 'NABÓN', 'OÑA'],
    'BOLÍVAR': ['GUARANDA', 'LAS NAVES', 'ECHEANDÍA', 'CALUMA', 'CHIMBO', 'SAN MIGUEL', 'CHILLANES'],
    'CAÑAR': ['LA TRONCAL', 'CAÑAR', 'SUSCAL', 'EL TAMBO', 'AZOGUES', 'BIBLIÁN', 'DÉLEG'],
    'CARCHI': ['TULCÁN', 'MIRA', 'ESPEJO', 'MONTÚFAR', 'SAN PEDRO DE HUACA', 'BOLÍVAR'],
    'CHIMBORAZO': ['GUANO', 'PENIPE', 'RIOBAMBA', 'COLTA', 'CHAMBO', 'PALLATANGA', 'GUAMOTE', 'ALAUSÍ', 'CUMANDÁ', 'CHUNCHI'],
    'COTOPAXI': ['SIGCHOS', 'LA MANÁ', 'LATACUNGA', 'SAQUISILÍ', 'PUJILÍ', 'PANGUA', 'SALCEDO'],
    'IMBABURA': ['IBARRA', 'SAN MIGUEL DE URCUQUÍ', 'COTACACHI', 'ANTONIO ANTE', 'OTAVALO', 'PIMAMPIRO'],
    'LOJA': ['SARAGURO', 'LOJA', 'CHAGUARPAMBA', 'OLMEDO', 'CATAMAYO', 'PALTAS', 'PUYANGO', 'PINDAL', 'CELICA', 'ZAPOTILLO', 'MACARÁ', 'SOZORANGA', 'CALVAS', 'GONZANAMÁ', 'QUILANGA', 'ESPÍNDOLA'],
    'PICHINCHA': ['QUITO', 'PEDRO VICENTE MALDONADO', 'SAN MIGUEL DE LOS BANCOS', 'DISTRITO METROPOLITANO DE QUITO', 'PEDRO MONCAYO', 'CARAPUNGO', 'CAYAMBE', 'RUMIÑAHUI', 'MEJÍA'],
    'TUNGURAHUA': ['AMBATO', 'PÍLLARO', 'PATATE', 'BAÑOS DE AGUA SANTA', 'SAN PEDRO DE PELILEO', 'CEVALLOS', 'TISALEO', 'MOCHA', 'PELILEO', 'QUERO'],
    'ESMERALDAS': ['SAN LORENZO', 'ELOY ALFARO', 'RIOVERDE', 'ESMERALDAS', 'MUISNE', 'ATACAMES', 'QUININDÉ'],
    'MANABÍ': ['PEDERNALES', 'CHONE', 'FLAVIO ALFARO', 'EL CARMEN', 'JAMA', 'SAN VICENTE', 'SUCRE', 'TOSAGUA', 'ROCAFUERTE', 'JUNÍN', 'BOLÍVAR', 'PICHINCHA', 'PORTOVIEJO', 'JARAMIJÓ', 'MANTA', 'MONTECRISTI', 'SANTA ANA', 'JIPIJAPA', 'VEINTICUATRO DE MAYO', 'OLMEDO', 'PUERTO LÓPEZ', 'PAJÁN'],
    'GUAYAS': ['EL EMPALME', 'BALZAR', 'COLIMES', 'PALESTINA', 'SANTA LUCÍA', 'PEDRO CARBO', 'ISIDRO AYORA', 'LOMAS DE SARGENTILLO', 'NOBOL', 'DAULE', 'SALITRE', 'SAMBORONDÓN', 'SAN JACINTO DE YAGUACHI', 'ALFREDO BAQUERIZO MORENO', 'MILAGRO', 'SIMÓN BOLÍVAR', 'NARANJITO', 'GENERAL ANTONIO ELIZALDE', 'CORONEL MARCELINO MARIDUEÑA', 'EL TRIUNFO', 'DURÁN', 'GUAYAQUIL', 'PLAYAS', 'NARANJAL', 'BALAO'],
    'EL ORO': ['EL GUABO', 'MACHALA', 'PASAJE', 'CHILLA', 'ZARUMA', 'SANTA ROSA', 'ATAHUALPA', 'ARENILLAS', 'HUAQUILLAS', 'LAS LAJAS', 'MARCABELÍ', 'BALSAS', 'PIÑAS', 'PORTOVELO'],
    'LOS RÍOS': ['BUENA FE', 'VALENCIA', 'QUEVEDO', 'QUINSALOMA', 'PALENQUE', 'MOCACHE', 'VENTANAS', 'VINCES', 'BABA', 'PUEBLOVIEJO', 'URDANETA', 'BABAHOYO', 'MONTALVO'],
    'SANTA ELENA': ['SANTA ELENA', 'LA LIBERTAD', 'SALINAS'],
    'SANTO DOMINGO DE LOS TSÁCHILAS': ['LA CONCORDIA', 'SANTO DOMINGO'],
    'NAPO': ['EL CHACO', 'QUIJOS', 'ARCHIDONA', 'TENA', 'CARLOS JULIO AROSEMENA TOLA'],
    'ORELLANA': ['LORETO', 'FRANCISCO DE ORELLANA', 'LA JOYA DE LOS SACHAS', 'AGUARICO'],
    'PASTAZA': ['MERA', 'SANTA CLARA', 'ARAJUNO', 'PASTAZA'],
    'SUCUMBÍOS': ['SUCUMBÍOS', 'GONZALO PIZARRO', 'CASCALES', 'LAGO AGRIO', 'PUTUMAYO', 'CUYABENO', 'SHUSHUFINDI'],
    'MORONA SANTIAGO': ['PALORA', 'PABLO SEXTO', 'HUAMBOYA', 'MORONA', 'TAISHA', 'SUCÚA', 'SANTIAGO', 'LOGROÑO', 'TIWINTZA', 'LIMÓN INDANZA', 'SAN JUAN BOSCO', 'GUALAQUIZA', 'SEVILLA DON BOSCO'],
    'ZAMORA CHINCHIPE': ['YACUAMBI', 'YANTZAZA', 'EL PANGUI', 'ZAMORA', 'CENTINELA DEL CÓNDOR', 'PAQUISHA', 'NANGARITZA', 'PALANDA', 'CHINCHIPE'],
    'GALÁPAGOS': ['ISABELA', 'SAN CRISTÓBAL', 'SANTA CRUZ'],
}


def seed(apps, schema_editor):
    Provincia = apps.get_model('CoreFisica', 'Provincia')
    Canton = apps.get_model('CoreFisica', 'Canton')

    # Mapas normalizados de lo existente
    prov_por_norm = {}
    for p in Provincia.objects.all():
        prov_por_norm.setdefault(_norm(p.nombre), p)

    for prov_nombre, cantones in DATA.items():
        key = _norm(prov_nombre)
        prov = prov_por_norm.get(key)
        if not prov:
            try:
                with transaction.atomic():
                    prov = Provincia.objects.create(nombre=prov_nombre)
            except IntegrityError:
                prov = Provincia.objects.filter(nombre=prov_nombre).first()
            if not prov:
                continue
            prov_por_norm[key] = prov

        # cantones existentes de esta provincia (normalizados)
        existentes = {_norm(c.nombre) for c in Canton.objects.filter(provincia_id=prov.id)}
        for cant_nombre in cantones:
            if _norm(cant_nombre) in existentes:
                continue
            try:
                with transaction.atomic():
                    Canton.objects.create(nombre=cant_nombre, provincia_id=prov.id)
            except IntegrityError:
                pass
            existentes.add(_norm(cant_nombre))


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0114_merge_provincias_guiones'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_noop),
    ]
