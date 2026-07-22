const money = value => Number.parseFloat(value || 0);

function hoursBetween(startDate, endDate, deliveryTime, pickupTime) {
  if (!startDate || !endDate || !deliveryTime || !pickupTime) return 0;
  const start = new Date(`${startDate}T${deliveryTime}`);
  const end = new Date(`${endDate}T${pickupTime}`);
  return Math.max(0, (end - start) / 3600000);
}

export const pricingService = {
  hoursBetween,
  calculate({ variant, logistics = {}, startDate, endDate, quantity = 1, mode = 'days', deliveryTime = '', pickupTime = '', hours = 0 }) {
    const days = startDate && endDate
      ? Math.max(0, Math.floor((new Date(endDate) - new Date(startDate)) / 86400000))
      : 0;
    const computedHours = mode === 'hours'
      ? (hoursBetween(startDate, endDate, deliveryTime, pickupTime) || money(hours))
      : 0;
    const rental = mode === 'hours'
      ? money(variant?.rental_price_per_hour) * computedHours * quantity
      : money(variant?.rental_price_per_day) * days * quantity;
    const delivery = money(logistics.delivery_cost);
    const pickup = money(logistics.pickup_cost);
    const installation = money(logistics.installation_cost) + money(logistics.calibration_cost) + money(logistics.startup_cost);
    const training = money(logistics.training_cost);
    const subtotal = rental + delivery + pickup + installation + training;
    const tax = Math.round(subtotal * .19 * 100) / 100;
    return { days, hours: mode === 'hours' ? computedHours : null, rental, delivery, pickup, installation, training, subtotal, tax, total: subtotal + tax };
  },
};
