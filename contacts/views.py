from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerForm, SupplierForm
from .models import Customer, Supplier


def customer_list(request):
    customers = Customer.objects.all()

    if request.GET.get("inactive") != "1":
        customers = customers.filter(is_active=True)

    return render( request, "contacts/customer_list.html", { "customers": customers, "show_inactive": request.GET.get("inactive") == "1", }, )


def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)

        if form.is_valid():
            customer = form.save()

            messages.success( request, f"Customer '{customer.name}' was created.", )

            return redirect( "contacts:customer_detail", pk=customer.pk, )
    else:
        form = CustomerForm()

    return render( request, "contacts/customer_form.html", { "form": form, "title": "Add Customer", }, )



def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    invoices = customer.invoices.all().order_by(
        "-issue_date",
        "-id",
    )

    return render( request, "contacts/customer_detail.html", { "customer": customer, "invoices": invoices, }, )


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            customer = form.save()

            messages.success( request, f"Customer '{customer.name}' was updated.", )

            return redirect( "contacts:customer_detail", pk=customer.pk, )
    else:
        form = CustomerForm(instance=customer)

    return render( request, "contacts/customer_form.html", { "form": form, "title": "Edit Customer", "customer": customer, }, )


def customer_deactivate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        customer.is_active = False
        customer.save(update_fields=["is_active"])

        messages.success( request, f"Customer '{customer.name}' was deactivated.", )

        return redirect("contacts:customer_list")

    return render( request, "contacts/customer_detail.html", { "customer": customer, "confirm_deactivate": True, }, )


def customer_activate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        customer.is_active = True
        customer.save(update_fields=["is_active"])

        messages.success( request, f"Customer '{customer.name}' was reactivated.", )

    return redirect( "contacts:customer_detail", pk=customer.pk, )



# SUPPLIER VIEWS 

def supplier_list(request):
    suppliers = Supplier.objects.all()

    if request.GET.get("inactive") != "1":
        suppliers = suppliers.filter(is_active=True)

    return render( request, "contacts/supplier_list.html", { "suppliers": suppliers, "show_inactive": request.GET.get("inactive") == "1", }, )


def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)

        if form.is_valid():
            supplier = form.save()

            messages.success( request, f"Supplier '{supplier.name}' was created.", )

            return redirect( "contacts:supplier_detail", pk=supplier.pk, )
    else:
        form = SupplierForm()

        supplier_id = request.GET.get("supplier")

        if supplier_id:
            supplier = get_object_or_404(
                Supplier,
                pk=supplier_id,
            )
            form.initial["supplier"] = supplier

    return render( request, "contacts/supplier_form.html", { "form": form, "title": "Add Supplier", }, )



def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    purchases = supplier.purchases.all().order_by( "-purchase_date", "-id", )

    return render( request, "contacts/supplier_detail.html", { "supplier": supplier, "purchases": purchases, }, )


def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)

        if form.is_valid():
            supplier = form.save()

            messages.success( request, f"Supplier '{supplier.name}' was updated.", )

            return redirect( "contacts:supplier_detail", pk=supplier.pk, )
    else:
        form = SupplierForm(instance=supplier)

    return render( request, "contacts/supplier_form.html", { "form": form, "title": "Edit Supplier", "supplier": supplier, }, )


def supplier_deactivate(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        supplier.is_active = False
        supplier.save(update_fields=["is_active"])

        messages.success( request, f"Supplier '{supplier.name}' was deactivated.", )

        return redirect("contacts:supplier_list")

    return render( request, "contacts/supplier_detail.html", { "supplier": supplier, "confirm_deactivate": True, }, )


def supplier_activate(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        supplier.is_active = True
        supplier.save(update_fields=["is_active"])

        messages.success( request, f"Supplier '{supplier.name}' was reactivated.", )

    return redirect( "contacts:supplier_detail", pk=supplier.pk, )
