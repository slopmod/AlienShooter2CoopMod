"""Keep the final boss phases and share Kate's original campaign ending."""


def adapt(source):
    from old_native_campaign_ending import adapt_script
    return adapt_script(source, picture_vid=2251, text_prefix=r'Text\\end2_0',
                        original_body_sha256='673089fd69dd6320e544bbe1d78c5f3ee578d87317c405646a951972d9947ebe')
