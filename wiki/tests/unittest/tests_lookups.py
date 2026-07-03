from django.test import TestCase, RequestFactory
from django.conf import settings
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt, Viide, Allikas, Pilt
from wiki.lookups import ArtikkelLookup, IsikLookup, ViideLookup

class LookupTestCase(TestCase):
    def setUp(self):
        # We need a request object because your get_query calls .daatumitega(request)
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        
        # 1. Setup Allikas & Viide (Foreign Key relationship)
        self.allikas = Allikas.objects.filter(nimi="Lõuna-Eesti").first()
        self.allikas = Viide.objects.filter(allikas=self.allikas).first()

        # 2. Setup Isik
        self.isik = Isik.objects.filter(eesnimi="Kalev", perenimi="Härk").first()

        # 3. Setup Artikkel
        self.artikkel = Artikkel.objects.filter(
            kirjeldus="Valga",
            hist_year=1900
        ).first()

    def test_artikkel_lookup_query(self):
        """Tests if ArtikkelLookup filters correctly using the annotated full_viide."""
        lookup = ArtikkelLookup()
        # Test searching by description
        results = lookup.get_query("1900 Valga", self.request)
        self.assertIn(self.artikkel, results)
        
        # Test searching by ID (part of full_viide annotation)
        results = lookup.get_query(str(self.artikkel.id), self.request)
        self.assertIn(self.artikkel, results)

    def test_isik_lookup_query(self):
        """Tests the 'nimi' annotation (eesnimi + perenimi)."""
        lookup = IsikLookup()
        # Search combined name
        results = lookup.get_query("Kalev Härk", self.request)
        self.assertIn(self.isik, results)

    def test_viide_lookup_query(self):
        """Tests searching Viide via the related Allikas name."""
        lookup = ViideLookup()
        results = lookup.get_query("Lõuna-Eesti", self.request)
        self.assertIn(self.viide, results)

    def test_format_item_display_contains_copy_icon(self):
        """
        Verifies that format_item_display produces the HTML span 
        with the correct class and ID for the jQuery click handler.
        """
        lookup = IsikLookup()
        html = lookup.format_item_display(self.isik)
        
        # Verify the span for your jQuery function exists
        expected_id = f'id="copy_isik_{self.isik.id}"'
        self.assertIn('class="ui-icon ui-icon-copy"', html)
        self.assertIn(expected_id, html)
        self.assertIn('X</span>', html)

    def test_translation_logic(self):
        """
        Tests if the character translation works (e.g., replacing 
        special characters based on settings.TRANSLATION).
        """
        lookup = IsikLookup()
        # If TRANSLATION maps 'k' to 'ck', searching 'Kalev Härck' should find 'Kalev Härk'
        # This depends on what you have in your settings.TRANSLATION
        if 'k' in settings.TRANSLATION:
            results = lookup.get_query("Kalev Härck", self.request)
            self.assertIn(self.isik, results)

    def test_format_match(self):
        """Verify the plain text match format used in the autocomplete dropdown."""
        lookup = ArtikkelLookup()
        match_text = lookup.format_match(self.artikkel)
        # Expected: (1900:1) Test Description (or similar based on __str__)
        self.assertIn(str(self.artikkel.id), match_text)
        self.assertIn("1900", match_text)