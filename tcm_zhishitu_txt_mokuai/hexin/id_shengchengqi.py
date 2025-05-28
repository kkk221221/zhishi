# In-memory counter for generating IDs.
# For a real application, this should be more robust,
# e.g., by checking existing IDs in files or using UUIDs.
_counters = {}

def generate_id(prefix: str) -> str:
    """
    Generates a new ID with the given prefix and an incrementing number.

    Args:
        prefix: The prefix for the ID (e.g., "YC", "ZZ").

    Returns:
        A string representing the new unique ID (e.g., "YC001").
    """
    if prefix not in _counters:
        _counters[prefix] = 0
    
    _counters[prefix] += 1
    return f"{prefix}{_counters[prefix]:03d}"

# Example usage (optional, can be removed or commented out):
if __name__ == '__main__':
    print(generate_id("YC"))
    print(generate_id("YC"))
    print(generate_id("ZZ"))
    print(generate_id("YC"))
    for i in range(95):
        generate_id("TEST")
    print(generate_id("TEST")) # Should be TEST096
    print(generate_id("TEST")) # Should be TEST097
    print(generate_id("TEST")) # Should be TEST098
    print(generate_id("TEST")) # Should be TEST099
    print(generate_id("TEST")) # Should be TEST100
    print(generate_id("ANOTHER")) # Should be ANOTHER001
