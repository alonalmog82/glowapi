def apply_substitutions(template: str, substitutions: dict) -> str:
    """
    Replace {{key}} markers in template with values from substitutions.

    Uses str.replace() in a loop — never str.format() — to avoid conflicts with
    Terraform/HCL syntax which uses single braces for its own interpolation (${}),
    and to avoid KeyErrors on unrelated {} patterns in config files.

    Unmatched keys in substitutions are silently ignored.
    Unresolved {{markers}} are left as-is.
    """
    result = template
    for key, value in substitutions.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def derive_sidecar_path(target_file: str) -> str:
    """
    Return the sidecar JSON path for a given target file.

    Example: 'customers/acme/vpn.tf' → 'customers/acme/vpn.tf.json'

    The sidecar stores the original API request payload and enables the /update
    endpoint to reconstruct and diff the previous provisioning state.
    """
    return f"{target_file}.json"
