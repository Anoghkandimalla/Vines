# API upgrades

## 2022-11-15

### Breaking changes

- The `charges` property on the `PaymentIntent` resource is no longer included by default. You can request its inclusion using the `expand` parameter. As a replacement, a new `latest_charge` property has been added, which contains the ID of the latest charge created by the PaymentIntent.

### Other changes

- Adds support for new values on `Account` capabilities.

## 2022-08-01

### Breaking changes

- The `paid_out_of_band` property on `Invoice` has been replaced by the `out_of_band_amount` property.

## 2020-08-27

### Breaking changes

- The `sources` property on `Customer` is no longer included by default.
