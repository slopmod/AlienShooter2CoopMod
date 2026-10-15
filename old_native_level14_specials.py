"""Retain Level14's queen battle and both original story branches."""


def adapt(source):
    from old_native_campaign_ending import adapt_script
    return adapt_script(source, picture_vid=2250, text_prefix=r'Text\\end1_0',
                        original_body_sha256='ccb35f2e384858bc1ba76b59544e24850938cdf394e641f5640aee74aadacda5')
