from django.test import TestCase
from django.urls import reverse

class VgvkViewTests(TestCase):
    def test_algus_view(self):
        response = self.client.get(reverse('vgvk:vgvk_index'))
        self.assertEqual(response.status_code, 200)

