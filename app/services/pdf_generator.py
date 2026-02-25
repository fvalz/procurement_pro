import os
from datetime import datetime
from fpdf import FPDF
from app import models

def remove_polish_chars(text):
    """Zamienia polskie znaki diakrytyczne na ich odpowiedniki bez znaków."""
    if text is None:
        return ""
    mapping = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
    }
    return ''.join(mapping.get(ch, ch) for ch in text)

class OrderPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ZAMOWIENIE ZAKUPU', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Purchase Order', 0, 1, 'C')
        self.ln(5)
        self.set_draw_color(100, 100, 100)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Strona {self.page_no()}', 0, 0, 'C')

    def supplier_section(self, supplier):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'Sprzedawca:', 0, 1)
        self.set_font('Arial', '', 10)
        supplier_name = remove_polish_chars(supplier.name) if supplier else 'Nieznany'
        supplier_email = remove_polish_chars(supplier.contact_email) if supplier and supplier.contact_email else '-'
        self.cell(0, 6, supplier_name, 0, 1)
        self.cell(0, 6, f'Email: {supplier_email}', 0, 1)
        self.ln(4)

    def buyer_section(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'Kupujacy:', 0, 1)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Procurement Pro Sp. z o.o.', 0, 1)
        self.cell(0, 6, 'ul. Przemyslowa 1, 00-001 Warszawa', 0, 1)
        self.cell(0, 6, 'NIP: 1234567890', 0, 1)
        self.ln(4)

    def order_info(self, order):
        self.set_font('Arial', 'B', 10)
        self.cell(50, 6, 'Numer zamowienia:', 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, order.id, 0, 1)
        self.set_font('Arial', 'B', 10)
        self.cell(50, 6, 'Data wystawienia:', 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, datetime.now().strftime('%Y-%m-%d'), 0, 1)
        self.set_font('Arial', 'B', 10)
        self.cell(50, 6, 'Planowana dostawa:', 0, 0)
        est = order.estimated_delivery.strftime('%Y-%m-%d') if order.estimated_delivery else '-'
        self.cell(0, 6, est, 0, 1)
        self.ln(5)

    def item_table(self, order):
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(80, 8, 'Produkt', 1, 0, 'L', 1)
        self.cell(20, 8, 'Ilosc', 1, 0, 'C', 1)
        self.cell(25, 8, 'Cena netto', 1, 0, 'R', 1)
        self.cell(25, 8, 'Wartosc netto', 1, 0, 'R', 1)
        self.cell(15, 8, 'VAT%', 1, 0, 'C', 1)
        self.cell(25, 8, 'Wartosc brutto', 1, 1, 'R', 1)

        self.set_font('Arial', '', 9)
        product = order.product
        qty = order.quantity
        total_brutto = order.total_price
        vat_rate = 0.23
        netto = total_brutto / (1 + vat_rate)
        unit_netto = netto / qty if qty else 0
        
        product_name = remove_polish_chars(product.name) if product else 'Produkt'
        self.cell(80, 8, product_name[:50], 'LR', 0, 'L')
        self.cell(20, 8, str(qty), 'LR', 0, 'C')
        self.cell(25, 8, f'{unit_netto:.2f} PLN', 'LR', 0, 'R')
        self.cell(25, 8, f'{netto:.2f} PLN', 'LR', 0, 'R')
        self.cell(15, 8, '23%', 'LR', 0, 'C')
        self.cell(25, 8, f'{total_brutto:.2f} PLN', 'LR', 1, 'R')

        self.set_font('Arial', 'B', 10)
        self.cell(150, 8, 'Razem brutto:', 'LT', 0, 'R')
        self.cell(25, 8, f'{total_brutto:.2f} PLN', 'LRT', 1, 'R')

    def terms(self, order):
        self.ln(10)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 8, 'Warunki handlowe:', 0, 1)
        self.set_font('Arial', '', 9)
        self.cell(0, 5, f'Termin platnosci: {order.payment_terms_days or 30} dni od daty wystawienia.', 0, 1)
        self.cell(0, 5, 'Dokument wazny bez podpisu i pieczeci.', 0, 1)
        self.cell(0, 5, 'Zamowienie wygenerowane automatycznie przez system Procurement Pro.', 0, 1)

def generate_order_pdf(order: models.Order, output_dir='generated_orders'):
    """Generuje PDF dla zamówienia i zwraca ścieżkę pliku."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf = OrderPDF()
    pdf.add_page()
    pdf.supplier_section(order.supplier)
    pdf.buyer_section()
    pdf.order_info(order)
    pdf.item_table(order)
    pdf.terms(order)
    
    filename = f"Order_{order.id}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)
    return filepath