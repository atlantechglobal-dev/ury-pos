import { call } from './frappe-sdk';

interface PaymentMode {
  mode_of_payment: string;
  opening_amount: number;
}

interface PaymentModeResponse {
  message: PaymentMode[];
}

export const getPaymentModes = async (): Promise<string[]> => {
  // Always fetch fresh — payment modes are admin-configured on the POS Profile
  // and must reflect immediately, not a stale session cache.
  try {
    const response = await call.get<PaymentModeResponse>("ury.ury_pos.api.getModeOfPayment");

    const paymentModes = response.message.map((mode:PaymentMode) => mode.mode_of_payment);
    
    // Cache in session storage
    sessionStorage.setItem('payment_modes', JSON.stringify(paymentModes));
    
    return paymentModes;
  } catch (error) {
    console.error('Failed to fetch payment modes:', error);
    throw error;
  }
}; 