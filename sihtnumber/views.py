import os
from pathlib import Path, PurePath
import pickle
import re

from django.shortcuts import render

from .forms import OtsiSihtnumberForm

def sihtnumbrid_to_dict():
    path = os.path.join(os.getcwd(), 'sihtnumber')
    print(path)
    filename = os.path.join(path, 'data.pickle')
    if os.path.isfile(filename):
        with open(filename, 'rb') as f:
            # The protocol version used is detected automatically, so we do not
            # have to specify it.
            sihtnumbrid = pickle.load(f)
    else:
        counter = 0
        csv_file = os.path.join(path, 'sihtnumbrid.csv')
        with open(csv_file, 'r', encoding='utf-8') as f:
            f.readline() # Jätame päise vahele
            sihtnumbrid = dict()
            while True:
                row = f.readline()
                counter += 1
                if counter % 100000 == 0:
                    print(counter)
                if row:
                    splitid = row.split(';')
                    aadress = re.sub(r"\s+", "", splitid[3]).lower()
                    sihtnumber = splitid[1]
                    sihtnumbrid[aadress] = sihtnumber
                else:
                    break
            with open(filename, 'wb') as f:
                # Pickle the 'sihtnumbrid' dictionary using the highest protocol available.
                pickle.dump(sihtnumbrid, f, pickle.HIGHEST_PROTOCOL)
    return sihtnumbrid

# otsivorm
def otsi_sihtnumber(request):
    # If this is a POST request then process the Form data
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request (binding):
        form = OtsiSihtnumberForm(request.POST)
        vastus = []
        # Check if the form is valid:
        if form.is_valid():
            aadressid = form.cleaned_data['aadressid']
            aadressi_loend = aadressid.splitlines()
            sihtnumbrid = sihtnumbrid_to_dict()
            vastus = [
                sihtnumbrid.get(re.sub(r"\s+", "", aadress).lower(), 'ei leidnud')
                for aadress
                in aadressi_loend
            ]

    # If this is a GET (or any other method) create the default form.
    else:
        vastus = []
        form = OtsiSihtnumberForm(initial={'aadressid': ''})

    context = {
        'form': form,
        'vastus': vastus
    }

    return render(request, 'sihtnumber/otsi_sihtnumber.html', context)
