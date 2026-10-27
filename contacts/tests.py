
from django.test import TestCase
from django.urls import reverse

from .models import Customer, Supplier


class CustomerCRUDTestCase(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="01234 567890",
            address="1 Test Street\nTest Town",
            postcode="RH12 1AA",
            is_active=True,
        )

    def test_customer_list_shows_active_customers(self):
        response = self.client.get(
            reverse("contacts:customer_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Customer")

    def test_customer_list_hides_inactive_customers_by_default(self):
        self.customer.is_active = False
        self.customer.save()

        response = self.client.get(
            reverse("contacts:customer_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Customer")

    def test_customer_list_can_show_inactive_customers(self):
        self.customer.is_active = False
        self.customer.save()

        response = self.client.get(
            reverse("contacts:customer_list") + "?inactive=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Customer")

    def test_customer_create_page_loads(self):
        response = self.client.get(
            reverse("contacts:customer_create")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Customer")

    def test_customer_can_be_created(self):
        response = self.client.post(
            reverse("contacts:customer_create"),
            {
                "name": "New Customer",
                "email": "new@example.com",
                "phone": "020 1234 5678",
                "address": "10 New Street",
                "postcode": "RH12 2BB",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        customer = Customer.objects.get(
            name="New Customer"
        )

        self.assertEqual(
            customer.email,
            "new@example.com",
        )
        self.assertEqual(
            customer.phone,
            "020 1234 5678",
        )
        self.assertTrue(customer.is_active)

        self.assertRedirects(
            response,
            reverse(
                "contacts:customer_detail",
                kwargs={"pk": customer.pk},
            ),
        )

    def test_customer_create_rejects_invalid_email(self):
        response = self.client.post(
            reverse("contacts:customer_create"),
            {
                "name": "Invalid Customer",
                "email": "not-an-email",
                "phone": "",
                "address": "",
                "postcode": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Customer.objects.filter(
                name="Invalid Customer"
            ).exists()
        )

        self.assertContains(
            response,
            "Enter a valid email address.",
        )

    def test_customer_detail_page_loads(self):
        response = self.client.get(
            reverse(
                "contacts:customer_detail",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Test Customer",
        )
        self.assertContains(
            response,
            "customer@example.com",
        )
        self.assertContains(
            response,
            "01234 567890",
        )
        self.assertContains(
            response,
            "RH12 1AA",
        )

    def test_customer_update_page_loads(self):
        response = self.client.get(
            reverse(
                "contacts:customer_update",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Customer")

    def test_customer_can_be_updated(self):
        response = self.client.post(
            reverse(
                "contacts:customer_update",
                kwargs={"pk": self.customer.pk},
            ),
            {
                "name": "Updated Customer",
                "email": "updated@example.com",
                "phone": "01999 111222",
                "address": "20 Updated Street",
                "postcode": "RH12 3CC",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.name,
            "Updated Customer",
        )
        self.assertEqual(
            self.customer.email,
            "updated@example.com",
        )
        self.assertEqual(
            self.customer.phone,
            "01999 111222",
        )
        self.assertEqual(
            self.customer.address,
            "20 Updated Street",
        )
        self.assertEqual(
            self.customer.postcode,
            "RH12 3CC",
        )
        self.assertTrue(self.customer.is_active)

        self.assertRedirects(
            response,
            reverse(
                "contacts:customer_detail",
                kwargs={"pk": self.customer.pk},
            ),
        )

    def test_customer_can_be_deactivated(self):
        response = self.client.post(
            reverse(
                "contacts:customer_deactivate",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.customer.refresh_from_db()

        self.assertFalse(
            self.customer.is_active
        )

        self.assertRedirects(
            response,
            reverse("contacts:customer_list"),
        )

    def test_deactivate_page_requires_confirmation(self):
        response = self.client.get(
            reverse(
                "contacts:customer_deactivate",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Deactivate customer?",
        )

        self.customer.refresh_from_db()

        self.assertTrue(
            self.customer.is_active
        )

    def test_customer_can_be_reactivated(self):
        self.customer.is_active = False
        self.customer.save()

        response = self.client.post(
            reverse(
                "contacts:customer_activate",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.customer.refresh_from_db()

        self.assertTrue(
            self.customer.is_active
        )

        self.assertRedirects(
            response,
            reverse(
                "contacts:customer_detail",
                kwargs={"pk": self.customer.pk},
            ),
        )

    def test_deactivate_requires_post(self):
        response = self.client.get(
            reverse(
                "contacts:customer_deactivate",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.customer.refresh_from_db()

        self.assertTrue(
            self.customer.is_active
        )

    def test_activate_requires_post(self):
        self.customer.is_active = False
        self.customer.save()

        response = self.client.get(
            reverse(
                "contacts:customer_activate",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.customer.refresh_from_db()

        self.assertFalse(
            self.customer.is_active
        )

    def test_customer_detail_returns_404_for_unknown_customer(self):
        response = self.client.get(
            reverse(
                "contacts:customer_detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_customer_update_returns_404_for_unknown_customer(self):
        response = self.client.get(
            reverse(
                "contacts:customer_update",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_customer_deactivate_returns_404_for_unknown_customer(self):
        response = self.client.post(
            reverse(
                "contacts:customer_deactivate",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_customer_activate_returns_404_for_unknown_customer(self):
        response = self.client.post(
            reverse(
                "contacts:customer_activate",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)



class SupplierCRUDTestCase(TestCase):

    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Test Supplier",
            email="supplier@example.com",
            phone="01234 567890",
            address="1 Supplier Street\nSupplier Town",
            postcode="RH12 1AA",
            is_active=True,
        )

    def test_supplier_list_shows_active_suppliers(self):
        response = self.client.get(
            reverse("contacts:supplier_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Supplier")

    def test_supplier_list_hides_inactive_suppliers_by_default(self):
        self.supplier.is_active = False
        self.supplier.save()

        response = self.client.get(
            reverse("contacts:supplier_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Supplier")

    def test_supplier_list_can_show_inactive_suppliers(self):
        self.supplier.is_active = False
        self.supplier.save()

        response = self.client.get(
            reverse("contacts:supplier_list") + "?inactive=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Supplier")

    def test_supplier_create_page_loads(self):
        response = self.client.get(
            reverse("contacts:supplier_create")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Supplier")

    def test_supplier_can_be_created(self):
        response = self.client.post(
            reverse("contacts:supplier_create"),
            {
                "name": "New Supplier",
                "email": "new-supplier@example.com",
                "phone": "020 1234 5678",
                "address": "10 Supplier Street",
                "postcode": "RH12 2BB",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        supplier = Supplier.objects.get(
            name="New Supplier"
        )

        self.assertEqual(
            supplier.email,
            "new-supplier@example.com",
        )
        self.assertEqual(
            supplier.phone,
            "020 1234 5678",
        )
        self.assertTrue(supplier.is_active)

        self.assertRedirects(
            response,
            reverse(
                "contacts:supplier_detail",
                kwargs={"pk": supplier.pk},
            ),
        )

    def test_supplier_create_rejects_invalid_email(self):
        response = self.client.post(
            reverse("contacts:supplier_create"),
            {
                "name": "Invalid Supplier",
                "email": "not-an-email",
                "phone": "",
                "address": "",
                "postcode": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Supplier.objects.filter(
                name="Invalid Supplier"
            ).exists()
        )

        self.assertContains(
            response,
            "Enter a valid email address.",
        )

    def test_supplier_detail_page_loads(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_detail",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Test Supplier",
        )
        self.assertContains(
            response,
            "supplier@example.com",
        )
        self.assertContains(
            response,
            "01234 567890",
        )
        self.assertContains(
            response,
            "RH12 1AA",
        )

    def test_supplier_update_page_loads(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_update",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Supplier")

    def test_supplier_can_be_updated(self):
        response = self.client.post(
            reverse(
                "contacts:supplier_update",
                kwargs={"pk": self.supplier.pk},
            ),
            {
                "name": "Updated Supplier",
                "email": "updated-supplier@example.com",
                "phone": "01999 111222",
                "address": "20 Updated Supplier Street",
                "postcode": "RH12 3CC",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.supplier.refresh_from_db()

        self.assertEqual(
            self.supplier.name,
            "Updated Supplier",
        )
        self.assertEqual(
            self.supplier.email,
            "updated-supplier@example.com",
        )
        self.assertEqual(
            self.supplier.phone,
            "01999 111222",
        )
        self.assertEqual(
            self.supplier.address,
            "20 Updated Supplier Street",
        )
        self.assertEqual(
            self.supplier.postcode,
            "RH12 3CC",
        )
        self.assertTrue(self.supplier.is_active)

        self.assertRedirects(
            response,
            reverse(
                "contacts:supplier_detail",
                kwargs={"pk": self.supplier.pk},
            ),
        )

    def test_supplier_can_be_deactivated(self):
        response = self.client.post(
            reverse(
                "contacts:supplier_deactivate",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.supplier.refresh_from_db()

        self.assertFalse(
            self.supplier.is_active
        )

        self.assertRedirects(
            response,
            reverse("contacts:supplier_list"),
        )

    def test_deactivate_supplier_page_requires_confirmation(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_deactivate",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Deactivate supplier?",
        )

        self.supplier.refresh_from_db()

        self.assertTrue(
            self.supplier.is_active
        )

    def test_supplier_can_be_reactivated(self):
        self.supplier.is_active = False
        self.supplier.save()

        response = self.client.post(
            reverse(
                "contacts:supplier_activate",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.supplier.refresh_from_db()

        self.assertTrue(
            self.supplier.is_active
        )

        self.assertRedirects(
            response,
            reverse(
                "contacts:supplier_detail",
                kwargs={"pk": self.supplier.pk},
            ),
        )

    def test_supplier_deactivate_requires_post(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_deactivate",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.supplier.refresh_from_db()

        self.assertTrue(
            self.supplier.is_active
        )

    def test_supplier_activate_requires_post(self):
        self.supplier.is_active = False
        self.supplier.save()

        response = self.client.get(
            reverse(
                "contacts:supplier_activate",
                kwargs={"pk": self.supplier.pk},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.supplier.refresh_from_db()

        self.assertFalse(
            self.supplier.is_active
        )

    def test_supplier_detail_returns_404_for_unknown_supplier(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_supplier_update_returns_404_for_unknown_supplier(self):
        response = self.client.get(
            reverse(
                "contacts:supplier_update",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_supplier_deactivate_returns_404_for_unknown_supplier(self):
        response = self.client.post(
            reverse(
                "contacts:supplier_deactivate",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_supplier_activate_returns_404_for_unknown_supplier(self):
        response = self.client.post(
            reverse(
                "contacts:supplier_activate",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

