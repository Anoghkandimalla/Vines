# Changelog

Keep track of changes and upgrades to the Stripe API.

## 2026-07-29.dahlia

### Billing and invoicing

| Title | Affected Products | Breaking change? | Category |
| --- | --- | --- | --- |
| [Adds invoice description, footer, and custom parameters to the Subscription Schedules and Quotes APIs](https://docs.stripe.com/changelog/dahlia/2026-07-29/invoice-description-footer-and-custom-fields.md) | Billing, Invoicing | Non-breaking | api |
| [Adds subscription metadata support to invoice previews](https://docs.stripe.com/changelog/dahlia/2026-07-29/adds-subscription-metadata-support-to-invoice-preview.md) | Invoicing, Billing | Non-breaking | api |
| [Adds the trial property to subscription schedule phases](https://docs.stripe.com/changelog/dahlia/2026-07-29/subscription-schedule-phases-trial-property.md) | Billing | Non-breaking | api |
| [Adds item-level discount support for pending updates](https://docs.stripe.com/changelog/dahlia/2026-07-29/item-level-discounts-for-pending-updates.md) | Billing | Non-breaking | api |

## 2022-11-15

### Additional updates

| Title | Affected Products | Breaking change? | Category |
| --- | --- | --- | --- |
| [The `Charges` object no longer auto-expands refunds by default](https://docs.stripe.com/changelog/2022-11-15/deprecates-charges-auto-expand.md) | Payments | Breaking | api |
| [Removes the `charges` attribute from the `PaymentIntent` object](https://docs.stripe.com/changelog/2022-11-15/removes-charges-attribute-paymentintent.md) | Payments | Breaking | api |
| [Adds new decline codes to the PaymentIntent and PaymentMethod APIs](https://docs.stripe.com/changelog/2022-11-15/adds-decline-codes-paymentintent-paymentmethod.md) | Payments | Breaking | api |
| [Adds new decline codes to the SetupIntent API](https://docs.stripe.com/changelog/2022-11-15/adds-decline-codes-setupintent.md) | Payments | Breaking | api |
| [Adds a new structure error code to the Accounts API](https://docs.stripe.com/changelog/2022-11-15/adds-structure-error-code-accounts.md) | Connect | Breaking | api |

## 2022-08-01

### Additional updates

| Title | Affected Products | Breaking change? | Category |
| --- | --- | --- | --- |
| [Removes the `include_and_require` value when creating invoices](https://docs.stripe.com/changelog/2022-08-01/removes-include-require-value-invoices.md) | Invoicing | Breaking | api |
| [Default customer creation in Checkout Session payment mode changed to `if_required`](https://docs.stripe.com/changelog/2022-08-01/default-customer-creation-checkout-session.md) | Checkout | Breaking | api |
| [Deferred PaymentIntent creation in Checkout Session payment mode](https://docs.stripe.com/changelog/2022-08-01/deferred-paymentintent-checkout-session.md) | Checkout, Payments | Breaking | api |
| [Removes the `setup_intent` property from Checkout Sessions in subscription mode](https://docs.stripe.com/changelog/2022-08-01/removes-setupintent-checkout-session.md) | Checkout | Breaking | api |
| [Replaces line item parameters from the Create Checkout Session endpoint](https://docs.stripe.com/changelog/2022-08-01/replaces-line-item-create-checkout-session.md) | Checkout | Breaking | api |
| [Removes the subscription data parameter from the Create Checkout Session endpoint](https://docs.stripe.com/changelog/2022-08-01/removes-subscription-data-create-checkout-session.md) | Checkout, Billing | Breaking | api |
| [Removes the shipping rate parameter from Create Checkout Session endpoint](https://docs.stripe.com/changelog/2022-08-01/removes-shipping-rate-create-checkout-session.md) | Checkout | Breaking | api |
| [Updates Checkout Session shipping properties](https://docs.stripe.com/changelog/2022-08-01/updates-shipping-property-checkout-session.md) | Checkout | Breaking | api |
| [Adds 3D Secure exemption status to card charges](https://docs.stripe.com/changelog/2022-08-01/adds-3d-secure-exemption-charges.md) | Payments | Breaking | api |
| [New error code for invalid terms of service acceptance in Accounts API](https://docs.stripe.com/changelog/2022-08-01/error-code-invalid-tos-accounts.md) | Connect | Breaking | api |
| [New endpoints for managing a physical card’s shipping status in test mode](https://docs.stripe.com/changelog/2022-08-01/endpoints-shipping-status-cards.md) | Issuing | Breaking | api |
| [Adds `design_rejected` as a possible cancellation reason for issued cards](https://docs.stripe.com/changelog/2022-08-01/adds-design-rejected-value-cards.md) | Issuing | Breaking | api |
| [Removes the `default_currency` attribute from the `Customer` object](https://docs.stripe.com/changelog/2022-08-01/removes-default-currency-customer-object.md) | All products | Breaking | api |

# 2020
