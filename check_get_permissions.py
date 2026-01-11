"""
Check get_user_permissions output
"""

from init_database import WBSEDCLDatabase

print("=" * 80)
print("CHECKING get_user_permissions() FOR DCC USER")
print("=" * 80)

db = WBSEDCLDatabase()

# Get permissions for DCC user (ID=4)
perms = db.get_user_permissions(4)

print("\nPermissions returned for user_id=4 (DCC):")
print(perms)

print("\nIndividual permission checks:")
for key, value in perms.items():
    print(f"   {key} = {value}")

print("\nis_section_head in perms?", 'is_section_head' in perms)
print("perms.get('is_section_head', False) =", perms.get('is_section_head', False))

db.close()

print("=" * 80)