import React, { useState, useEffect } from 'react';
import { X, Percent, Coins } from 'lucide-react';
import { usePOSStore } from '../store/pos-store';
import { useRootStore } from '../store/root-store';
import { cn, formatCurrency, getServerErrorMessage } from '../lib/utils';
import { Button, Input, Dialog, DialogContent } from './ui';
import { Spinner } from './ui/spinner';
import { call } from '../lib/frappe-sdk';
import { DEFAULT_PAYMENT_MODE } from '../data/order-types';
import { isUserManagerOrAdmin } from '../lib/role-utils';
import { printOrder } from '../lib/print';
import { showToast } from './ui/toast';
import { t } from '../i18n';


interface PaymentDialogProps {
  onClose: () => void;
  grandTotal: number;
  roundedTotal: number;
  subTotal: number;
  invoice: string;
  customer: string;
  posProfile: string;
  table: string | null;
  cashier: string;
  owner: string;
  fetchOrders: () => Promise<void>;
  clearSelectedOrder: () => void;
  initialDiscountPercentage?: number;
}

const PaymentDialog: React.FC<PaymentDialogProps> = ({
  onClose,
  grandTotal,
  roundedTotal,
  subTotal,
  invoice,
  customer,
  posProfile,
  table,
  cashier,
  owner,
  fetchOrders,
  clearSelectedOrder,
  initialDiscountPercentage
}) => {
  const { paymentModes, fetchPaymentModes, posProfile: storePosProfile } = usePOSStore();
  const { user } = useRootStore();
  // At the payment step the bill has always already been printed (Orders.tsx
  // requires printing before enabling Payment), so a Cashier changing the
  // discount here would only hit the "no changes after print" Server Script
  // rule anyway. Hide the control for them entirely — only Manager/Admin can
  // still adjust it at this stage.
  const canApplyDiscount = isUserManagerOrAdmin(user);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discountType] = useState<'percentage'>('percentage'); // Only percentage now
  // Pre-filled from whatever discount was already applied at print time — the
  // cashier can see it and increase it further here if the customer negotiates more.
  const [discountValue, setDiscountValue] = useState<string>(
    initialDiscountPercentage ? String(initialDiscountPercentage) : ''
  );
  // Discount is always a percentage of the true pre-discount subtotal (subTotal),
  // never of grandTotal — grandTotal may already have a discount baked in from
  // print time, and discounting off it again would compound instead of replace.
  const [appliedDiscount, setAppliedDiscount] = useState<number>(
    initialDiscountPercentage ? (subTotal * initialDiscountPercentage) / 100 : 0
  );
  const [paymentInputs, setPaymentInputs] = useState<{ [mode: string]: string }>({});
  const PART_PAYMENT = '__PART_PAYMENT__';
  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [showPartPaymentModal, setShowPartPaymentModal] = useState(false);

  useEffect(() => {
    fetchPaymentModes();
  }, [fetchPaymentModes]);

  // Calculate split payment total
  const payments = paymentModes
    .map((mode: any) => {
      const id = typeof mode === 'string' ? mode : mode.id;
      const amount = parseFloat(paymentInputs[id] || '');
      return amount > 0 ? { mode_of_payment: id, amount } : null;
    })
    .filter(Boolean);
  const paymentsTotal = payments.reduce((sum, p: any) => sum + p.amount, 0);

  const [isReprinting, setIsReprinting] = useState(false);

  const handleApplyDiscount = () => {
    const value = parseFloat(discountValue);
    if (isNaN(value) || value <= 0) {
      setError(t('errors.invalid_discount'));
      return;
    }
    if (value > 100) {
      setError(t('errors.discount_exceeds_max'));
      return;
    }
    const calculatedDiscount = (subTotal * value) / 100;
    setAppliedDiscount(calculatedDiscount);
    setError(null);
  };

  // Persists the current discount value and reprints the bill, without leaving this screen.
  const handleReprintWithDiscount = async () => {
    if (!storePosProfile) return;
    setIsReprinting(true);
    setError(null);
    try {
      const value = discountValue ? parseFloat(discountValue) : 0;
      await call.post('ury.ury.doctype.ury_order.ury_order.apply_discount', {
        invoice,
        discount_percentage: value,
      });
      setAppliedDiscount(value ? (subTotal * value) / 100 : 0);
      await printOrder({ orderId: invoice, posProfile: storePosProfile });
      showToast.success(t('success.printed'));
    } catch (err) {
      setError(getServerErrorMessage(err, t('errors.print_failed', { reason: String(err) })));
    } finally {
      setIsReprinting(false);
    }
  };

  // Order summary logic
  const subtotal = subTotal;
  const adjustment = roundedTotal - grandTotal;
  const roundedAdjustment = Math.round(adjustment * 100) / 100;
  const showAdjustment = Math.abs(roundedAdjustment) > 0.001;
  const totalDiscount = appliedDiscount;
  const discountedTotal = Math.max(0, subtotal - totalDiscount);
  // If discount is applied, round up; else, round normally
  const finalTotal = appliedDiscount > 0 ? Math.ceil(discountedTotal) : Math.round(discountedTotal);
  const finalAdjustment = finalTotal - discountedTotal;
  const roundedFinalAdjustment = Math.round(finalAdjustment * 100) / 100;
  const showFinalAdjustment = Math.abs(roundedFinalAdjustment) > 0.001;

  // Default to the primary mode (Cash) pre-filled with the full amount — the
  // common case needs zero input from the cashier beyond hitting Pay.
  useEffect(() => {
    if (selectedMode !== null || paymentModes.length === 0) return;
    const defaultMode = paymentModes.find((mode: any) => (typeof mode === 'string' ? mode : mode.id) === DEFAULT_PAYMENT_MODE);
    const initialMode = defaultMode ? DEFAULT_PAYMENT_MODE : (typeof paymentModes[0] === 'string' ? paymentModes[0] : paymentModes[0].id);
    setSelectedMode(initialMode);
  }, [paymentModes, selectedMode]);

  useEffect(() => {
    if (!selectedMode || selectedMode === PART_PAYMENT || !finalTotal) return;
    setPaymentInputs({ [selectedMode]: String(finalTotal) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMode, finalTotal]);

  function handleSelectMode(modeId: string) {
    setSelectedMode(modeId);
    setPaymentInputs({ [modeId]: String(finalTotal) });
  }

  function handleSelectPartPayment() {
    setSelectedMode(PART_PAYMENT);
    setPaymentInputs({});
    setShowPartPaymentModal(true);
  }

  // Helper to calculate remaining balance
  const getRemainingBalance = (currentId: string) => {
    const totalEntered = Object.entries(paymentInputs)
      .filter(([id]) => id !== currentId)
      .reduce((sum, [_, val]) => sum + (parseFloat(val) || 0), 0);
    return Math.max(0, finalTotal - totalEntered);
  };

  // Handler for input focus to auto-fill remaining balance
  const handlePaymentInputFocus = (id: string) => {
    setPaymentInputs(inputs => {
      // Only auto-fill if the field is empty or zero
      if (!inputs[id] || parseFloat(inputs[id]) === 0) {
        const remaining = getRemainingBalance(id);
        return { ...inputs, [id]: remaining > 0 ? String(remaining) : '' };
      }
      return inputs;
    });
  };

  const handlePayment = async () => {
    setIsProcessing(true);
    setError(null);
    try {
      await call.post('ury.ury.doctype.ury_order.ury_order.make_invoice', {
        additionalDiscount: discountValue && canApplyDiscount ? parseFloat(discountValue) : null,
        cashier,
        customer,
        invoice,
        owner,
        payments,
        pos_profile: posProfile,
        table,
      });
      // Show toast and reload orders (assume showToast and reload available globally)
      if (typeof window !== 'undefined' && (window as any).showToast) {
        (window as any).showToast.success('Payment successful');
      }
      onClose();
      clearSelectedOrder();
      await fetchOrders();
    } catch (err) {
      setError(getServerErrorMessage(err, t('errors.print_failed', { reason: String(err) })));
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent variant="xlarge" className="bg-white w-full max-w-4xl max-h-[90vh] flex flex-col md:flex-row p-0" showCloseButton={false}>
        {/* Left Column - Discount and Payment Mode */}
        <div className="md:w-1/2 p-6 border-b md:border-b-0 md:border-r border-gray-200 overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{t('payment.title')}</h2>
            <Button
              onClick={onClose}
              variant="ghost"
              size="icon"
              className="p-2"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Discount Section (conditional) — Admin/Cashier/Manager only, not Captain */}
          {storePosProfile?.enable_discount === 1 && canApplyDiscount && (
            <div className="space-y-4 mb-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Percent className="w-5 h-5" />
                {t('payment.apply_discount')}
              </h3>
              <div className="flex gap-2">
                <Input
                  type="number"
                  value={discountValue}
                  onChange={(e) => setDiscountValue(e.target.value)}
                  placeholder={t('payment.discount_placeholder')}
                  size="sm"
                  className="flex-1"
                />
                <Button
                  onClick={handleApplyDiscount}
                  variant="default"
                  size="sm"
                >
                  {t('common.apply')}
                </Button>
                <Button
                  onClick={handleReprintWithDiscount}
                  variant="outline"
                  size="sm"
                  disabled={isReprinting}
                >
                  {isReprinting ? <Spinner className="w-4 h-4" hideMessage /> : t('payment.reprint_bill')}
                </Button>
              </div>
            </div>
          )}

          {/* Payment Mode Section - single-select radio, with Part Payment opening a split popup */}
          <div className="space-y-4 mb-6">
            <h3 className="text-lg font-semibold">{t('payment.payment_methods')}</h3>
            <div className="grid grid-cols-1 gap-2">
              {paymentModes.map((mode: any) => {
                const id = typeof mode === 'string' ? mode : mode.id;
                const label = typeof mode === 'string' ? mode : mode.name;
                return (
                  <label
                    key={id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                      selectedMode === id ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'
                    )}
                  >
                    <input
                      type="radio"
                      name="payment-mode"
                      className="w-4 h-4"
                      checked={selectedMode === id}
                      onChange={() => handleSelectMode(id)}
                      disabled={isProcessing}
                    />
                    <span className="font-medium">{label}</span>
                  </label>
                );
              })}
              <label
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                  selectedMode === PART_PAYMENT ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'
                )}
              >
                <input
                  type="radio"
                  name="payment-mode"
                  className="w-4 h-4"
                  checked={selectedMode === PART_PAYMENT}
                  onChange={handleSelectPartPayment}
                  disabled={isProcessing}
                />
                <span className="font-medium">{t('payment.part_payment')}</span>
              </label>
            </div>

            {selectedMode && selectedMode !== PART_PAYMENT && (
              <div className="flex items-center gap-3">
                <span className="w-24 font-medium text-sm text-gray-600">{t('payment.amount')}</span>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={paymentInputs[selectedMode] || ''}
                  onChange={e => setPaymentInputs({ [selectedMode]: e.target.value })}
                  placeholder={t('payment.amount_placeholder')}
                  className="flex-1"
                  size="sm"
                  disabled={isProcessing}
                />
              </div>
            )}

            {selectedMode === PART_PAYMENT && (
              <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 border border-gray-200">
                <span className="text-sm text-gray-600">
                  {payments.length > 0
                    ? t('payment.split_summary', { count: String(payments.length), amount: formatCurrency(paymentsTotal) })
                    : t('payment.split_not_set')}
                </span>
                <Button size="sm" variant="outline" onClick={() => setShowPartPaymentModal(true)}>
                  {t('payment.edit_split')}
                </Button>
              </div>
            )}

            <div className="flex justify-between mt-2 text-sm">
              <span className="font-medium">{t('payment.total_entered')}</span>
              <span className={'text-green-600 font-semibold flex items-center gap-1'}>
                {formatCurrency(paymentsTotal)} / {formatCurrency(finalTotal)}
                {paymentsTotal > finalTotal && (
                  <span className="text-yellow-700 font-semibold">
                    <Coins className="inline w-4 h-4 ml-1 text-yellow-500" />
                    <span className="text-yellow-500 font-bold ml-1">{formatCurrency(paymentsTotal - finalTotal)}</span>
                  </span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Part Payment popup - split the total across multiple modes */}
        <Dialog open={showPartPaymentModal} onOpenChange={setShowPartPaymentModal}>
          <DialogContent variant="large" onClose={() => setShowPartPaymentModal(false)}>
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4">{t('payment.part_payment')}</h3>
              <div className="grid grid-cols-1 gap-3">
                {paymentModes.map((mode: any) => {
                  const id = typeof mode === 'string' ? mode : mode.id;
                  return (
                    <div key={id} className="flex items-center gap-3">
                      <span className="w-24 font-medium">{typeof mode === 'string' ? mode : mode.name}</span>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        value={paymentInputs[id] || ''}
                        onChange={e => setPaymentInputs(inputs => ({ ...inputs, [id]: e.target.value }))}
                        onFocus={() => handlePaymentInputFocus(id)}
                        placeholder={t('payment.amount_placeholder')}
                        className="flex-1"
                        size="sm"
                      />
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-4 text-sm">
                <span className="font-medium">{t('payment.total_entered')}</span>
                <span className="text-green-600 font-semibold">
                  {formatCurrency(paymentsTotal)} / {formatCurrency(finalTotal)}
                </span>
              </div>
              <Button className="w-full mt-4" onClick={() => setShowPartPaymentModal(false)}>
                {t('common.save')}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Right Column - Order Summary and Pay Button */}
        <div className="md:w-1/2 p-6 overflow-y-auto">
          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {/* Order Summary */}
          <div className="space-y-3 mb-6">
            <h3 className="text-lg font-semibold">{t('payment.order_summary')}</h3>
            <div className="space-y-2 text-sm">
              {/* Subtotal (Grand Total) */}
              <div className="flex justify-between">
                <span className="text-gray-600">{t('payment.subtotal')}</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              {/* Discount */}
              {appliedDiscount > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>{t('payment.discount')}</span>
                  <span>-{formatCurrency(appliedDiscount)}</span>
                </div>
              )}
              {/* Adjustment (if any) */}
              {showFinalAdjustment && (
                <div className="flex justify-between text-blue-600">
                  <span>{t('payment.adjustment')}</span>
                  <span>{roundedFinalAdjustment > 0 ? '+' : ''}{formatCurrency(roundedFinalAdjustment)}</span>
                </div>
              )}
              {/* Final Total (Rounded) */}
              <div className="border-t pt-2">
                <div className="flex justify-between font-semibold text-lg">
                  <span>{t('payment.total')}</span>
                  <span>{formatCurrency(finalTotal)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Payment Button */}
          <Button
            onClick={handlePayment}
            disabled={isProcessing || payments.length === 0}
            variant={isProcessing || payments.length === 0 ? "secondary" : "default"}
            className="w-full"
          >
            {isProcessing ? t('payment.processing') : t('payment.pay_button', { amount: formatCurrency(paymentsTotal > 0 ? paymentsTotal : finalTotal) })}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PaymentDialog; 