"""Changelog formats apiwatch can watch, keyed by the `format` config field."""
from apiwatch.watcher import stripe, twilio

# format -> (parse_changelog, enrich_change or None)
FORMATS = {
    "stripe": (stripe.parse_changelog, stripe.enrich_change),
    "twilio": (twilio.parse_changelog, None),
}


def get_format(api: dict):
    """Resolve an api config entry's format; defaults to its name."""
    fmt = str(api.get("format", api["name"])).lower()
    if fmt not in FORMATS:
        raise ValueError(
            f"unsupported changelog format '{fmt}' for api '{api['name']}'; "
            f"set 'format:' to one of: {', '.join(sorted(FORMATS))}"
        )
    return FORMATS[fmt]
