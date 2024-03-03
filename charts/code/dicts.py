import pandas as pd

datadir = '../data/'

def _convert_helper(df, oldcol, newcol, dictfile):
    # read dictionary
    filename = datadir + dictfile

    with open(filename, 'r') as f:
        lines = f.readlines()

    make_dict = []
    for line in lines:
        line = line.strip()
        items = line.split(',', 1)
        itm = items[0].strip()
        if len(items) > 1:
            make_dict.append((itm, items[1].strip()))
        else:
            make_dict.append((itm, itm))

    newdat = df[oldcol].copy()
    for (m_in, m_out) in make_dict:
        newdat[newdat.str.startswith(m_in)] = m_out
    df[newcol] = newdat

def convert_make(df, oldcol='tozeret_nm', newcol='make'):
    _convert_helper(df, oldcol, newcol, 'makes_dict.csv')

def convert_color(df, oldcol='tzeva_rechev', newcol='color'):
    _convert_helper(df, oldcol, newcol, 'color_dict.csv')

make_heb_to_eng= {
    'טסלה': 'Tesla',
    'BYD': 'BYD',
    'Geely': 'Geely',
    'יונדאי': 'Hyundai',
    'MG': 'MG',
    'Aiways': 'Aiways',
    'סקודה': 'Skoda',
    'מרצדס': 'Mercedes',
    'אאודי': 'Audi',
    'סרס': 'Seres',
    'סקיוול': 'Skywell',
    'קיה': 'Kia',
    'BMW': 'BMW',
    'פיאט': 'Fiat',
    'מקסוס': 'Lexus',
    'רנו': 'Renault',
    "פיג'ו": 'Peugeot',
    'GAC': 'GAC',
    'וולבו': 'Volvo',
    'טויוטה': 'Toyota',
    'סיטרואן': 'Citroën',
    'ניסאן': 'Nissan',
    'ליפמוטור': 'Lifan',
    'אורה': 'Ora',
    'פולקסווגן': 'Volkswagen',
    'אופל': 'Opel',
    'לקסוס': 'Lexus',
    'פורד': 'Ford',
    'פולסטאר': 'Polestar',
    'FAW': 'FAW',
    'פורשה': 'Porsche',
    'יגואר': 'Jaguar',
    'סמארט': 'Smart',
    'Voyah': 'Voyah',
    'LEVC': 'LEVC',
    'סיאט': 'Seat',
    'דאציה': 'Dacia',
    'DS': 'DS',
    'מזדה': 'Mazda',
    'שברולט': 'Chevrolet',
    'סנטרו סין': 'Centro China',
    'EVEASY': 'EVEASY',
    'מיצובישי': 'Mitsubishi',
    'גרייט וול': 'Great Wall',
    'רובר': 'Rover',
    'סובארו': 'Subaru',
    'קרייזלר': 'Chrysler',
    'הונדה': 'Honda',
    'סוזוקי': 'Suzuki',
    'דייהטסו': 'Daihatsu',
    'צ\'רי': 'Chery',
}

body_style_heb_to_eng = {
    'פנאי-שטח': 'SUV',
    'סדאן': 'Sedan',
    'הצ\'בק': 'Hatchback',
    'קופה': 'Coupe',
    'קומבי': 'Wagon',
    'MPV': 'MPV',
    'קבריולט': 'Convertible',
    'סטיישן': 'Station Wagon',
    'תא כפול': 'Double Cab',
    'משא אחוד': 'Single Cab',
    'ואן/נוסעים': 'Van',
    'סגור/משלוח': 'Delivery',
    'תא בודד': 'Single Cab',
    'שדה': 'Off-Road'
}

fuel_heb_to_eng = {
    'דיזל': 'diesel',
    'בנזין': 'gasoline',
    'חשמל/בנזין': 'electric/gasoline',
    'חשמל': 'electric',
    'חשמל/דיזל': 'electric/diesel',
    'לא ידוע קוד ': 'Unknown Code',
    'גפמ"': 'LPG'
}

technology_heb_to_eng = {
    'הנעה רגילה': 'ICE',
    'PLUG IN': 'PHEV',
    'רכב חשמלי': 'Electric',
    'היברידי רגיל': 'Hybrid'
}

