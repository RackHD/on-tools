# Copyright 2016, EMC, Inc.

def strip_suffix(text, suffix):
    """
    Cut a set of the last characters from a provided string
    :param text: Base string to cut
    :param suffix: String to remove if found at the end of text
    :return: text without the provided suffix
    """
    if text is not None and text.endswith(suffix):
        return text[:len(text) - len(suffix)]
    else:
        return text


def strip_prefix(text, prefix):
    if text is not None and text.startswith(prefix):
        return text[len(prefix):]
    else:
        return text
