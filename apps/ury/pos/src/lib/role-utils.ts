import type { PosProfileCombined } from './pos-profile-api';
import type { User } from '../store/slices/auth-slice';

export const isUserRestrictedFromTableOrders = (
  user: User | null,
  posProfile: PosProfileCombined | null
): boolean => {
  if (!user || !posProfile || !user.roles || !posProfile.role_restricted_for_table_order) {
    return false;
  }

  // Get the restricted roles from the POS profile
  const restrictedRoles = posProfile.role_restricted_for_table_order.map(role => role.role);
  
  // Check if the user has any of the restricted roles
  const hasRestrictedRole = user.roles.some(role => restrictedRoles.includes(role));
  
  return hasRestrictedRole;
};

const DISCOUNT_ALLOWED_ROLES = ['System Manager', 'URY Cashier', 'URY Manager'];

// Only Admin/Cashier/Manager can apply a discount at billing time — Captain cannot.
export const isUserAllowedToApplyDiscount = (user: User | null): boolean => {
  if (!user) return false;
  if (user.name === 'Administrator') return true;
  if (!user.roles) return false;
  return user.roles.some(role => DISCOUNT_ALLOWED_ROLES.includes(role));
};

const MANAGER_ROLES = ['System Manager', 'URY Manager'];

// Once payment is reached, the bill has always already been printed — so
// a Cashier changing the discount there would just hit the 10%-cap /
// no-change-after-print Server Script anyway. Hide the control for them
// entirely at that point; only Manager/Admin can still adjust it there.
export const isUserManagerOrAdmin = (user: User | null): boolean => {
  if (!user) return false;
  if (user.name === 'Administrator') return true;
  if (!user.roles) return false;
  return user.roles.some(role => MANAGER_ROLES.includes(role));
};

const KOT_REPRINT_ALLOWED_ROLES = ['System Manager', 'URY Cashier', 'URY Manager'];

// KOT Reprint is an override action — once a KOT is punched, a Captain must
// get it right or the order gets cancelled, not reprinted. Only Admin/Cashier/Manager can reprint.
export const isUserAllowedToReprintKot = (user: User | null): boolean => {
  if (!user) return false;
  if (user.name === 'Administrator') return true;
  if (!user.roles) return false;
  return user.roles.some(role => KOT_REPRINT_ALLOWED_ROLES.includes(role));
};