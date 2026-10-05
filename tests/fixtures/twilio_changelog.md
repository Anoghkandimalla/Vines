twilio-python Changelog
=======================

Here you can see the full list of changes between each twilio-python release.

[2024-02-27] Version 9.0.0
--------------------------
**Note:** This release contains breaking changes, check our [upgrade guide](./UPGRADE.md###-2024-02-20-8xx-to-9xx) for detailed migration notes.

**Library - Feature**
- [PR #767](https://github.com/twilio/twilio-python/pull/767): Merge branch '9.0.0-rc' into main. Thanks to [@tiwarishubham635](https://github.com/tiwarishubham635)! **(breaking change)**

**Library - Chore**
- [PR #771](https://github.com/twilio/twilio-python/pull/771): added check for unset values. Thanks to [@tiwarishubham635](https://github.com/tiwarishubham635)!
- [PR #768](https://github.com/twilio/twilio-python/pull/768): cluster tests enabled. Thanks to [@sbansla](https://github.com/sbansla)!

**Api**
- remove feedback and feedback summary from call resource

**Flex**
- Adding `routing_properties` to Interactions Channels Participant

**Lookups**
- Add new `line_status` package to the lookup response
- Remove `live_activity` package from the lookup response **(breaking change)**

**Messaging**
- Add tollfree multiple rejection reasons response array

**Trusthub**
- Add ENUM for businessRegistrationAuthority in compliance_registration. **(breaking change)**
- Add new field in isIsvEmbed in compliance_registration.
- Add additional optional fields in compliance_registration for Individual business type.

**Twiml**
- Add support for new Amazon Polly and Google voices (Q1 2024) for `Say` verb


[2024-02-09] Version 8.13.0
---------------------------
**Library - Fix**
- [PR #753](https://github.com/twilio/twilio-python/pull/753): added boolean_to_string converter. Thanks to [@tiwarishubham635](https://github.com/tiwarishubham635)!

**Library - Chore**
- [PR #758](https://github.com/twilio/twilio-python/pull/758): disable cluster test. Thanks to [@sbansla](https://github.com/sbansla)!
- [PR #760](https://github.com/twilio/twilio-python/pull/760): run make prettier. Thanks to [@tiwarishubham635](https://github.com/tiwarishubham635)!

**Api**
- Updated service base url for connect apps and authorized connect apps APIs **(breaking change)**
- Update documentation to reflect RiskCheck GA
- Added optional parameter `CallToken` for create participant api

**Events**
- Marked as GA

**Flex**
- Adding `flex_instance_sid` to Flex Configuration
- Adding `provisioning_status` for Email Manager
- Adding `offline_config` to Flex Configuration

**Insights**
- add flag to restrict access to unapid customers
- decommission voice-qualitystats-endpoint role

**Intelligence**
- Add text-generation operator (for example conversation summary) results to existing OperatorResults collection.

**Lookups**
- Remove `carrier` field from `sms_pumping_risk` and leave `carrier_risk_category` **(breaking change)**
- Remove carrier information from call forwarding package **(breaking change)**

**Messaging**
- Add update instance endpoints to us_app_to_person api
- Add tollfree edit_allowed and edit_reason fields
- Update Phone Number, Short Code, Alpha Sender, US A2P and Channel Sender documentation
- Add DELETE support to Tollfree Verification resource

**Numbers**
- Add Get Port In request api

**Push**
- Migrated to new Push API V4 with Resilient Notification Delivery.

**Serverless**
- Add node18 as a valid Build runtime

**Taskrouter**
- Add `jitter_buffer_size` param in update reservation
- Add container attribute to task_queue_bulk_real_time_statistics endpoint
- Remove beta_feature check on task_queue_bulk_real_time_statistics endpoint

**Trusthub**
- Add optional field NotificationEmail to the POST /v1/ComplianceInquiries/Customers/Initialize API
- Add additional optional fields in compliance_tollfree_inquiry.json
- Rename did to tollfree_phone_number in compliance_tollfree_inquiry.json
- Add new optional field notification_email to compliance_tollfree_inquiry.json

**Verify**
- `Tags` property added again to Public Docs **(breaking change)**
- Remove `Tags` from Public Docs **(breaking change)**
- Add `VerifyEventSubscriptionEnabled` parameter to service create and update endpoints.
- Add `Tags` optional parameter on Verification creation.
- Update Verify TOTP maturity to GA.


[2024-01-25] Version 8.12.0
---------------------------
**Oauth**
- updated openid discovery endpoint uri **(breaking change)**
- Added device code authorization endpoint
- added oauth JWKS endpoint
- Get userinfo resource
- OpenID discovery resource
- Add new API for token endpoint


