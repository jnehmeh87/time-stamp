import base64
from io import BytesIO
import segno

def generate_epc_qr_code(invoice):
    """
    Generates a SEPA EPC QR code for an invoice.
    """
    # EPC QR Code data structure
    # See: https://www.europeanpaymentscouncil.eu/document-library/guidance-documents/quick-response-code-guidelines-enable-data-capture-initiation
    data = {
        'name': invoice.organization.name,
        'iban': invoice.organization.iban,
        'amount': str(invoice.total_amount),
        'bic': invoice.organization.bic,
        'reference': f'INV-{invoice.pk}',
        'purpose': 'Invoice payment',
    }

    # Create the EPC QR code
    qrcode = segno.helpers.make_epc_qr(data)

    # Save the QR code to a buffer
    buffer = BytesIO()
    qrcode.save(buffer, kind='png', scale=5)
    buffer.seek(0)

    # Encode the image to base64
    encoded_img = base64.b64encode(buffer.read()).decode('utf-8')

    return encoded_img
