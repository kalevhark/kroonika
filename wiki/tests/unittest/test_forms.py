"""
Unit testid wiki vormide jaoks.

Using: python manage.py test wiki.tests.unittest.test_forms
"""
from datetime import datetime as dt

from django.test import TestCase

from wiki.forms import ArtikkelForm
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt, Viide

class AddArtikkelForm(TestCase):

    def setUp(self) -> None:
        # GIVEN
        self.test_viide = Viide.objects.order_by('?').first()

    def test__forms__empty_kirjeldus(self):
        """
        Testib tühja sisuga vormi mittelubatavust.
        
        :param self: TestCase objekt
        """
        form = ArtikkelForm()
        self.assertFalse(form.is_valid())


    def test__forms__empty_kirjeldus_empty_histdate_error(self):
        """
        Testib tühja kirjeldusega vormi valideerimist, kus hist_date on täidetud.
        """
        form = ArtikkelForm(
            data={
                "kirjeldus": "",
                "hist_date": dt.now(),
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.errors.get("kirjeldus"), None
        )

    def test__forms__hist_month_with_empty_histyear_error(self):
        """
        Testib, kus hist_month on täidetud ja hist_year on tühi.
        """
        form = ArtikkelForm(
            data={
                "hist_month": 5,
            }
        )
        self.assertFalse(form.is_valid())


    def test__forms__hist_month_with_histyear(self):
        """
        Testib, kus hist_month ja hist_year on täidetud.
        """
        form = ArtikkelForm(
            data={
                "hist_month": 5,
                "hist_year": 1990,
            }
        )
        self.assertTrue(form.is_valid())

    
    def test__forms__hist_endmonth_with_empty_hist_endyear_error(self):
        """
        Testib, kus hist_endmonth on täidetud ja hist_endyear on tühi.
        """
        form = ArtikkelForm(
            data={
                "hist_date": dt.now(),
                "hist_endmonth": 5,
            }
        )
        self.assertFalse(form.is_valid())


    def test__forms__hist_endmonth_with_hist_endyear(self):
        """
        Testib, kus hist_endmonth ja hist_endyear on täidetud.
        """
        form = ArtikkelForm(
            data={
                "hist_date": dt.now(),
                "hist_endmonth": 5,
                "hist_endyear": 2000,
            }
        )
        self.assertTrue(form.is_valid())


    def test__forms__viitetag_not_defined(self):
        """
        Testib vormi valideerimist, kui viitetagi pole defineeritud.
        """
        form = ArtikkelForm(
            data={
                "kirjeldus": f"Testi artikkel viidetagita [viide_{self.test_viide.id}]",
                "hist_date": dt.now(),
            }
        )
        self.assertFalse(form.is_valid())


    def test__forms__viitetag_defined(self):
        """
        Testib vormi valideerimist, kui viitetagi pole defineeritud.
        """
        form = ArtikkelForm(
            data={
                "kirjeldus": f"Testi artikkel viidetagiga [viide_{self.test_viide.id}]",
                "hist_date": dt.now(),
                "viited": f"{self.test_viide.id}", # ajax_select välja sisu kujul "id|id|id"
            }
        )
        self.assertTrue(form.is_valid())